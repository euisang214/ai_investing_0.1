# Phase 13: Operator Documentation And Closeout - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Create clear, actionable documentation so an operator can take the system from git clone to production without hidden knowledge. Produce a formal milestone closeout artifact summarizing the full v2.0 milestone.

</domain>

<decisions>
## Implementation Decisions

### README Structure
- Extend the existing README with new sections rather than splitting into separate files.
- Add "Production Setup" and "Test vs Production" sections directly into README.md.

### Vendor Dashboard Coverage
- Document setup steps for all 4 providers: OpenAI, Anthropic, Google (Gemini), and Groq.
- Include the OpenAI-compatible generic endpoint as a fifth option.
- Each provider section should include: account creation link, API key generation steps, required env var names, and a link to the vendor dashboard.

### Milestone Closeout Artifact
- Produce a formal `v2.0-CLOSEOUT.md` summarizing the full milestone.
- This should cover: what was delivered across all phases, requirement traceability, and the final state of the system.

### Claude's Discretion
- **Section ordering**: Where exactly in the README the new sections go relative to existing content.
- **Level of detail**: How much prose vs. code blocks in the production guide.
- **Closeout format**: Internal structure of the v2.0-CLOSEOUT.md artifact.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md`: 161 lines, covers runtime description, panel surface, run policies, support contract, quick start, queue operations, and generated artifacts.
- `docs/architecture.md`, `docs/runbook.md`: Existing operator-facing documentation.
- `.env.example` or equivalent: May need creation if not present.
- `settings.py`: All configurable env vars live here with `AI_INVESTING_` prefix.

### Established Patterns
- Provider selection: `AI_INVESTING_PROVIDER` env var.
- API key env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENAI_COMPATIBLE_API_KEY`.
- Model env vars per profile in `config/model_profiles.yaml`.
- Auth: `AI_INVESTING_API_KEYS` env var with role-based keys.
- Docker profiles: `dev` and `prod` via `docker compose --profile`.

### Integration Points
- `README.md` — primary target for new sections.
- `.planning/` — location for the closeout artifact.

</code_context>

<specifics>
## Specific Ideas

- None — standard documentation approach.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-operator-documentation-and-closeout*
*Context gathered: 2026-03-15*
