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
    """管理项目级长期记忆文件和中文索引。

    MemoryManager 是 `.memory/` 目录的唯一程序入口，负责创建记忆目录、
    维护 `index.md`、写入分类记忆文件、修复索引，以及按查询加载相关记忆。
    调用方不应绕过本类直接修改 `.memory/` 下的文件。
    """

    def __init__(self, project_root: Path | str):
        """初始化记忆管理器的项目路径和文件路径。

        Args:
            project_root: 项目根目录路径。记忆目录会固定放在该目录下的
                `.memory/` 中。
        """

        self.project_root = Path(project_root)
        self.memory_dir = self.project_root / ".memory"
        self.index_path = self.memory_dir / "index.md"

    def ensure_memory_store(self) -> None:
        """确保 `.memory/` 目录和 `index.md` 索引文件存在。

        Side Effects:
            如果 `.memory/` 不存在会创建目录；如果 `index.md` 不存在会
            创建一个空的中文记忆索引。
        """

        self.memory_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.write_text(self._render_index([]), encoding="utf-8")

    def load_index(self) -> str:
        """读取中文记忆索引内容。

        Returns:
            `.memory/index.md` 的完整文本内容。

        Side Effects:
            会先确保 `.memory/` 和 `index.md` 存在。
        """

        self.ensure_memory_store()
        return self.index_path.read_text(encoding="utf-8")

    def load_relevant_memories(self, query: str) -> str:
        """根据查询文本加载相关长期记忆。

        方法会先修复索引，随后通过 `evaluate_memory_value()` 尝试判断查询
        对应的记忆分类。如果能判断出分类，则只加载该分类对应的记忆文件；
        如果无法判断分类，则回退加载索引中登记的全部记忆文件。

        Args:
            query: 当前用户请求或用于检索记忆的查询文本。

        Returns:
            由相关记忆文件内容拼接成的字符串；没有可用记忆时返回空字符串。

        Side Effects:
            会调用 `repair_index()`，因此可能重写 `.memory/index.md`。
        """

        self.repair_index()
        decision = evaluate_memory_value(query)
        target_filename = None
        if decision.category in CATEGORY_METADATA:
            target_filename = CATEGORY_METADATA[decision.category]["filename"]

        rows = self._index_rows()
        contents = []
        for row in rows:
            if target_filename and row["filename"] != target_filename:
                continue
            path = self.memory_dir / row["filename"]
            if path.exists():
                contents.append(path.read_text(encoding="utf-8").strip())
        return "\n\n".join(content for content in contents if content)

    def maybe_update_memory(self, user_input: str) -> bool:
        """根据用户输入判断并写入长期记忆。

        方法会先读取或创建索引，然后调用记忆价值判断规则。只有当输入
        被判定为值得长期记忆时，才会写入对应分类的 Markdown 文件，并
        同步刷新 `index.md`。

        Args:
            user_input: 当前轮用户的原始输入。

        Returns:
            如果创建或更新了记忆文件，返回 True；如果输入不值得记忆，
            返回 False。

        Side Effects:
            可能创建 `.memory/`、创建或修改分类记忆文件，并重写
            `.memory/index.md`。
        """

        self.load_index()
        decision = evaluate_memory_value(user_input)
        if not decision.should_remember or decision.category is None:
            return False

        metadata = CATEGORY_METADATA.get(decision.category, CATEGORY_METADATA["preferences"])
        memory_path = self.memory_dir / metadata["filename"]
        self._append_memory_entry(memory_path, metadata["title"], user_input)
        self._write_index_from_existing_files()
        return True

    def repair_index(self) -> None:
        """修复 `index.md` 与实际记忆文件之间的不一致。

        当前修复策略以已知分类文件为准：存在的分类记忆文件会被登记到
        索引中，索引里指向缺失文件的旧行会被移除。

        Side Effects:
            会创建缺失的 `.memory/` 或 `index.md`，并重写 `index.md`。
        """

        self.ensure_memory_store()
        self._write_index_from_existing_files()

    def _append_memory_entry(self, path: Path, title: str, user_input: str) -> None:
        """向指定分类记忆文件追加一条用户输入。

        Args:
            path: 目标记忆文件路径。
            title: 目标记忆文件的中文标题。
            user_input: 要保存的用户原始输入。

        Side Effects:
            如果目标文件不存在会创建文件；如果已存在会在文件末尾追加
            一条带当前日期的记忆记录。
        """

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
        """根据当前存在的分类记忆文件重写索引。

        Side Effects:
            会覆盖写入 `.memory/index.md`，让索引内容与已知分类文件的
            实际存在状态保持一致。
        """

        rows = self._existing_memory_rows()
        self.index_path.write_text(self._render_index(rows), encoding="utf-8")

    def _existing_memory_rows(self) -> list[dict[str, str]]:
        """收集当前已存在分类记忆文件对应的索引行数据。

        Returns:
            每个已存在分类记忆文件的一行索引数据，包含文件名、用途、
            最后更新时间和关键主题。最后更新时间取文件修改时间。
        """

        rows = []
        for metadata in CATEGORY_METADATA.values():
            filename = metadata["filename"]
            path = self.memory_dir / filename
            if path.exists():
                rows.append(
                    {
                        "filename": filename,
                        "purpose": metadata["purpose"],
                        "updated": date.fromtimestamp(path.stat().st_mtime).isoformat(),
                        "topics": metadata["topics"],
                    }
                )
        return rows

    def _index_rows(self) -> list[dict[str, str]]:
        """从当前 `index.md` 中解析有效的记忆文件表格行。

        Returns:
            索引中登记且属于已知分类文件的行数据。格式异常或未知分类
            文件名会被忽略。
        """

        rows = []
        if not self.index_path.exists():
            return rows

        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("| ") or line.startswith("| 文件 ") or line.startswith("|---"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 4:
                continue
            filename, purpose, updated, topics = cells
            if filename in {metadata["filename"] for metadata in CATEGORY_METADATA.values()}:
                rows.append(
                    {
                        "filename": filename,
                        "purpose": purpose,
                        "updated": updated,
                        "topics": topics,
                    }
                )
        return rows

    def _render_index(self, rows: list[dict[str, str]]) -> str:
        """渲染完整的中文记忆索引 Markdown 内容。

        Args:
            rows: 要写入“记忆文件列表”表格的行数据。

        Returns:
            可直接写入 `.memory/index.md` 的 Markdown 字符串。
        """

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
