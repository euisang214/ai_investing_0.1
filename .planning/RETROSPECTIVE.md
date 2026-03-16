# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v2.0 — Productionization

**Shipped:** 2026-03-16
**Phases:** 5 | **Plans:** 6

### What Was Built
- 5 LLM provider adapters with chain fallback and retry resilience (exponential backoff on 429/5xx)
- Structured JSON logging with per-agent token tracking and Postgres persistence
- API key authentication middleware with role-based authorization (operator/readonly)
- Multi-stage Dockerfile with /health and /ready probes, dev/prod profiles, credential safety
- Per-run token budget cap with graceful mid-run abort and cost estimation via rate cards
- GitHub Actions CI pipeline running lint, type check, and full test suite with fake provider
- Complete README production setup guide with vendor dashboard links for all providers
- v2.0 closeout artifact with full requirement traceability (21/21 requirements satisfied)

### What Worked
- Documentation-as-last-phase pattern: writing production documentation after all features are implemented ensures accuracy
- Config-driven provider chain: adding new providers (Gemini, Groq, OpenAI-compatible) was straightforward because the adapter pattern was established in Phase 9
- Yolo mode execution: phases 9–13 were relatively small in scope after the core platform was solid, enabling rapid sequential execution
- Retroactive SUMMARY.md recovery: git commit history was sufficient to reconstruct missing metadata

### What Was Inefficient
- Phase 12 execution didn't produce a SUMMARY.md, requiring retroactive creation — commit discipline should be consistent across all phases
- ROADMAP phase table got corrupted (rows for phases 10, 11 lost their names, showing only plan counts) — the gsd-tools update command may not handle all table formats gracefully
- v1.0 milestone was never formally closed (no MILESTONES.md entry, no v1.0 archival) — milestone closure should happen immediately after the last phase

### Patterns Established
- Provider adapter pattern: base class with `generate_structured()` and `generate_structured_with_usage()`, optional dependency installs via extras
- Middleware exemption pattern: `_EXEMPT_PATHS` frozenset check at top of `dispatch()` for health/ready
- Credential safety gate: standalone validation function called at `AppContext.load()` startup

### Key Lessons
1. Close milestones immediately when the last phase completes — accumulating milestone debt makes archival harder
2. Per-phase SUMMARY.md creation should be enforced as part of the commit workflow, not optional
3. Small production-hardening phases (security, deployment, CI) execute quickly when the core architecture is solid — scope them confidently

### Cost Observations
- Model mix: 100% sonnet (executor and verifier)
- Sessions: ~5 for phases 9–13
- Notable: documentation-only Phase 13 completed in under 5 minutes — pure docs phases are efficient

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 8 | 26 | Established core platform with config-driven orchestration |
| v2.0 | 5 | 6 | Productionized: real providers, security, deployment, CI/CD |

### Top Lessons (Verified Across Milestones)

1. Config-driven architecture pays off in later phases — adding providers, panels, and policies requires minimal code changes
2. Docker-first development keeps host environment issues from blocking progress (Python 3.9 host vs 3.11+ target)
3. Generate-and-lock artifacts (ACME examples) catch regressions that unit tests miss
