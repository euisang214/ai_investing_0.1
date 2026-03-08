from __future__ import annotations

from pathlib import Path


class PromptLoader:
    def __init__(self, prompts_dir: Path):
        self._prompts_dir = prompts_dir

    def load(self, relative_path: str) -> str:
        path = self._prompts_dir / Path(relative_path).relative_to("prompts")
        with path.open("r", encoding="utf-8") as handle:
            return handle.read()

