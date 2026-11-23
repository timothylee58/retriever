# Retriever

Retriever gets Singapore and Malaysia SMEs paid. It turns a failed card or an expired QR into a fresh PayNow or DuitNow link, matches transfers that arrived without a reference, and warns when a cash gap is cheaper to close with a small early-payment discount than to finance.

This repository was scaffolded from `PRD.md`, `architecture.md`, `schema.md`, `flow.md`, `implementation-plan.md`, and `progress.md` for HitPay Build Night. The demo story is Mei Ling’s tuition centre: declined cards, expired QR codes, and bank lines like “S$320 TAN” that match no invoice.

**This build is a dry-run.** `DRY_RUN=true` does not call live HitPay or Stripe. Providers are exercised with signed fixtures. See [CHALLENGES.md](CHALLENGES.md) for every bug found while scaffolding and the workaround that shipped.

## What it does

| ID | Behaviour in this scaffold |
|---|---|
| F1 | `POST /api/invoices` issues an invoice and stores a HitPay payment request whose reference is the invoice ref. In dry-run the URL and QR are synthetic. |
| F2 | `POST /webhooks/hitpay` and `POST /webhooks/stripe` verify a signature, insert `webhook_inbox` (duplicates return 200), and enqueue `process_webhook`. |
| F3 | Tier 1 matches an exact reference and currency. Tier 2 matches one open invoice with the same amount, a known payer name, and a due date within 30 days. |
| F4 | Anything else becomes a suggestion (`rules-v1`, or Grok when `XAI_API_KEY` is set) and an approval. Tier 3 never auto-applies. |
| F5, F11, F18 | A failed attempt opens one rescue. The fallback never repeats the method that failed. Singapore defaults to PayNow. The message is shown as sent on the dashboard. |
| F6 | `POST /api/churn/sweep` marks offered rescues older than `CHURN_AFTER_DAYS` as churned. A later match moves a churned rescue to `won_back`. |
| F8 | Every transition inserts an `events` row. A trigger rejects `UPDATE` and `DELETE` on that table. |
| F9 | The Next.js dashboard shows metrics, the queue, rescues, the audit feed, and an invoice form. |
| F13, F14 | EarlyBird builds a 14-day balance series and proposes a discount only when the discount costs less than the financing cost of the gap. Six tools are exposed at `POST /mcp`. |
| F20 | A refund row cannot be submitted until its approval is approved. Dry-run marks the provider refund succeeded and adds `amount_refunded_minor`. |

Not in this round: live HitPay MCP (F7), Stripe Custom Payment Methods (F15), the payee bank-detail guard and recurring rescue (F12, Phase 5), WhatsApp (F16), and the demo video (F10).

## Architecture

```
Payer ── card (Stripe test) ─────────────┐
       └─ PayNow / DuitNow (HitPay) ──────┤
                                          ▼
                              FastAPI  /webhooks/*  → webhook_inbox → jobs
                                       /api/*       → invoices, approvals, rescues, forecast
                              Worker   SKIP LOCKED  → matcher, rescue, forecast
                                          │
                         Postgres ledger  │  Grok (optional) for tier-3 suggestions
                                          ▼
                              Next.js dashboard (shared demo password)
```

Money is integer minor units plus a currency code. The ledger is the state machine. The model only proposes a match or a sentence. It does not move money. Refunds run only after an approval, and in this scaffold that call is simulated.

## MCP tools

`POST /mcp` with `{"name","arguments"}`:

| Tool | Effect |
|---|---|
| `get_recovery_summary` | Recovered count, failure count, recovery rate, churn rate, amount at risk |
| `list_open_rescues` | Rescues in `opened` or `offered` |
| `list_unmatched_payments` | Pending approvals |
| `get_cash_forecast` | Builds the 14-day forecast |
| `ingest_hitpay_snapshot` | Stores `balance_minor` on the merchant settings |
| `propose_discount_offer` | Runs the forecast and, when the cost test passes, creates a discount approval |

## Run locally

Requirements: Postgres listening on port 5432, Python 3.12+, Node 22.

```bash
createdb retriever    # the test suite creates retriever_test itself
python3 -m venv .venv
.venv/bin/pip install -e "./api[dev]"
cp .env.example .env
.venv/bin/python -c "from app.db import make_engine, apply_schema; from app.config import get_settings; e=make_engine(get_settings().database_url); apply_schema(e)"
.venv/bin/uvicorn app.main:app --app-dir api --reload --port 8000

cd web && npm install && DEMO_PASSWORD=retriever-demo npm run dev
```

Open http://localhost:3000 and sign in with `retriever-demo`.

Tests:

```bash
.venv/bin/pytest api/tests -q
```

Eleven tests cover the currency guard, tier 2’s single-candidate rule, SG/MY fallback, signatures, exact match, duplicate and bad webhooks, the review queue, a Stripe decline that becomes a PayNow rescue and then a recovery, partial payment plus overpayment, and approval-gated refunds.

## Environment

See `.env.example`. Secrets stay in `.env`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URL, SQLAlchemy + psycopg |
| `DRY_RUN` | `true` skips outbound HitPay writes |
| `HITPAY_API_KEY`, `HITPAY_WEBHOOK_SALT`, `HITPAY_API_BASE` | Sandbox REST and the assumed HMAC salt |
| `STRIPE_WEBHOOK_SECRET` | Verifies `Stripe-Signature` (`t=`, `v1=` HMAC-SHA256) |
| `XAI_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Grok via the OpenAI-compatible xAI API. Empty key uses rules |
| `DEMO_PASSWORD` | Shared password for the dashboard cookie |
| `CHURN_AFTER_DAYS` | Default 7 |

## Demo path (no live providers)

1. Create `INV-104` for S$420 on the Invoices page.
2. Post a Stripe `payment_intent.payment_failed` fixture (see `api/tests/test_ledger.py`). The rescue sheet shows a PayNow message.
3. Post a HitPay `completed` body with no reference. The Queue page asks for one approval.
4. `POST /api/forecast` after `ingest_hitpay_snapshot` sets a low opening balance. A discount approval appears only when the discount is cheaper than the gap.

The three-minute video, the email to ria@hit-pay.com, and the live HitPay MCP login are still Phase 4 and were not done here.

## Challenges

The full table is [CHALLENGES.md](CHALLENGES.md). The ones that change how you read this code:

- The previous progress note claimed a finished scaffold. It was not in the folder.
- HitPay’s HMAC algorithm is implemented as SHA-256 until a real `hitpay trigger` payload says otherwise.
- Job processing runs inside the webhook request so a single process can complete a flow.
- Overpayments and the refund’s approval pointer do not fit the approval kinds and insert order in the spec; the event log and a payment-id subject are the stand-ins.
- Phase 5 (supplier bank-detail changes and recurring-charge rescue) is not migrated yet.
