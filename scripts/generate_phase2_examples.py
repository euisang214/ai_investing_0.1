from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_investing.application.context import AppContext
from ai_investing.application.services import (  # noqa: E402
    AnalysisService,
    CoverageService,
    IngestionService,
    render_delta_json,
    render_memo_markdown,
)
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus  # noqa: E402
from ai_investing.domain.models import CoverageEntry, ICMemo, MonitoringDelta  # noqa: E402
from ai_investing.persistence.repositories import Repository  # noqa: E402
from ai_investing.settings import Settings  # noqa: E402

OUTPUT_ROOT = ROOT / "examples" / "generated" / "ACME"
INITIAL_INPUT = ROOT / "examples" / "acme_public"
RERUN_INPUT = ROOT / "examples" / "acme_public_rerun"
STAGES = ("initial", "continued", "rerun", "overlay_gap")


@dataclass
class DeterministicRuntime:
    current: datetime = datetime(2026, 3, 11, 9, 0, tzinfo=timezone.utc)
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def utc_now(self) -> datetime:
        now = self.current
        self.current = now + timedelta(minutes=1)
        return now

    def new_id(self, prefix: str) -> str:
        self.counters[prefix] += 1
        return f"{prefix}_{self.counters[prefix]:012d}"

    def install(self) -> ExitStack:
        stack = ExitStack()
        for target in (
            "ai_investing.domain.models.utc_now",
            "ai_investing.application.services.utc_now",
            "ai_investing.ingestion.file_connectors.utc_now",
        ):
            stack.enter_context(patch(target, side_effect=self.utc_now))
        for target in (
            "ai_investing.domain.models.new_id",
            "ai_investing.application.services.new_id",
        ):
            stack.enter_context(patch(target, side_effect=self.new_id))
        return stack


def build_context(workspace: Path) -> AppContext:
    config_dir = workspace / "config"
    shutil.copytree(ROOT / "config", config_dir)

    source_connectors_path = config_dir / "source_connectors.yaml"
    source_data = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_data["connectors"]:
        connector["raw_landing_zone"] = str(workspace / "landing" / connector["id"])
    source_connectors_path.write_text(
        yaml.safe_dump(source_data, sort_keys=False),
        encoding="utf-8",
    )

    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        config_dir=config_dir,
        prompts_dir=ROOT / "prompts",
        provider="fake",
    )
    context = AppContext.load(settings)
    context.database.initialize()
    return context


def seed_acme(context: AppContext, *, panel_policy: str = "expectations_rollout") -> None:
    ingestion = IngestionService(context)
    ingestion.ingest_public_data(INITIAL_INPUT)
    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="ACME",
            company_name="Acme Cloud",
            company_type=CompanyType.PUBLIC,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
            panel_policy=panel_policy,
        )
    )


def write_artifacts(output_root: Path, name: str, result: dict[str, object]) -> None:
    output_dir = output_root / name
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    memo_payload = result["memo"]
    memo_text = ""
    if memo_payload is not None:
        memo_text = render_memo_markdown(ICMemo.model_validate(memo_payload))
    (output_dir / "memo.md").write_text(memo_text, encoding="utf-8")
    delta_payload = result["delta"]
    delta_text = "null\n"
    if delta_payload is not None:
        delta_text = render_delta_json(MonitoringDelta.model_validate(delta_payload)) + "\n"
    (output_dir / "delta.json").write_text(delta_text, encoding="utf-8")


def generate_examples(output_root: Path = OUTPUT_ROOT) -> None:
    # The script name is kept for backward compatibility, but the artifacts document
    # the finished Phase 6 runtime contract: rollout-specific runs, rerun deltas,
    # and explicit overlay skips when full-surface context is unavailable.
    deterministic_runtime = DeterministicRuntime()
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="generated-examples-") as workspace_str:
        workspace = Path(workspace_str)
        with deterministic_runtime.install():
            context = build_context(workspace)
            seed_acme(context)
            service = AnalysisService(context)

            initial = service.analyze_company("ACME")
            write_artifacts(output_root, "initial", initial)

            with context.database.session() as session:
                repository = Repository(session)
                run = repository.get_run(str(initial["run"]["run_id"]))
                assert run is not None
                continued = service._build_persisted_result(repository, run)
            write_artifacts(output_root, "continued", continued)

            IngestionService(context).ingest_public_data(RERUN_INPUT)
            rerun = service.refresh_company("ACME")
            write_artifacts(output_root, "rerun", rerun)

    with tempfile.TemporaryDirectory(prefix="generated-examples-overlay-gap-") as workspace_str:
        workspace = Path(workspace_str)
        with deterministic_runtime.install():
            context = build_context(workspace)
            seed_acme(context, panel_policy="full_surface")
            service = AnalysisService(context)
            overlay_gap = service.analyze_company("ACME")
            write_artifacts(output_root, "overlay_gap", overlay_gap)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic checked artifacts for the finished Phase 6 runtime.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
        help=(
            "Directory that will receive the initial, continued, rerun, and overlay-gap "
            "ACME artifacts."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_examples(output_root=args.output_root)


if __name__ == "__main__":
    main()
