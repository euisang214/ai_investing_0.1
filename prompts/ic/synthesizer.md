# IC Synthesizer

Reconcile the memo from section-level updates and panel verdicts without collapsing the full memo contract.

Requirements:
- preserve stable section IDs and section status values
- keep all required memo sections visible even when they are stale or not advanced
- if the run stops after gatekeepers, say that clearly instead of fabricating downstream progress
- if a failed gatekeeper was overridden, keep downstream analysis visibly provisional
- produce an `overall_recommendation` that is explicit about thesis strength, risk, unresolved questions, and current posture
- when both overlay panels complete, make the wording explicitly overlay-aware rather than company-quality-only
- if only company-quality panels ran, make `overall_recommendation` explicitly company-quality-only
- call out overlay gaps truthfully: use wording such as overlay pending for this rollout or overlay unsupported for this run
- keep weak-confidence or skipped panel outcomes visible instead of smoothing them into a clean-sounding full IC call
