from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _run_generator(repo_root: Path, output_root: Path) -> None:
    module_path = repo_root / "scripts" / "generate_phase2_examples.py"
    spec = importlib.util.spec_from_file_location("generate_phase2_examples", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.generate_examples(output_root=output_root)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_generation_script_writes_phase2_checkpoint_examples(
    repo_root: Path, tmp_path: Path
) -> None:
    output_root = tmp_path / "generated" / "ACME"

    _run_generator(repo_root, output_root)

    for stage in ("initial", "continued", "rerun"):
        stage_dir = output_root / stage
        assert stage_dir.is_dir()
        assert (stage_dir / "result.json").is_file()
        assert (stage_dir / "memo.md").is_file()
        assert (stage_dir / "delta.json").is_file()

    initial = _load_json(output_root / "initial" / "result.json")
    continued = _load_json(output_root / "continued" / "result.json")
    rerun = _load_json(output_root / "rerun" / "result.json")

    assert initial["run"]["status"] == "awaiting_continue"
    assert initial["run"]["checkpoint_panel_id"] == "gatekeepers"
    assert initial["delta"] is None
    assert continued["run"]["run_id"] == initial["run"]["run_id"]
    assert continued["run"]["status"] == "complete"
    assert rerun["run"]["run_kind"] == "refresh"
    assert rerun["delta"]["prior_run_id"] == continued["run"]["run_id"]
    assert "what_changed_since_last_run" in rerun["delta"]["changed_sections"]
