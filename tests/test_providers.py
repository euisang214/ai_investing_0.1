from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ai_investing.application.context import AppContext
from ai_investing.config.models import ModelProfileConfig, ProviderChainEntry
from ai_investing.providers.fake import FakeModelProvider
from ai_investing.settings import Settings


def _copy_config(repo_root: Path, tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)
    return config_dir


def _settings_for(
    repo_root: Path,
    config_dir: Path,
    *,
    provider: str = "fake",
    allow_fake_fallback: bool = True,
) -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        config_dir=config_dir,
        prompts_dir=repo_root / "prompts",
        provider=provider,
        allow_fake_fallback=allow_fake_fallback,
    )


class TestProviderChainConfig:
    def test_provider_chain_entry_validates_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unsupported provider"):
            ProviderChainEntry(provider="mystery", model="some-model")

    def test_provider_chain_entry_defaults_api_key_env(self) -> None:
        entry = ProviderChainEntry(provider="openai", model="gpt-4o")
        assert entry.api_key_env == "OPENAI_API_KEY"

    def test_provider_chain_entry_fake_has_no_api_key(self) -> None:
        entry = ProviderChainEntry(provider="fake", model="deterministic")
        assert entry.api_key_env is None

    def test_model_profile_config_validates_provider_chain(self) -> None:
        profile = ModelProfileConfig(
            provider_chain=[
                ProviderChainEntry(provider="openai", model="gpt-4o"),
                ProviderChainEntry(provider="fake", model="deterministic"),
            ],
            temperature=0.1,
            max_tokens=1800,
        )
        assert len(profile.provider_chain) == 2
        assert profile.provider_chain[0].provider == "openai"

    def test_model_profile_backward_compatibility_from_legacy(self) -> None:
        profile = ModelProfileConfig(
            primary_provider="fake",
            provider_order=["fake", "openai"],
            env_model_keys={"openai": "OPENAI_MODEL_BALANCED"},
            temperature=0.1,
            max_tokens=1800,
        )
        assert len(profile.provider_chain) == 2
        assert profile.provider_chain[0].provider == "fake"
        assert profile.provider_chain[1].provider == "openai"


class TestProviderChainResolution:
    def test_fake_provider_default(self, repo_root: Path, tmp_path: Path) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        ctx = AppContext.load(_settings_for(repo_root, config_dir))
        provider = ctx.get_provider("balanced")
        assert isinstance(provider, FakeModelProvider)

    def test_explicit_fake_provider(self, repo_root: Path, tmp_path: Path) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        ctx = AppContext.load(_settings_for(repo_root, config_dir, provider="fake"))
        provider = ctx.get_provider("balanced")
        assert isinstance(provider, FakeModelProvider)

    def test_fake_fallback_blocked(
        self, repo_root: Path, tmp_path: Path
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        ctx = AppContext.load(
            _settings_for(repo_root, config_dir, allow_fake_fallback=False)
        )
        # With no real API keys set and fake blocked, should raise
        with pytest.raises(RuntimeError, match="No valid provider found"):
            ctx.get_provider("balanced")

    def test_missing_api_key_skips_to_next(
        self, repo_root: Path, tmp_path: Path
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        # No real API keys set — should skip real providers, land on fake
        ctx = AppContext.load(_settings_for(repo_root, config_dir, provider="auto"))
        provider = ctx.get_provider("balanced")
        assert isinstance(provider, FakeModelProvider)

    def test_explicit_missing_provider_raises(
        self, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        # Ask for anthropic explicitly but no API key
        ctx = AppContext.load(
            _settings_for(repo_root, config_dir, provider="anthropic")
        )
        with pytest.raises(RuntimeError, match="No valid provider found"):
            ctx.get_provider("balanced")

    def test_real_provider_with_key_requires_dependency(
        self, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        ctx = AppContext.load(_settings_for(repo_root, config_dir, provider="openai"))
        with pytest.raises(RuntimeError, match="Install ai-investing\\[openai\\]"):
            ctx.get_provider("balanced")

    def test_chain_order_prefers_first_valid(
        self, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        # quality tier has anthropic first, then openai
        # Set only openai key — should skip anthropic and use openai
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        ctx = AppContext.load(_settings_for(repo_root, config_dir, provider="auto"))
        # Will raise because langchain_openai isn't installed, but it means
        # it successfully skipped anthropic (no key) and tried openai
        with pytest.raises(RuntimeError, match="Install ai-investing\\[openai\\]"):
            ctx.get_provider("quality")

    def test_exhausted_chain_error_message_lists_providers(
        self, repo_root: Path, tmp_path: Path
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        ctx = AppContext.load(
            _settings_for(
                repo_root, config_dir, provider="auto", allow_fake_fallback=False,
            )
        )
        with pytest.raises(RuntimeError, match="openai.*missing env var") as exc_info:
            ctx.get_provider("balanced")
        assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_provider_chain_all_tiers_resolve_with_fake(
        self, repo_root: Path, tmp_path: Path
    ) -> None:
        config_dir = _copy_config(repo_root, tmp_path)
        ctx = AppContext.load(_settings_for(repo_root, config_dir))
        for tier in ("balanced", "quality", "budget"):
            provider = ctx.get_provider(tier)
            assert isinstance(provider, FakeModelProvider), tier
