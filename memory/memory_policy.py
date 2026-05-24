from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryDecision:
    """表示一次用户输入的记忆价值判断结果。

    Attributes:
        should_remember: 当前输入是否值得写入长期记忆。
        category: 记忆分类名称；不需要记忆时为 None。
        reason: 做出该判断的简短中文原因，便于日志或调试使用。
    """

    should_remember: bool
    category: str | None
    reason: str


EXPLICIT_MEMORY_KEYWORDS = (
    "记住",
    "帮我记住",
    "以后都按",
    "以后推荐",
)

STABLE_PREFERENCE_KEYWORDS = (
    "喜欢",
    "不喜欢",
    "偏好",
    "预算",
    "不能",
    "不要",
    "希望",
    "适合",
)

ONE_OFF_KEYWORDS = (
    "今天",
    "现在",
    "实时",
    "查询",
    "天气",
    "搜索",
)

GREETING_TEXTS = {
    "你好",
    "您好",
    "嗨",
    "hello",
    "hi",
}

SENSITIVE_KEYWORDS = (
    "身份证",
    "银行卡",
    "密码",
    "手机号",
    "电话",
    "住址",
)

BUDGET_KEYWORDS = (
    "预算",
    "价格",
    "消费",
    "花费",
    "每天",
    "元",
    "便宜",
    "贵",
)

TRAVEL_STYLE_KEYWORDS = (
    "慢旅行",
    "节奏",
    "太赶",
    "行程",
    "亲子",
    "自由行",
)

CONSTRAINT_KEYWORDS = (
    "不能",
    "不要",
    "不想",
    "避免",
    "避开",
    "无障碍",
    "走太多路",
)


def evaluate_memory_value(text: str) -> MemoryDecision:
    """判断用户输入是否值得长期记忆，并给出记忆分类。

    本函数只使用确定性关键词规则，不调用模型、不读写文件。它负责把
    用户输入分成“值得记忆”和“不值得记忆”两类，并在值得记忆时映射
    到 `preferences`、`budget`、`travel_style` 或 `constraints`。

    Args:
        text: 当前轮用户的原始输入。

    Returns:
        MemoryDecision: 包含是否记忆、目标分类和判断原因。
    """

    normalized = text.strip()
    lowered = normalized.lower()

    if not normalized:
        return MemoryDecision(False, None, "输入为空，不需要记忆")

    if lowered in GREETING_TEXTS:
        return MemoryDecision(False, None, "寒暄内容，不需要记忆")

    explicit = _contains_any(normalized, EXPLICIT_MEMORY_KEYWORDS)

    if _contains_any(normalized, SENSITIVE_KEYWORDS) and not explicit:
        return MemoryDecision(False, None, "疑似敏感信息，且用户未明确要求记忆")

    stable = _contains_any(normalized, STABLE_PREFERENCE_KEYWORDS)
    one_off = _contains_any(normalized, ONE_OFF_KEYWORDS)

    if one_off and not explicit and not stable:
        return MemoryDecision(False, None, "一次性查询内容，不需要记忆")

    if not explicit and not stable:
        return MemoryDecision(False, None, "没有长期复用价值")

    return MemoryDecision(True, _classify_category(normalized), "包含可长期复用的用户偏好或约束")


def _classify_category(text: str) -> str:
    """根据关键词把值得记忆的文本映射到固定分类。

    Args:
        text: 已确认值得记忆的用户输入。

    Returns:
        分类名称。当前只返回 `budget`、`travel_style`、`constraints`
        或默认的 `preferences`。
    """

    if _contains_any(text, BUDGET_KEYWORDS):
        return "budget"
    if _contains_any(text, TRAVEL_STYLE_KEYWORDS):
        return "travel_style"
    if _contains_any(text, CONSTRAINT_KEYWORDS):
        return "constraints"
    return "preferences"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """判断文本中是否包含任意一个指定关键词。

    Args:
        text: 待检查文本。
        keywords: 关键词元组。

    Returns:
        如果文本包含任一关键词，返回 True；否则返回 False。
    """

    return any(keyword in text for keyword in keywords)
