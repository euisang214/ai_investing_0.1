from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_investing.domain.models import StructuredGenerationRequest, TokenUsageRecord
from ai_investing.persistence.repositories import Repository
from ai_investing.persistence.tables import Base
from ai_investing.providers.base import GenerationResult
from ai_investing.providers.fake import FakeModelProvider


def _make_db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


class TestTokenUsageRecord:
    def test_token_usage_record_defaults(self) -> None:
        record = TokenUsageRecord(
            run_id="run_1",
            panel_id="demand_revenue_quality",
            agent_id="demand_specialist",
            provider="openai",
            model="gpt-4o",
            input_tokens=500,
            output_tokens=200,
        )
        assert record.usage_id.startswith("tok_")
        assert record.input_tokens == 500
        assert record.output_tokens == 200
        assert record.estimated_cost_usd == 0.0

    def test_base_provider_returns_zero_tokens(self) -> None:
        """Base ModelProvider.generate_structured_with_usage returns zero tokens."""
        from unittest.mock import patch

        fake = FakeModelProvider()
        request = StructuredGenerationRequest(
            task_type="test",
            prompt="test",
            input_data={"key": "value"},
        )

        from pydantic import BaseModel

        class TestOutput(BaseModel):
            answer: str = "test"

        # Directly test the base class default by patching generate_structured
        with patch.object(fake, "generate_structured", return_value=TestOutput()):
            result = fake.generate_structured_with_usage(request, TestOutput)
        assert isinstance(result, GenerationResult)
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.provider == "unknown"


class TestTokenUsagePersistence:
    def test_save_and_list_token_usage(self) -> None:
        session_factory = _make_db()
        with session_factory() as session:
            repo = Repository(session)
            record = TokenUsageRecord(
                run_id="run_1",
                panel_id="demand_revenue_quality",
                agent_id="demand_specialist",
                provider="openai",
                model="gpt-4o",
                input_tokens=500,
                output_tokens=200,
                estimated_cost_usd=0.0032,
            )
            repo.save_token_usage(record)
            session.commit()

            records = repo.list_token_usage("run_1")
            assert len(records) == 1
            assert records[0].input_tokens == 500
            assert records[0].agent_id == "demand_specialist"

    def test_list_token_usage_by_panel(self) -> None:
        session_factory = _make_db()
        with session_factory() as session:
            repo = Repository(session)
            for panel_id, agent_id in [
                ("panel_a", "agent_1"),
                ("panel_a", "agent_2"),
                ("panel_b", "agent_3"),
            ]:
                repo.save_token_usage(
                    TokenUsageRecord(
                        run_id="run_1",
                        panel_id=panel_id,
                        agent_id=agent_id,
                        provider="openai",
                        model="gpt-4o",
                        input_tokens=100,
                        output_tokens=50,
                    )
                )
            session.commit()

            panel_a = repo.list_token_usage("run_1", panel_id="panel_a")
            assert len(panel_a) == 2

            panel_b = repo.list_token_usage("run_1", panel_id="panel_b")
            assert len(panel_b) == 1

    def test_per_run_aggregation(self) -> None:
        session_factory = _make_db()
        with session_factory() as session:
            repo = Repository(session)
            for i in range(3):
                repo.save_token_usage(
                    TokenUsageRecord(
                        run_id="run_agg",
                        panel_id="panel_x",
                        agent_id=f"agent_{i}",
                        provider="openai",
                        model="gpt-4o",
                        input_tokens=100 * (i + 1),
                        output_tokens=50 * (i + 1),
                        estimated_cost_usd=0.001 * (i + 1),
                    )
                )
            session.commit()

            records = repo.list_token_usage("run_agg")
            total_input = sum(r.input_tokens for r in records)
            total_output = sum(r.output_tokens for r in records)
            total_cost = sum(r.estimated_cost_usd for r in records)
            assert total_input == 600  # 100 + 200 + 300
            assert total_output == 300  # 50 + 100 + 150
            assert round(total_cost, 4) == 0.006

    def test_cost_estimation_reasonable(self) -> None:
        # GPT-4o: ~$2.50/1M input, ~$10/1M output
        input_cost = (1000 / 1_000_000) * 2.50  # $0.0025
        output_cost = (500 / 1_000_000) * 10.00  # $0.005
        total = input_cost + output_cost
        assert 0.005 < total < 0.01
