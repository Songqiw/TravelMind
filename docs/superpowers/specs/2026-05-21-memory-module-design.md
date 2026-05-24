# TravelMind Memory Module Design

## Goal

Implement a program-level memory module for TravelMind that can persist long-term user preferences under `.memory/` while maintaining `.memory/index.md` as the only memory entry point.

The first implementation phase only creates and tests the `memory/` module. It must not modify `main.py`, prompt wiring, tool registration, or other runtime integration code. Integration changes are documented here for later execution.

## Current Project Context

TravelMind is a lightweight Python ReAct-style travel assistant.

- `main.py` owns the current loop, prompt history, LLM call, action parsing, and tool execution.
- `prompts/AGENTS_SYSTEM_PROMPT.py` defines the travel assistant ReAct prompt.
- `prompts/MEMORY_PROMPT.py` already contains the memory policy text, but it is not currently wired into runtime behavior.
- There is no committed git history yet, and the working tree already contains existing user changes.

## Chosen Approach

Use a program-level memory module instead of relying on pure prompt instructions or model tool calls.

The memory module will:

- Decide whether a user input is worth remembering.
- Create `.memory/` when needed.
- Create and maintain `.memory/index.md`.
- Write memory entries into categorized Markdown files.
- Repair index/file inconsistencies when detected.
- Load relevant memory snippets for a future prompt-injection step.

This approach makes the strong constraints enforceable by code and tests.

## First-Phase Scope

Implement only:

- `memory/__init__.py`
- `memory/memory_policy.py`
- `memory/memory_manager.py`
- tests for the memory module

Do not modify in this phase:

- `main.py`
- `prompts/AGENTS_SYSTEM_PROMPT.py`
- `prompts/MEMORY_PROMPT.py`
- `tools/`
- `client/`

## Out of Scope For First Phase

These are intentionally deferred:

- Injecting memory context into the agent prompt.
- Calling memory updates after `Finish[...]`.
- Adding ReAct tools for memory operations.
- Using an LLM to extract or classify memory.
- Semantic deduplication or advanced conflict resolution.
- Remembering sensitive information by default.

## Module Design

### `memory/memory_policy.py`

Responsible for deciding whether a user input is worth long-term memory and assigning it to a category.

Recommended API:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryDecision:
    should_remember: bool
    category: str | None
    reason: str


def evaluate_memory_value(text: str) -> MemoryDecision:
    ...
```

First-phase rule set:

- Remember explicit memory requests containing phrases such as `记住`, `帮我记住`, `以后都按`, `以后推荐`.
- Remember stable travel preferences such as `喜欢`, `不喜欢`, `偏好`, `预算`, `不能`, `不要`, `希望`, `适合`.
- Do not remember empty input, one-off weather/search requests, or pure greetings.
- Do not remember obvious sensitive information unless the user explicitly asks to remember it.

Category mapping:

- Budget-related input -> `budget`
- Travel pace/style input -> `travel_style`
- Constraints and avoidances -> `constraints`
- General attraction/interest preferences -> `preferences`
- Otherwise -> `preferences`

### `memory/memory_manager.py`

Responsible for filesystem behavior and index consistency.

Recommended API:

```python
from pathlib import Path


class MemoryManager:
    def __init__(self, project_root: Path | str):
        ...

    def ensure_memory_store(self) -> None:
        ...

    def load_index(self) -> str:
        ...

    def load_relevant_memories(self, query: str) -> str:
        ...

    def maybe_update_memory(self, user_input: str) -> bool:
        ...

    def repair_index(self) -> None:
        ...
```

Responsibilities:

- `.memory/index.md` is always the entry point.
- Before reading or modifying memory files, ensure the memory store exists and load the index.
- If the index is missing, create it in the Chinese format defined below.
- If known memory files exist but are missing from the index, repair the index.
- If the index references missing files, remove or fix those entries.
- When adding a memory entry, update the relevant category file and rewrite the index.
- If `evaluate_memory_value()` returns `should_remember=False`, do not write or update any memory files beyond initialization explicitly requested by a method.

## Memory File Layout

Memory files live under the project root:

```text
.memory/
  index.md
  preferences.md
  budget.md
  travel_style.md
  constraints.md
```

Files should be created only when needed. The index may exist with an empty table.

Memory entry format:

```md
# 用户偏好

## 记忆条目

- 2026-05-21：用户喜欢历史文化景点。
```

## Chinese Index Format

`index.md` should use this structure:

```md
# 记忆索引

本文件是记忆系统的入口文件。智能体在读取、更新、新增、合并或删除任何记忆文件时，必须同步维护本文件。

## 记忆文件列表

| 文件 | 用途 | 最后更新时间 | 关键主题 |
|---|---|---|---|

## 更新规则

- 在读取或修改任何记忆文件之前，必须先读取本索引文件。
- 必须根据本索引文件定位最相关的记忆文件。
- 如果新记忆适合写入已有文件，必须优先更新已有文件。
- 只有当现有记忆文件都不适合承载新信息时，才允许创建新的记忆文件。
- 每次新增、修改、合并、重命名或删除记忆文件后，必须立即更新本索引文件。
- 索引中的文件列表、用途、最后更新时间和关键主题必须与实际记忆文件保持一致。

## 强约束

- `.memory/index.md` 是记忆系统的唯一入口。
- 智能体不得绕过 `.memory/index.md` 直接盲目扫描或随意创建记忆文件。
- 任何对 `.memory/` 下记忆文件的变更，如果没有同步更新 `.memory/index.md`，都视为任务未完成。
- 新增记忆文件但未登记到 `.memory/index.md`，视为无效记忆。
- 删除、重命名或合并记忆文件后，如果没有更新 `.memory/index.md`，视为记忆系统损坏。
- 如果索引内容与实际文件不一致，必须先修复索引，再继续执行记忆相关任务。
```

When memory files exist, add rows such as:

```md
| preferences.md | 记录用户的旅行偏好 | 2026-05-21 | 历史文化、景点偏好、兴趣类型 |
| budget.md | 记录用户的预算偏好 | 2026-05-21 | 预算范围、消费上限、价格敏感度 |
```

## Later Integration Design

These changes should be planned but not executed in the first phase.

### Prompt Context Injection

In `main.py`, before creating `prompt_history`, a later phase can load relevant memory:

```python
memory_context = memory_manager.load_relevant_memories(user_prompt)
prompt_history = [
    f"长期记忆上下文:\n{memory_context}",
    f"用户请求: {user_prompt}",
]
```

If no relevant memory exists, omit the memory block or use a short empty-state sentence.

### Post-Answer Memory Update

After the assistant reaches `Finish[...]`, a later phase can update memory:

```python
memory_manager.maybe_update_memory(user_prompt)
```

This keeps memory writes tied to completed user turns.

### Prompt Wiring

A later phase can append `MEMORY_PROMPT` to the system prompt, but the source of truth for writing files remains `MemoryManager`.

## Error Handling

- Missing `.memory/` directory: create it.
- Missing `index.md`: create it.
- Index references missing files: repair the index before proceeding.
- Existing memory files not listed in index: add them to the index.
- Empty or irrelevant input: return a negative memory decision and do not write memory entries.
- File write errors: raise the original exception so tests and callers can fail visibly.

## Testing Strategy

Use temporary project roots in tests so real `.memory/` data is never touched.

Required tests:

- Creating a `MemoryManager` and calling `ensure_memory_store()` creates `.memory/index.md`.
- Irrelevant input such as `你好` is not remembered.
- One-off request such as `今天北京天气怎么样` is not remembered.
- Explicit request `记住我喜欢历史文化景点` writes to `preferences.md`.
- Budget input writes to `budget.md`.
- Constraint input writes to `constraints.md`.
- Every write updates `index.md`.
- `repair_index()` adds existing memory files missing from the index.
- `repair_index()` removes missing files from the index.

## Acceptance Criteria

- First-phase implementation touches only `memory/` and tests, plus optional design/plan docs.
- Memory decisions are deterministic and testable.
- `.memory/index.md` is generated in Chinese.
- Memory files are categorized and created only when needed.
- Index rows match the memory files that actually exist.
- Non-memory-worthy input does not create category memory files.
- Deferred integration steps are documented but not implemented.
