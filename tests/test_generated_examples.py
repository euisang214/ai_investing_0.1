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


def test_generation_script_writes_phase5_lifecycle_examples(
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

    assert initial["run"]["status"] == "complete"
    assert initial["run"]["gate_decision"] in {"pass", "review"}
    assert initial["run"]["awaiting_continue"] is False
    assert initial["run"]["checkpoint"]["resolution_action"] == "continue"
    assert "continue automatically" in initial["run"]["checkpoint"]["note"]
    assert initial["delta"]["prior_run_id"] is None
    assert continued["run"]["run_id"] == initial["run"]["run_id"]
    assert continued["run"]["status"] == "complete"
    assert continued["run"]["checkpoint"]["resolution_action"] == "continue"
    assert continued["memo"]["is_initial_coverage"] is True
    assert continued["delta"]["prior_run_id"] is None
    assert rerun["run"]["run_kind"] == "refresh"
    assert rerun["run"]["awaiting_continue"] is False
    assert rerun["delta"]["prior_run_id"] == continued["run"]["run_id"]
    assert "what_changed_since_last_run" in rerun["delta"]["changed_sections"]


def test_checked_in_examples_match_generator_output(repo_root: Path, tmp_path: Path) -> None:
    output_root = tmp_path / "generated" / "ACME"
    checked_in_root = repo_root / "examples" / "generated" / "ACME"

    _run_generator(repo_root, output_root)

    for relative_path in (
        Path("initial/result.json"),
        Path("initial/memo.md"),
        Path("initial/delta.json"),
        Path("continued/result.json"),
        Path("continued/memo.md"),
        Path("continued/delta.json"),
        Path("rerun/result.json"),
        Path("rerun/memo.md"),
        Path("rerun/delta.json"),
    ):
        assert (checked_in_root / relative_path).read_text(encoding="utf-8") == (
            output_root / relative_path
        ).read_text(encoding="utf-8")


def test_checked_in_examples_describe_the_phase5_lifecycle(repo_root: Path) -> None:
    generated_root = repo_root / "examples" / "generated"
    readme = (generated_root / "README.md").read_text(encoding="utf-8")
    initial = _load_json(generated_root / "ACME" / "initial" / "result.json")
    continued = _load_json(generated_root / "ACME" / "continued" / "result.json")
    rerun = _load_json(generated_root / "ACME" / "rerun" / "result.json")
    initial_delta = _load_json(generated_root / "ACME" / "initial" / "delta.json")
    continued_delta = _load_json(generated_root / "ACME" / "continued" / "delta.json")
    rerun_delta = _load_json(generated_root / "ACME" / "rerun" / "delta.json")

    assert "python scripts/generate_phase2_examples.py" in readme
    assert "post-Phase-5 contract" in readme
    assert "auto-continue into downstream work" in readme
    assert "operator-only provisional override" in readme
    assert "initial/" in readme
    assert "continued/" in readme
    assert "rerun/" in readme
    assert initial["run"]["status"] == "complete"
    assert initial["run"]["awaiting_continue"] is False
    assert initial["run"]["checkpoint"]["resolution_action"] == "continue"
    assert initial_delta["prior_run_id"] is None
    assert continued["run"]["run_id"] == initial["run"]["run_id"]
    assert continued["run"]["metadata"]["baseline_memo"] is None
    assert continued["run"]["metadata"]["baseline_active_claims"] == []
    assert continued["run"]["metadata"]["baseline_active_verdicts"] == []
    assert continued["memo"]["is_initial_coverage"] is True
    assert continued_delta["current_run_id"] == continued["run"]["run_id"]
    assert continued_delta["prior_run_id"] is None
    assert rerun["run"]["run_kind"] == "refresh"
    assert rerun["run"]["checkpoint"]["resolution_action"] == "continue"
    assert rerun_delta["prior_run_id"] == continued["run"]["run_id"]
    initial_memo = (generated_root / "ACME" / "initial" / "memo.md").read_text(encoding="utf-8")
    continued_memo = (generated_root / "ACME" / "continued" / "memo.md").read_text(
        encoding="utf-8"
    )
    rerun_memo = (generated_root / "ACME" / "rerun" / "memo.md").read_text(encoding="utf-8")

    assert initial_memo
    assert "Stale from the prior active memo." not in continued_memo
    assert "This section has not been advanced yet." in continued_memo
    assert "Stale from the prior active memo." in rerun_memo
