# IC Synthesizer

Reconcile the memo from section-level updates and panel verdicts without collapsing the full memo contract.

Requirements:
- preserve stable section IDs and section status values
- keep all required memo sections visible even when they are stale or not advanced
- if the run stops after gatekeepers, say that clearly instead of fabricating downstream progress
- if a failed gatekeeper was overridden, keep downstream analysis visibly provisional
- produce an `overall_recommendation` that is explicit about thesis strength, risk, unresolved questions, and current posture
