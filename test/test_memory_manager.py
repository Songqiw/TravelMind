from memory.memory_manager import MemoryManager


def test_ensure_memory_store_creates_directory_and_index(tmp_path):
    manager = MemoryManager(tmp_path)

    manager.ensure_memory_store()

    memory_dir = tmp_path / ".memory"
    index_file = memory_dir / "index.md"
    assert memory_dir.is_dir()
    assert index_file.is_file()
    assert "# 记忆索引" in index_file.read_text(encoding="utf-8")


def test_load_index_creates_index_when_missing(tmp_path):
    manager = MemoryManager(tmp_path)

    index = manager.load_index()

    assert "# 记忆索引" in index
    assert (tmp_path / ".memory" / "index.md").is_file()


def test_irrelevant_input_does_not_create_category_files(tmp_path):
    manager = MemoryManager(tmp_path)

    updated = manager.maybe_update_memory("你好")

    assert updated is False
    for filename in ("preferences.md", "budget.md", "travel_style.md", "constraints.md"):
        assert not (tmp_path / ".memory" / filename).exists()
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    for filename in ("preferences.md", "budget.md", "travel_style.md", "constraints.md"):
        assert filename not in index


def test_explicit_preference_writes_preferences_and_index(tmp_path):
    manager = MemoryManager(tmp_path)

    updated = manager.maybe_update_memory("记住我喜欢历史文化景点")

    assert updated is True
    preferences = (tmp_path / ".memory" / "preferences.md").read_text(encoding="utf-8")
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "记住我喜欢历史文化景点" in preferences
    assert "preferences.md" in index
    assert "记录用户的旅行偏好" in index


def test_budget_input_writes_budget_and_index(tmp_path):
    manager = MemoryManager(tmp_path)

    updated = manager.maybe_update_memory("我的预算是每天500元以内")

    assert updated is True
    budget = (tmp_path / ".memory" / "budget.md").read_text(encoding="utf-8")
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "我的预算是每天500元以内" in budget
    assert "budget.md" in index
    assert "记录用户的预算偏好" in index


def test_constraint_input_writes_constraints_and_index(tmp_path):
    manager = MemoryManager(tmp_path)

    updated = manager.maybe_update_memory("我不能走太多路")

    assert updated is True
    constraints = (tmp_path / ".memory" / "constraints.md").read_text(encoding="utf-8")
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "我不能走太多路" in constraints
    assert "constraints.md" in index
    assert "记录用户的旅行限制和避雷项" in index


def test_travel_style_input_writes_travel_style_and_index(tmp_path):
    manager = MemoryManager(tmp_path)

    updated = manager.maybe_update_memory("以后推荐行程不要太赶")

    assert updated is True
    travel_style = (tmp_path / ".memory" / "travel_style.md").read_text(encoding="utf-8")
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "以后推荐行程不要太赶" in travel_style
    assert "travel_style.md" in index
    assert "记录用户的旅行方式" in index


def test_multiple_preferences_append_to_same_file(tmp_path):
    manager = MemoryManager(tmp_path)

    manager.maybe_update_memory("记住我喜欢历史文化景点")
    manager.maybe_update_memory("我喜欢博物馆")

    preferences = (tmp_path / ".memory" / "preferences.md").read_text(encoding="utf-8")
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "记住我喜欢历史文化景点" in preferences
    assert "我喜欢博物馆" in preferences
    assert index.count("preferences.md") == 1


def test_repair_index_adds_existing_memory_file(tmp_path):
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "preferences.md").write_text(
        "# 用户偏好\n\n## 记忆条目\n\n- 2026-05-21：用户喜欢历史文化景点。\n",
        encoding="utf-8",
    )
    (memory_dir / "index.md").write_text("# 记忆索引\n", encoding="utf-8")
    manager = MemoryManager(tmp_path)

    manager.repair_index()

    index = (memory_dir / "index.md").read_text(encoding="utf-8")
    assert "preferences.md" in index
    assert "记录用户的旅行偏好" in index


def test_repair_index_removes_missing_memory_file(tmp_path):
    manager = MemoryManager(tmp_path)
    manager.ensure_memory_store()
    (tmp_path / ".memory" / "index.md").write_text(
        "# 记忆索引\n\n"
        "## 记忆文件列表\n\n"
        "| 文件 | 用途 | 最后更新时间 | 关键主题 |\n"
        "|---|---|---|---|\n"
        "| budget.md | 记录用户的预算偏好 | 2026-05-21 | 预算范围 |\n",
        encoding="utf-8",
    )

    manager.repair_index()

    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "budget.md" not in index


def test_load_relevant_memories_returns_existing_memory_contents(tmp_path):
    manager = MemoryManager(tmp_path)
    manager.maybe_update_memory("记住我喜欢历史文化景点")
    manager.maybe_update_memory("我的预算是每天500元以内")

    context = manager.load_relevant_memories("推荐北京景点")

    assert "记住我喜欢历史文化景点" in context
    assert "我的预算是每天500元以内" in context


def test_load_relevant_memories_filters_by_query_category(tmp_path):
    manager = MemoryManager(tmp_path)
    manager.maybe_update_memory("记住我喜欢历史文化景点")
    manager.maybe_update_memory("我的预算是每天500元以内")

    context = manager.load_relevant_memories("我的预算偏好是什么")

    assert "我的预算是每天500元以内" in context
    assert "记住我喜欢历史文化景点" not in context


def test_load_relevant_memories_uses_repaired_index(tmp_path):
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "preferences.md").write_text(
        "# 用户偏好\n\n## 记忆条目\n\n- 2026-05-21：用户喜欢历史文化景点。\n",
        encoding="utf-8",
    )
    (memory_dir / "index.md").write_text("# 记忆索引\n", encoding="utf-8")
    manager = MemoryManager(tmp_path)

    context = manager.load_relevant_memories("推荐北京景点")

    assert "用户喜欢历史文化景点" in context
    index = (memory_dir / "index.md").read_text(encoding="utf-8")
    assert "preferences.md" in index
