from __future__ import annotations

from pathlib import Path


class PromptLoader:
    def __init__(self, prompts_dir: Path):
        self._prompts_dir = prompts_dir

    def resolve(self, relative_path: str) -> Path:
        raw_path = Path(relative_path)
        if raw_path.is_absolute():
            raise ValueError(f"Prompt path must be relative: {relative_path}")
        if not raw_path.parts or raw_path.parts[0] != "prompts":
            raise ValueError(f"Prompt path must stay under prompts/: {relative_path}")

        path = (self._prompts_dir / Path(*raw_path.parts[1:])).resolve()
        try:
            path.relative_to(self._prompts_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"Prompt path escapes prompts directory: {relative_path}") from exc
        return path

    def load(self, relative_path: str) -> str:
        path = self.resolve(relative_path)
        with path.open("r", encoding="utf-8") as handle:
            return handle.read()
