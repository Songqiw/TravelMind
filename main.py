# 将所有工具函数放入一个字典，方便后续调用
import os
import re
from pathlib import Path

from memory import MemoryManager
from prompts.AGENTS_SYSTEM_PROMPT import AGENT_SYSTEM_PROMPT


def build_prompt_history(user_prompt: str, memory_context: str) -> list[str]:
    """根据用户请求和长期记忆上下文构建首轮 prompt history。

    Args:
        user_prompt: 当前轮用户的原始请求。
        memory_context: 从 `MemoryManager` 读取到的长期记忆文本。为空时不会
            注入长期记忆块。

    Returns:
        用于后续 ReAct 循环的 prompt history 列表。
    """

    prompt_history = []
    if memory_context.strip():
        prompt_history.append(f"长期记忆上下文:\n{memory_context.strip()}")
    prompt_history.append(f"用户请求: {user_prompt}")
    return prompt_history


def update_memory_after_finish(memory_manager: MemoryManager, user_prompt: str) -> bool:
    """在 agent 完成回答后尝试更新长期记忆。

    Args:
        memory_manager: 项目级记忆管理器。
        user_prompt: 当前轮用户的原始请求。

    Returns:
        如果用户请求被写入长期记忆，返回 True；否则返回 False。

    Side Effects:
        可能创建或修改 `.memory/` 下的记忆文件和 `index.md`。
    """

    return memory_manager.maybe_update_memory(user_prompt)


def run_agent() -> None:
    """运行旅行智能体主循环，并在程序层接入长期记忆。

    主流程会先读取与用户请求相关的长期记忆并注入 prompt history；当模型
    使用 `Finish[...]` 完成任务后，再根据用户原始请求尝试更新长期记忆。

    Side Effects:
        会调用大模型 API、执行工具函数、打印运行日志，并可能更新
        `.memory/` 下的记忆文件。
    """

    from client.model_client import OpenAICompatibleClient
    from tools.get_attraction import get_attraction
    from tools.get_weather import get_weather

    available_tools = {
        "get_weather": get_weather,
        "get_attraction": get_attraction,
    }

    # --- 1. 配置LLM客户端 ---
    # 请根据您使用的服务，将这里替换成对应的凭证和地址
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    model_id = os.getenv("MODEL_ID")

    llm = OpenAICompatibleClient(
        model=model_id,
        api_key=api_key,
        base_url=base_url
    )

    # --- 2. 初始化 ---
    user_prompt = "你好，请帮我查询一下今天北京的天气，然后根据天气推荐一个合适的旅游景点。"
    project_root = Path(__file__).resolve().parent
    memory_manager = MemoryManager(project_root)
    memory_context = memory_manager.load_relevant_memories(user_prompt)
    prompt_history = build_prompt_history(user_prompt, memory_context)

    print(f"用户输入: {user_prompt}\n" + "=" * 40)

    # --- 3. 运行主循环 ---
    for i in range(5):  # 设置最大循环次数
        print(f"--- 循环 {i + 1} ---\n")

        # 3.1. 构建Prompt
        full_prompt = "\n".join(prompt_history)

        # 3.2. 调用LLM进行思考
        llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
        # 模型可能会输出多余的Thought-Action，需要截断
        match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
        if match:
            truncated = match.group(1).strip()
            if truncated != llm_output.strip():
                llm_output = truncated
                print("已截断多余的 Thought-Action 对")
        print(f"模型输出:\n{llm_output}\n")
        prompt_history.append(llm_output)

        # 3.3. 解析并执行行动
        action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
        if not action_match:
            observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
            observation_str = f"Observation: {observation}"
            print(f"{observation_str}\n" + "=" * 40)
            prompt_history.append(observation_str)
            continue
        action_str = action_match.group(1).strip()

        if action_str.startswith("Finish"):
            final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
            print(f"任务完成，最终答案: {final_answer}")
            if update_memory_after_finish(memory_manager, user_prompt):
                print("长期记忆已更新。")

            break

        tool_name = re.search(r"(\w+)\(", action_str).group(1)
        args_str = re.search(r"\((.*)\)", action_str).group(1)
        kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

        if tool_name in available_tools:
            observation = available_tools[tool_name](**kwargs)
        else:
            observation = f"错误:未定义的工具 '{tool_name}'"

        # 3.4. 记录观察结果
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)


if __name__ == "__main__":
    run_agent()
