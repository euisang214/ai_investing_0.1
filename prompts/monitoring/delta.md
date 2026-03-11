# Monitoring Delta

Compare the current run against the prior active run using structured claim, verdict, and memo posture changes instead of raw wording churn.

Requirements:
- treat confidence moves below `0.05` as immaterial unless the claim meaning also changed
- always refresh `what_changed_since_last_run` because it is the run-log section
- emphasize recommendation shifts, gatekeeper changes, risk movement, and real thesis drift
- avoid calling out purely cosmetic memo rewrites as material changes
