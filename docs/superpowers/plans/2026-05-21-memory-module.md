# Memory Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic first-phase memory module that stores long-term user preferences under `.memory/` and maintains `.memory/index.md` as the Chinese index entry point.

**Architecture:** Add a standalone `memory/` package with a rule-based `memory_policy` and a filesystem-backed `MemoryManager`. Tests use temporary project roots and do not touch the real project `.memory/` directory. Runtime integration with `main.py` and prompts is documented in the design spec but intentionally not implemented in this plan.

**Tech Stack:** Python standard library, `pytest`, Markdown files.

---

## File Structure

- Modify `memory/__init__.py`: exports `MemoryManager`, `MemoryDecision`, and `evaluate_memory_value`. The file already exists and is currently empty.
- Create `memory/memory_policy.py`: deterministic memory-worthiness and category classifier.
- Create `memory/memory_manager.py`: `.memory/` directory management, index generation/repair, memory file writes, and relevant-memory loading.
- Create `test/test_memory_policy.py`: unit tests for memory decisions.
- Create `test/test_memory_manager.py`: filesystem tests using `tmp_path`.

No first-phase implementation task may modify `main.py`, `prompts/`, `tools/`, or `client/`.

## Category Metadata

Use this shared category mapping in `memory_manager.py`:

```python
CATEGORY_METADATA = {
    "preferences": {
        "filename": "preferences.md",
        "title": "用户偏好",
        "purpose": "记录用户的旅行偏好",
        "topics": "历史文化、景点偏好、兴趣类型",
    },
    "budget": {
        "filename": "budget.md",
        "title": "预算偏好",
        "purpose": "记录用户的预算偏好",
        "topics": "预算范围、消费上限、价格敏感度",
    },
    "travel_style": {
        "filename": "travel_style.md",
        "title": "旅行方式",
        "purpose": "记录用户的旅行方式",
        "topics": "慢旅行、亲子游、行程节奏",
    },
    "constraints": {
        "filename": "constraints.md",
        "title": "旅行约束",
        "purpose": "记录用户的旅行限制和避雷项",
        "topics": "行动限制、禁忌、避雷要求",
    },
}
```

---

### Task 1: Memory Policy

**Files:**
- Modify: `memory/__init__.py`
- Create: `memory/memory_policy.py`
- Test: `test/test_memory_policy.py`

- [ ] **Step 1: Write failing policy tests**

Create `test/test_memory_policy.py`:

```python
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
```

- [ ] **Step 2: Run policy tests to verify they fail**

Run:

```bash
pytest test/test_memory_policy.py -q
```

Expected: FAIL because the `memory` package does not exist yet.

- [ ] **Step 3: Implement memory policy**

Create `memory/memory_policy.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryDecision:
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
    if _contains_any(text, BUDGET_KEYWORDS):
        return "budget"
    if _contains_any(text, TRAVEL_STYLE_KEYWORDS):
        return "travel_style"
    if _contains_any(text, CONSTRAINT_KEYWORDS):
        return "constraints"
    return "preferences"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)
```

Create `memory/__init__.py`:

```python
from memory.memory_policy import MemoryDecision, evaluate_memory_value

__all__ = ["MemoryDecision", "evaluate_memory_value"]
```

- [ ] **Step 4: Run policy tests to verify they pass**

Run:

```bash
pytest test/test_memory_policy.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit policy task**

Run:

```bash
git add memory/__init__.py memory/memory_policy.py test/test_memory_policy.py
git commit -m "feat: add memory policy"
```

Expected: commit succeeds if the user wants commits during execution. If the repo still has no initial commit and unrelated staged files exist, skip committing and report that the commit was intentionally skipped.

---

### Task 2: Memory Store Initialization And Index Rendering

**Files:**
- Modify: `memory/__init__.py`
- Create: `memory/memory_manager.py`
- Test: `test/test_memory_manager.py`

- [ ] **Step 1: Write failing initialization tests**

Create `test/test_memory_manager.py`:

```python
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
```

- [ ] **Step 2: Run manager tests to verify they fail**

Run:

```bash
pytest test/test_memory_manager.py -q
```

Expected: FAIL because `memory.memory_manager` does not exist yet.

- [ ] **Step 3: Implement initialization and index rendering**

Create `memory/memory_manager.py`:

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

from memory.memory_policy import evaluate_memory_value


CATEGORY_METADATA = {
    "preferences": {
        "filename": "preferences.md",
        "title": "用户偏好",
        "purpose": "记录用户的旅行偏好",
        "topics": "历史文化、景点偏好、兴趣类型",
    },
    "budget": {
        "filename": "budget.md",
        "title": "预算偏好",
        "purpose": "记录用户的预算偏好",
        "topics": "预算范围、消费上限、价格敏感度",
    },
    "travel_style": {
        "filename": "travel_style.md",
        "title": "旅行方式",
        "purpose": "记录用户的旅行方式",
        "topics": "慢旅行、亲子游、行程节奏",
    },
    "constraints": {
        "filename": "constraints.md",
        "title": "旅行约束",
        "purpose": "记录用户的旅行限制和避雷项",
        "topics": "行动限制、禁忌、避雷要求",
    },
}


class MemoryManager:
    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)
        self.memory_dir = self.project_root / ".memory"
        self.index_path = self.memory_dir / "index.md"

    def ensure_memory_store(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.write_text(self._render_index([]), encoding="utf-8")

    def load_index(self) -> str:
        self.ensure_memory_store()
        return self.index_path.read_text(encoding="utf-8")

    def load_relevant_memories(self, query: str) -> str:
        self.load_index()
        rows = self._existing_memory_rows()
        contents = []
        for row in rows:
            path = self.memory_dir / row["filename"]
            if path.exists():
                contents.append(path.read_text(encoding="utf-8").strip())
        return "\n\n".join(content for content in contents if content)

    def maybe_update_memory(self, user_input: str) -> bool:
        self.load_index()
        decision = evaluate_memory_value(user_input)
        if not decision.should_remember or decision.category is None:
            return False

        metadata = CATEGORY_METADATA[decision.category]
        memory_path = self.memory_dir / metadata["filename"]
        self._append_memory_entry(memory_path, metadata["title"], user_input)
        self._write_index_from_existing_files()
        return True

    def repair_index(self) -> None:
        self.ensure_memory_store()
        self._write_index_from_existing_files()

    def _append_memory_entry(self, path: Path, title: str, user_input: str) -> None:
        today = date.today().isoformat()
        entry = f"- {today}：{user_input.strip()}\n"

        if not path.exists():
            path.write_text(f"# {title}\n\n## 记忆条目\n\n{entry}", encoding="utf-8")
            return

        content = path.read_text(encoding="utf-8")
        if not content.endswith("\n"):
            content += "\n"
        path.write_text(f"{content}{entry}", encoding="utf-8")

    def _write_index_from_existing_files(self) -> None:
        rows = self._existing_memory_rows()
        self.index_path.write_text(self._render_index(rows), encoding="utf-8")

    def _existing_memory_rows(self) -> list[dict[str, str]]:
        rows = []
        today = date.today().isoformat()
        for metadata in CATEGORY_METADATA.values():
            filename = metadata["filename"]
            if (self.memory_dir / filename).exists():
                rows.append(
                    {
                        "filename": filename,
                        "purpose": metadata["purpose"],
                        "updated": today,
                        "topics": metadata["topics"],
                    }
                )
        return rows

    def _render_index(self, rows: list[dict[str, str]]) -> str:
        table_rows = "\n".join(
            f'| {row["filename"]} | {row["purpose"]} | {row["updated"]} | {row["topics"]} |'
            for row in rows
        )
        if table_rows:
            table_rows = f"{table_rows}\n"

        return (
            "# 记忆索引\n\n"
            "本文件是记忆系统的入口文件。智能体在读取、更新、新增、合并或删除任何记忆文件时，必须同步维护本文件。\n\n"
            "## 记忆文件列表\n\n"
            "| 文件 | 用途 | 最后更新时间 | 关键主题 |\n"
            "|---|---|---|---|\n"
            f"{table_rows}"
            "\n"
            "## 更新规则\n\n"
            "- 在读取或修改任何记忆文件之前，必须先读取本索引文件。\n"
            "- 必须根据本索引文件定位最相关的记忆文件。\n"
            "- 如果新记忆适合写入已有文件，必须优先更新已有文件。\n"
            "- 只有当现有记忆文件都不适合承载新信息时，才允许创建新的记忆文件。\n"
            "- 每次新增、修改、合并、重命名或删除记忆文件后，必须立即更新本索引文件。\n"
            "- 索引中的文件列表、用途、最后更新时间和关键主题必须与实际记忆文件保持一致。\n\n"
            "## 强约束\n\n"
            "- `.memory/index.md` 是记忆系统的唯一入口。\n"
            "- 智能体不得绕过 `.memory/index.md` 直接盲目扫描或随意创建记忆文件。\n"
            "- 任何对 `.memory/` 下记忆文件的变更，如果没有同步更新 `.memory/index.md`，都视为任务未完成。\n"
            "- 新增记忆文件但未登记到 `.memory/index.md`，视为无效记忆。\n"
            "- 删除、重命名或合并记忆文件后，如果没有更新 `.memory/index.md`，视为记忆系统损坏。\n"
            "- 如果索引内容与实际文件不一致，必须先修复索引，再继续执行记忆相关任务。\n"
        )
```

Modify `memory/__init__.py`:

```python
from memory.memory_manager import MemoryManager
from memory.memory_policy import MemoryDecision, evaluate_memory_value

__all__ = ["MemoryDecision", "MemoryManager", "evaluate_memory_value"]
```

- [ ] **Step 4: Run initialization tests**

Run:

```bash
pytest test/test_memory_manager.py -q
```

Expected: PASS for the two initialization tests.

- [ ] **Step 5: Run all memory tests**

Run:

```bash
pytest test/test_memory_policy.py test/test_memory_manager.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit initialization task**

Run:

```bash
git add memory/__init__.py memory/memory_manager.py test/test_memory_manager.py
git commit -m "feat: add memory store initialization"
```

Expected: commit succeeds if appropriate. If unrelated staged files make a focused commit unsafe, skip committing and report why.

---

### Task 3: Memory Writes And Index Updates

**Files:**
- Modify: `test/test_memory_manager.py`
- Modify: `memory/memory_manager.py`

- [ ] **Step 1: Add failing write tests**

Append to `test/test_memory_manager.py`:

```python
def test_irrelevant_input_does_not_create_category_files(tmp_path):
    manager = MemoryManager(tmp_path)

    updated = manager.maybe_update_memory("你好")

    assert updated is False
    assert not (tmp_path / ".memory" / "preferences.md").exists()
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "preferences.md" not in index


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
```

- [ ] **Step 2: Run write tests**

Run:

```bash
pytest test/test_memory_manager.py -q
```

Expected: PASS if Task 2 implementation already included write behavior. If any test fails, fix only `memory/memory_manager.py`.

- [ ] **Step 3: Add duplicate append behavior test**

Append to `test/test_memory_manager.py`:

```python
def test_multiple_preferences_append_to_same_file(tmp_path):
    manager = MemoryManager(tmp_path)

    manager.maybe_update_memory("记住我喜欢历史文化景点")
    manager.maybe_update_memory("我喜欢博物馆")

    preferences = (tmp_path / ".memory" / "preferences.md").read_text(encoding="utf-8")
    index = (tmp_path / ".memory" / "index.md").read_text(encoding="utf-8")
    assert "记住我喜欢历史文化景点" in preferences
    assert "我喜欢博物馆" in preferences
    assert index.count("preferences.md") == 1
```

- [ ] **Step 4: Run manager tests**

Run:

```bash
pytest test/test_memory_manager.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit write task**

Run:

```bash
git add memory/memory_manager.py test/test_memory_manager.py
git commit -m "feat: add memory writes and index updates"
```

Expected: commit succeeds if appropriate. If unrelated staged files make a focused commit unsafe, skip committing and report why.

---

### Task 4: Index Repair And Memory Loading

**Files:**
- Modify: `test/test_memory_manager.py`
- Modify: `memory/memory_manager.py`

- [ ] **Step 1: Add failing repair and load tests**

Append to `test/test_memory_manager.py`:

```python
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
```

- [ ] **Step 2: Run repair and load tests**

Run:

```bash
pytest test/test_memory_manager.py -q
```

Expected: PASS if Task 2 implementation already rewrites from existing files. If `load_relevant_memories()` behavior needs adjustment, fix only `memory/memory_manager.py`.

- [ ] **Step 3: Run all memory tests**

Run:

```bash
pytest test/test_memory_policy.py test/test_memory_manager.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit repair task**

Run:

```bash
git add memory/memory_manager.py test/test_memory_manager.py
git commit -m "feat: add memory index repair"
```

Expected: commit succeeds if appropriate. If unrelated staged files make a focused commit unsafe, skip committing and report why.

---

### Task 5: Final Verification

**Files:**
- Read only unless a verification issue appears in `memory/` or tests.

- [ ] **Step 1: Verify no forbidden files changed**

Run:

```bash
git status --short
```

Expected: no first-phase implementation changes to `main.py`, `prompts/`, `tools/`, or `client/`. Existing pre-plan user changes may still appear and should not be reverted.

- [ ] **Step 2: Run targeted test suite**

Run:

```bash
pytest test/test_memory_policy.py test/test_memory_manager.py -q
```

Expected: all tests pass.

- [ ] **Step 3: Inspect generated docs and code for placeholders**

Run:

```bash
rg -n "TBD|TODO|implement later|pass$|\\.\\.\\." memory test docs/superpowers/plans/2026-05-21-memory-module.md docs/superpowers/specs/2026-05-21-memory-module-design.md
```

Expected: no unresolved placeholders in implementation files. Ellipses may appear only in the design spec's illustrative API snippets.

- [ ] **Step 4: Report final status**

Summarize:

- Files created.
- Tests run and result.
- Confirmation that runtime integration files were not modified.
- Any skipped commits and why.

---

## Self-Review

- Spec coverage: The plan covers deterministic memory decisions, `.memory/` initialization, Chinese index rendering, category file writes, index updates, repair behavior, relevant memory loading, and the first-phase boundary.
- Placeholder scan: The plan contains no `TBD` or unfilled implementation placeholders. The only `...` appears in the design spec API examples and not in implementation code.
- Type consistency: `MemoryDecision`, `evaluate_memory_value()`, and `MemoryManager` signatures are consistent across tasks.
