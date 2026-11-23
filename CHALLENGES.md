# Challenges and workarounds

Recorded while scaffolding Retriever on 23 Nov 2026 from the six spec files in this folder.

| Challenge | What went wrong | Workaround |
|---|---|---|
| Spec said the scaffold already existed | `progress.md` listed FastAPI, Next.js, Docker, CI, and 19 passing tests. This folder contained only the six markdown files. | Treated the documents as the source of truth and built the app from them. The old “19 tests” number is not this suite. This suite has 11 tests. |
| Docker was not running | `docker info` failed, so compose could not host Postgres. | Used the already-running local Postgres 17 on `localhost:5432`. Tests create `retriever_test` and truncate it. Compose remains for machines that have Docker. |
| Interpreter is Python 3.14 | The architecture asks for 3.12. This Mac’s `python3` is 3.14.6. | The code uses 3.12-compatible syntax. CI pins 3.12. Local tests ran on 3.14. |
| GitHub token is invalid | `gh auth status` reports the keyring token for `timothylee58` is invalid. | The repo was prepared locally. Publishing needs `gh auth refresh -h github.com` and then `gh repo create`. |
| HitPay signature algorithm is unverified | PRD Q1 says the header is HMAC over the raw body, and the hash algorithm still had to be confirmed with `hitpay trigger`. | Implemented hex HMAC-SHA256 and constant-time compare. If a real sandbox payload uses another digest, only `app/signatures.py` should change. |
| No live HitPay or Stripe account in this session | Phase 0 needs a sandbox key, webhook salt, and `stripe listen`. Those were not available. | `DRY_RUN=true` stores a fake payment URL and QR. Webhook tests sign fixtures locally. Setting `DRY_RUN=false` plus `HITPAY_API_KEY` turns on the REST create call. |
| Failure webhooks may not exist | PRD Q2 is still open. | The normaliser accepts HitPay `failed` and `expired` when they arrive. A polling abandon job is not built yet. |
| `payment_method[]` binding | Passing a Python list through SQLAlchemy `text()` does not become a Postgres enum array. | The writer sends a literal such as `{paynow,grabpay}` and casts it. |
| Tests hung after the first database test | `db.connect()` without closing left a transaction open. The next test’s `TRUNCATE` waited forever on that lock. | Every read uses `with engine.connect()`. A killed pytest can still leave a session; `pg_terminate_backend` clears it. |
| Webhook work runs in the request | The spec wants a 200 in under 500 ms and a separate worker. | The handler queues the job, then calls `process_jobs` before returning, so one process can finish a demo without a second worker. A production process should call `process_jobs` on its own loop. |
| Tier 3 must not auto-match | Architecture says only tiers 1 and 2 may auto-apply in the demo. | LLM and rules suggestions always create an approval, even above 0.9. |
| Grok is optional | No `XAI_API_KEY` was provided. | `app/llm.py` calls `https://api.x.ai/v1` when the key is set. Any error, or a missing key, uses `rules-v1` and still queues the payment. |
| Overpayment has no approval kind | The schema’s approval kinds are match, discount, payee release, and refund. The flow asks for an overpayment note. | The remainder stays unallocated and is written as `payment.overpaid` on the append-only event log. |
| Refund approval cannot point at a refund that does not exist yet | `approvals.subject_id` is a single uuid, and the refund row needs the approval id. | The approval stores the payment id. The refund row stores the approval id. The UI should join that way. |
| Phase 5 tables were left out | Payees, subscriptions, and the bank-detail guard are after the deadline. This session stopped at the Should-haves. | `sql/0001_schema.sql` has no `payees` or `subscriptions`. Adding them later is a new migration, not an edit that rewrites history. |
| Append-only trigger does not see `TRUNCATE` | `BEFORE UPDATE OR DELETE` does not fire for `TRUNCATE`. | Tests are allowed to truncate. Application code never does. |
| Compose publishes Postgres on 5432 | This Mac already uses 5432 for Postgres 17. Starting compose as written would fail to bind. | For Docker, change the host port. Local development uses the existing server and does not start compose. |
| Demo cookie stores the password | The shared password is the cookie value, so anyone who can read it can sign in. | Acceptable only for a single demo password. Replace with a session id before any real merchant data. |
| Dashboard stack was slimmed | The architecture names shadcn, Framer Motion, and Recharts. Installing that kit was not needed to prove the pages. | Next.js 15 App Router, a shared-password cookie, and plain CSS. Metric, queue, rescue, audit, and invoice pages call the API. |
| Stripe Custom Payment Methods | F15 needs a business-verified Stripe account and `cpmt_…` ids. That was out of this session’s scope. | Card declines are modelled as `payment_intent.payment_failed` fixtures and rescued with a PayNow link (F11) in dry-run. |
| Metric views are not merchant-scoped | `v_recovery` and `v_at_risk` scan every row. Fine for one demo merchant. | Add `merchant_id` to the views before a second merchant is inserted. |
| Events ignore unknown webhook types with a random subject id | An ignored webhook has no domain row to point at. | The event still records the reason. The subject id is a new uuid, not a foreign key. |
