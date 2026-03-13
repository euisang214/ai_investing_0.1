# n8n Integration

These workflows show n8n acting as an external scheduler, webhook receiver, and notification dispatcher for the FastAPI service.

That boundary is strict:

- n8n may enqueue background refresh work
- n8n may forward webhook payloads into ingest and enqueue endpoints
- n8n may claim, dispatch, and acknowledge notification events
- n8n may not coordinate panel sequencing, memo updates, queue claims, or provisional continuation logic
- n8n may not read the database directly

## Stable Surfaces

Use only these service-owned boundaries from n8n:

- `POST /queue/enqueue-watchlist`
- `POST /queue/enqueue-portfolio`
- `POST /queue/enqueue-due`
- `POST /queue/enqueue-selected`
- `GET /queue`
- `POST /workers/run` only when an operator explicitly wants n8n to trigger worker polling; the reasoning runtime still stays inside the service
- `POST /companies/{company_id}/ingest-public`
- `GET /review-queue`
- `GET /notifications`
- `POST /notifications/claim`
- `POST /notifications/{event_id}/dispatch`
- `POST /notifications/{event_id}/acknowledge`

## Workflow Intent

- `weekly_watchlist_refresh.json`: submit a watchlist refresh batch into the queue and capture the resulting queue summary
- `weekly_portfolio_refresh.json`: submit a portfolio refresh batch into the queue and capture the resulting queue summary
- `new_evidence_webhook.json`: accept an inbound evidence webhook, call the ingest endpoint, then enqueue a refresh for the affected company
- `refresh_notification.json`: poll the notification outbox for immediate alerts and daily digest candidates, deliver them to one shared operator channel, then mark those events dispatched or acknowledged

## Gatekeeper Policy Reminder

The service owns run lifecycle decisions:

- every run still starts at `gatekeepers`
- `pass` and `review` auto-continue inside the service runtime
- `fail` enters the review queue and triggers an immediate notification
- provisional continuation remains operator-only through `continue-run --provisional`

n8n should never try to infer those decisions from memo text or trigger provisional continuation on its own.

## Daily Digest Expectation

The daily digest flow must include companies with no key changes. The notification event summary may say the run completed with no material changes; n8n should still include that company in the operator channel so the digest doubles as proof that the coverage processed successfully.
