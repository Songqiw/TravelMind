from main import build_prompt_history, update_memory_after_finish


class FakeMemoryManager:
    def __init__(self, updated: bool):
        self.updated = updated
        self.received_user_input = None

    def maybe_update_memory(self, user_input: str) -> bool:
        self.received_user_input = user_input
        return self.updated


def test_build_prompt_history_includes_memory_context_when_present():
    history = build_prompt_history(
        "推荐北京景点",
        "# 用户偏好\n\n## 记忆条目\n\n- 用户喜欢历史文化景点。",
    )

    assert history == [
        "长期记忆上下文:\n# 用户偏好\n\n## 记忆条目\n\n- 用户喜欢历史文化景点。",
        "用户请求: 推荐北京景点",
    ]


def test_build_prompt_history_omits_empty_memory_context():
    history = build_prompt_history("推荐北京景点", "")

    assert history == ["用户请求: 推荐北京景点"]


def test_update_memory_after_finish_delegates_to_memory_manager():
    manager = FakeMemoryManager(updated=True)

    updated = update_memory_after_finish(manager, "记住我喜欢历史文化景点")

    assert updated is True
    assert manager.received_user_input == "记住我喜欢历史文化景点"
