from main import (
    build_prompt_history,
    build_ticket_recovery_observation,
    update_memory_after_finish,
)


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


def test_build_ticket_recovery_observation_for_sold_out_ticket():
    observation = build_ticket_recovery_observation(
        "check_ticket_availability",
        {"attraction": "故宫博物院", "date": "今天"},
        "sold_out",
    )

    assert observation is not None
    assert "故宫博物院" in observation
    assert "门票已售罄" in observation
    assert "备选方案" in observation
    assert "不要继续推荐" in observation


def test_build_ticket_recovery_observation_ignores_available_ticket():
    observation = build_ticket_recovery_observation(
        "check_ticket_availability",
        {"attraction": "颐和园", "date": "今天"},
        "available",
    )

    assert observation is None


def test_build_ticket_recovery_observation_ignores_other_tools():
    observation = build_ticket_recovery_observation(
        "get_weather",
        {"city": "北京"},
        "sold_out",
    )

    assert observation is None
