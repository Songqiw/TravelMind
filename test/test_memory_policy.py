from memory.memory_policy import evaluate_memory_value


def test_empty_input_is_not_remembered():
    decision = evaluate_memory_value("")

    assert decision.should_remember is False
    assert decision.category is None


def test_greeting_is_not_remembered():
    decision = evaluate_memory_value("你好")

    assert decision.should_remember is False
    assert decision.category is None


def test_one_off_weather_query_is_not_remembered():
    decision = evaluate_memory_value("今天北京天气怎么样")

    assert decision.should_remember is False
    assert decision.category is None


def test_explicit_preference_is_remembered():
    decision = evaluate_memory_value("记住我喜欢历史文化景点")

    assert decision.should_remember is True
    assert decision.category == "preferences"


def test_budget_preference_is_remembered_as_budget():
    decision = evaluate_memory_value("我的预算是每天500元以内")

    assert decision.should_remember is True
    assert decision.category == "budget"


def test_constraint_is_remembered_as_constraints():
    decision = evaluate_memory_value("我不能走太多路")

    assert decision.should_remember is True
    assert decision.category == "constraints"


def test_travel_style_is_remembered_as_travel_style():
    decision = evaluate_memory_value("以后推荐行程不要太赶")

    assert decision.should_remember is True
    assert decision.category == "travel_style"


def test_sensitive_info_is_not_remembered_without_explicit_request():
    decision = evaluate_memory_value("我的身份证号是123456789")

    assert decision.should_remember is False
    assert decision.category is None
