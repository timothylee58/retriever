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

Automated tests:

```bash
.venv/bin/pytest api/tests -q
```

The suite stays offline. HitPay and Stripe are represented by signed fixtures, not live calls. The cases rewritten from the 23–24 Nov sandbox sessions are below. The rest cover the currency guard, tier 2, SG/MY fallback, the review queue, partial payment, overpayment, and approval-gated refunds.

## Environment

See `.env.example`. Secrets stay in `.env`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres URL, SQLAlchemy + psycopg |
| `DRY_RUN` | `true` skips outbound HitPay writes |
| `HITPAY_API_KEY`, `HITPAY_WEBHOOK_SALT`, `HITPAY_API_BASE` | Sandbox REST. The salt is the webhook endpoint salt, HMAC-SHA256 over the raw body |
| `STRIPE_WEBHOOK_SECRET` | The `whsec_…` printed by the current `stripe listen` session |
| `XAI_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Grok via the OpenAI-compatible xAI API. Empty key uses rules |
| `DEMO_PASSWORD` | Shared password for the dashboard cookie |
| `CHURN_AFTER_DAYS` | Default 7 |

## Sandbox sessions: HitPay and Stripe

These are the runs that actually worked on this machine. Custom Payment Method ids are not part of either path. `STRIPE_CPM_*` can stay empty.

### HitPay PayNow, SGD 420.00

The dashboard form rejects `http://127.0.0.1:8000/webhooks/hitpay`. `@hit-pay/cli` is also not on npm yet (`npm i -g @hit-pay/cli` returns 404). Install the CLI from source, then let `listen` register the public HTTPS tunnel:

```bash
git clone https://github.com/hit-pay/cli.git /tmp/hitpay-cli
cd /tmp/hitpay-cli && npm install && npm run build && npm link
hitpay login --api-key "$HITPAY_API_KEY"
hitpay whoami    # environment must say sandbox
```

The published `listen` command posts `{url, events}` and the sandbox answers `HITPAY_422`: `name` and `event_types` are required. The copy in `/tmp/hitpay-cli` was patched to send `name` plus `event_types` (`payment_request.completed`, `payment_request.failed`, `charge.created`, `charge.updated`). Rebuild with `npm run build` after that patch.

Start the API, then the tunnel, in two terminals:

```bash
cd /Users/apple/Retriever
.venv/bin/uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 8000

hitpay listen --forward-to http://127.0.0.1:8000/webhooks/hitpay
```

Copy the printed salt into `HITPAY_WEBHOOK_SALT` and start uvicorn again. A completed PayNow page is not enough on its own. One SGD 420.00 receipt (`a34baeee-9dba-4b81-878d-85c719394793`) stayed unpaid in Retriever because the webhook signature did not match and the API returned 401. After the salt matches, `POST /webhooks/hitpay` returns 200 and `INV-104` becomes `paid`.

Sandbox method name: send `paynow_online`, not `paynow`. This account also rejects a methods array that includes GrabPay or ShopeePay, so the request sends only the chosen fallback. `DRY_RUN=false` is what created the real checkout URL (`https://checkout.sandbox.hit-pay.com/...`). `DRY_RUN=true` stores a synthetic URL instead.

### Stripe decline card to PayNow

Card `4000 0000 0000 0002` is the generic decline. This Stripe CLI requires an event list:

```bash
stripe login
stripe listen --events payment_intent.payment_failed --forward-to http://127.0.0.1:8000/webhooks/stripe
```

Put that session’s `whsec_…` in `STRIPE_WEBHOOK_SECRET` and restart uvicorn. Create `INV-104` for S$420.00 first. The webhook reads `metadata.reference`.

```bash
stripe payment_intents create \
  --amount=42000 \
  --currency=sgd \
  --confirm \
  --payment-method-data[type]=card \
  --payment-method-data[card][number]=4000000000000002 \
  --payment-method-data[card][exp_month]=12 \
  --payment-method-data[card][exp_year]=2034 \
  --payment-method-data[card][cvc]=123 \
  -d "metadata[reference]=INV-104"
```

The API log should show `POST /webhooks/stripe` 200. `/rescues` then shows an `offered` row whose message contains a PayNow link for `INV-104`. Paying that link is the HitPay session above. `GET /v1/models` 404 lines in the API log are unrelated probes and can be ignored.

`test_stripe_decline_card_creates_paynow_rescue` and `test_unsigned_hitpay_webhook_does_not_mark_paid` in `api/tests/test_ledger.py` cover the same two outcomes without calling either provider.

The three-minute video, the email to ria@hit-pay.com, and the live HitPay MCP login are still open.

## Challenges

The full table is [CHALLENGES.md](CHALLENGES.md). The ones that change how you read this code:

- The previous progress note claimed a finished scaffold. It was not in the folder.
- HitPay event webhooks are HMAC-SHA256 over the raw body with that endpoint’s salt. A mismatched salt returns 401 and leaves the invoice unpaid.
- Job processing runs inside the webhook request so a single process can complete a flow.
- Overpayments and the refund’s approval pointer do not fit the approval kinds and insert order in the spec; the event log and a payment-id subject are the stand-ins.
- Phase 5 (supplier bank-detail changes and recurring-charge rescue) is not migrated yet.
