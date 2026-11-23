# Retriever: architecture and tech stack

Companion to `PRD.md`. Data model in `schema.md`, sequences in `flow.md`.

## 1. Principles

1. **Ledger first, AI at the edges.** Invoice and payment state is a deterministic state machine in Postgres. The LLM only classifies failures, proposes matches for unclear payments, and drafts messages. Its output is validated against a schema and never moves state on its own below the confidence threshold.
2. **Receive fast, process later.** Webhook handlers verify, store the raw event, and return 200. Processing runs from a job queue, so provider retries are harmless and spikes don't drop events.
3. **Idempotent everywhere.** Unique keys on provider event IDs and on outbound request keys (`invoice.ref`, `rescue.id`).
4. **Append-only audit.** Every state change writes an `events` row. Nothing is updated or deleted there.
5. **No money moves without a human.** The agent creates payment links and requests. Refunds use HitPay's REST API and run only from an approved approval row. Approvals gate everything else.
6. **One region, two currencies.** SGD and MYR from day one; amounts stored as integer minor units with an explicit currency.

## 2. System context

```
                  ┌──────────────────────── Payers ───────────────────────┐
                  │  card (Stripe)     PayNow / DuitNow QR (HitPay)        │
                  └──────┬───────────────────────────┬────────────────────┘
                         │                           │
                  ┌──────▼──────┐             ┌──────▼──────┐
                  │   Stripe    │             │   HitPay    │◄────── HitPay MCP (live, OAuth)
                  │ (test mode) │             │  (sandbox)  │        used by Claude as operator
                  └──────┬──────┘             └──────┬──────┘
             webhooks    │                           │  webhooks + REST
                         ▼                           ▼
         ┌───────────────────────────────────────────────────────────┐
         │                Retriever API (FastAPI, Python)             │
         │  /webhooks/stripe  /webhooks/hitpay  → webhook_inbox       │
         │  /api/* (invoices, queue, approvals, churn, forecast)      │
         │  Worker: matcher · rescue agent · EarlyBird · sweep         │
         │  Retriever MCP server (6 tools)                             │
         └───────────┬───────────────────────────────┬───────────────┘
                     │ SQL                            │ HTTPS (structured output)
              ┌──────▼──────┐                  ┌──────▼──────┐
              │  Postgres   │                  │     LLM     │
              │ (Supabase)  │                  │  provider   │
              └──────▲──────┘                  └─────────────┘
                     │ REST (/api)
              ┌──────┴──────────────────┐
              │ Dashboard (Next.js 15)   │  owner + bookkeeper
              └─────────────────────────┘
```

## 3. Components

| Component | Responsibility | Notes |
|---|---|---|
| **Webhook ingest** | Verify signature, insert into `webhook_inbox` (unique on provider + event id), enqueue job, return 200 | Raw body kept for replay and audit |
| **Normaliser** | Maps Stripe and HitPay payloads into one `payments` / `payment_attempts` shape | Provider-specific code lives only here and in `providers/` |
| **Matcher** | Tier 1: exact reference. Tier 2: amount + payer + date window (rules). Tier 3: LLM suggestion for leftovers | Confidence ≥ 0.9 auto-applies only for tiers 1–2; tier 3 always goes to the queue in the demo |
| **Rescue agent** | Classifies failure (`declined`, `expired`, `abandoned`), creates fallback HitPay PayNow/DuitNow link, drafts message | Uses decline codes from Stripe; HitPay status or polling fallback |
| **Churn sweep** | Daily: rescues open > `CHURN_AFTER_DAYS` → `churned`; later payment → `won_back` | `POST /api/churn/sweep`, cron in prod |
| **Protect** (Phase 5) | Payee bank-detail guard + recurring charge rescue | Not in the demo |
| **EarlyBird** | 14-day forecast from payouts + open invoices + expected payments; offers a discount link if `discount_cost < gap_cost` | Simple, explainable arithmetic, no ML |
| **Approvals** | Queue of decisions (match, discount, payee release); records approver, reason, timestamp | Every decision writes `events` |
| **Retriever MCP server** | Exposes Retriever to assistants (see §6) | Read tools + "propose" tools only |
| **Dashboard** | Owner view: metrics, queue, rescue timeline, forecast, audit trail | See `design.md` |

## 4. Tech stack

| Layer | Choice | Why |
|---|---|---|
| API and worker | **Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 / asyncpg** | Already scaffolded (19 tests passing); Pydantic validates LLM output |
| Jobs | **Postgres job table with `SELECT … FOR UPDATE SKIP LOCKED`** | No extra infra; scales to thousands of events/min; swap for Redis/RQ or Cloud Tasks later |
| Database | **Postgres (Supabase in cloud, Docker locally)** | Constraints for the state machine, RLS when multi-tenant |
| Dashboard | **Next.js 15 (App Router), TypeScript, Tailwind, shadcn/ui, Framer Motion, Recharts** | Already scaffolded; typechecks and builds |
| AI | One LLM provider behind an interface; structured JSON output validated by Pydantic | Deterministic fallbacks when the LLM is down |
| HitPay | **REST API (sandbox)**: payment requests, recurring billing, refunds, webhooks; **Claude Code plugin / Agent Skills / CLI** for building and testing; **hosted MCP** (live, OAuth) for business-management reads and link creation in the demo | See §5 for the full surface map |
| Stripe | **Test mode**: PaymentIntents, `payment_intent.payment_failed` decline codes; optional HitPay Custom Payment Method | Bonus points; F15 only if test mode works in ≤ 1 hour |
| Email (optional) | Resend | Rescue messages otherwise shown as "sent" in the dashboard |
| Packaging | Dockerfiles + docker-compose (api, worker, web, db) | Already present |
| CI | GitHub Actions: ruff, mypy, pytest; eslint, tsc, next build | Already present |
| Hosting | API + worker on Cloud Run or Fly; web on Vercel; Postgres on Supabase | Matches the move off Railway |

## 5. Integrations

### HitPay: full API suite (verify fields marked ⚠ against `openapi.json` or the sandbox)

All of HitPay's merchant APIs are available; Retriever uses each one where it fits. All REST calls go through `app/providers/hitpay/` and read the base URL from env (`https://api.sandbox.hit-pay.com` or live).

| Capability | Surface | Retriever use | Detail |
|---|---|---|---|
| **Payment requests** | REST `POST /v1/payment-requests` | Collect (F1), rescue links (F5), discount links (F13) | `amount`, `currency` (SGD/MYR), `reference_number` = invoice ref, `payment_methods[]` to steer the fallback method, `email`, `webhook`, `redirect_url`, expiry ⚠ |
| **Embedded QR** | REST payment request with QR generation ⚠ | Show PayNow/DuitNow QR in the dashboard and inside Stripe's Payment Element | See "Embedded QR Code Payments" guide |
| **Recurring billing** | REST recurring plans and recurring billing ⚠ | Later: rescue failed recurring charges (F12 Protect, Phase 5) | Auto-charge supports cards, ShopeePay, GrabPay, Touch 'n Go; QR methods need a per-cycle payment |
| **Refunds** | REST refund endpoint ⚠ | Approval-gated refunds (F20) | Full and partial; result confirmed by webhook or charge status ⚠ |
| **Webhooks** | Webhook endpoints (**Developers → Webhook Endpoints**) | Single source of payment state (F2) | `Hitpay-Signature` header = HMAC over the **raw** body using **that endpoint's salt**; statuses `completed` / `failed` / `expired` ⚠ |
| **Business management** | Hosted MCP + REST | Balances, payouts, charges, orders, invoices, products for EarlyBird and the operator assistant | MCP is live-only, 30 req/min, owners/admins; write tools limited to `create_payment_link`, `create_invoice`, `create_product`, `create_recurring_plan` |
| **Abandoned detection fallback** | Poll payment request / `list_charges` | Rescue when no failure event exists | PRD Q2 |

### HitPay AI tooling (how we satisfy "must use HitPay's MCP server and AI tooling")

| Tool | Auth | Mode | What we use it for |
|---|---|---|---|
| **Claude Code plugin** (28 tools, 5 skills, 4 slash commands) | API key + salt, `HITPAY_ENV=sandbox` | Sandbox | Generating the provider adapter and webhook handler; creating test payment requests during development. Install: `/plugin marketplace add hit-pay/claude-code-plugin` then `/plugin install hitpay@hitpay-plugins` |
| **Hosted MCP server** `https://mcp.hit-pay.com/` | HitPay login (OAuth) | Live only | Operator assistant in the demo: `get_balances`, `list_payouts`, `list_charges`, `create_payment_link`. Add with `claude mcp add --transport http hitpay https://mcp.hit-pay.com/`, then `/mcp` → Authenticate |
| **HitPay CLI** `@hit-pay/cli` | API key | Sandbox | `hitpay listen --forward-to http://localhost:8000/webhooks/hitpay`; `hitpay trigger` for fixtures |
| **Agent Skills** `npx skills add hit-pay/agent-skills` | API key in app env | Sandbox | Reference for refunds, embedded QR and webhook verification code |
| **LLM-ready docs** `llms.txt`, `llms-full.txt`, `openapi.json` | none | — | Ground truth for fields marked ⚠ |
| HitPay for Vercel (`HITPAY_ACCESS_TOKEN`) | OAuth | **Live** | Not used for the demo: payments would be real |

### Payment methods matrix

| Method | Market | Primary | Rescue fallback | Recurring auto-charge | Sandbox (Q6) |
|---|---|---|---|---|---|
| PayNow QR | SG | ✅ | ✅ default SG | ❌ per-cycle payment | ✅ |
| DuitNow QR | MY | ✅ | ✅ default MY | ❌ per-cycle payment | ⚠ |
| FPX (online banking) | MY | ✅ | ✅ B2B MY | ❌ | ⚠ |
| Touch 'n Go eWallet | MY | ✅ | ✅ if payer used it before | ✅ | ✅ recurring |
| Boost | MY | ✅ | ✅ if payer used it before | ⚠ | ⚠ |
| GrabPay | SG, MY | ✅ | ✅ | ✅ | ✅ |
| ShopeePay | SG, MY | ✅ | ✅ | ✅ | ✅ |
| Cards (Visa, Mastercard, Amex) | Global | ✅ | ❌ (card is what failed) | ✅ | ✅ test card 4242… |
| Atome (BNPL) | SG, MY | optional | ❌ | ❌ | ✅ |

Fallback selection (`app/domain/fallback.py`): merchant country → payer's last successful method → country default (PayNow / DuitNow) → FPX for MY B2B over RM 5,000. Never offer the method that just failed.

### Stripe

| Use | Detail |
|---|---|
| Card failure source | Test card `4000 0000 0000 0002` (generic decline) or other decline cards; webhook `payment_intent.payment_failed` with `last_payment_error.decline_code` |
| Signature | `Stripe-Signature` header, `stripe.Webhook.construct_event` |
| **Custom Payment Methods (bonus, F15)** | Requires a **business-verified** Stripe account. In **Settings → Payments → Custom Payment Methods**, create one CPM per HitPay method (PayNow, GrabPay, ShopeePay, FPX, Touch 'n Go) and copy each **CPM Type ID** (`cpmt_…`) into env. In the Payment Element use `customPaymentMethods: [{ id: cpmt_…, options: { type: 'embedded', embedded: { handleRender, handleDestroy } } }]` to render the HitPay QR inside the element |
| Recording | After HitPay confirms payment by webhook, record it in Stripe with the **Payment Records API** so Stripe reporting shows HitPay payments too |
| Flows | One-time: QR or redirect. Subscriptions **auto-charge**: cards, ShopeePay, GrabPay (tokenised). Subscriptions **out-of-band**: PayNow and other QR methods, one payment per invoice, so recovery means a fresh QR plus a reminder, not a retry |
| Fallback if not verified | Skip CPM; show plain Stripe card decline → HitPay PayNow link (F11) |

## 6. Retriever MCP server (6 tools)

| Tool | Type | Purpose |
|---|---|---|
| `get_recovery_summary` | read | Recovered revenue, at risk, recovery and churn rates |
| `list_open_rescues` | read | Rescues awaiting payment |
| `list_unmatched_payments` | read | The review queue |
| `get_cash_forecast` | read | 14-day forecast and gap |
| `ingest_hitpay_snapshot` | write (data only) | Assistant pushes balances/payouts read through HitPay MCP into Retriever |
| `propose_discount_offer` | propose | Creates an approval item; never sends without a human |

Names should match what's already in the scaffold; rename here, not there, if they differ.

## 7. Security

- Secrets via env only (`HITPAY_API_KEY`, `HITPAY_WEBHOOK_SALT` (one per webhook endpoint), `HITPAY_ENV`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CPM_PAYNOW` and other `cpmt_…` IDs, `LLM_API_KEY`, `DATABASE_URL`). `.env.example` committed, `.env` never.
- Webhooks: verify `Hitpay-Signature` / `Stripe-Signature` on the raw body before parsing; reject on failure; constant-time compare.
- Refunds: the refund call lives behind `approvals.kind = 'refund'`; the endpoint refuses to run without an approved row and writes the approver into `events`.
- `DRY_RUN=true` default locally: no outbound HitPay/Stripe writes, logged instead.
- LLM prompts receive only the fields needed (amount, date, payer display name, candidate invoice refs). No card data ever enters the system.
- Dashboard behind a single shared password for the demo; Supabase Auth + RLS per merchant later.

## 8. Scalability path

| Pressure | Now | Next |
|---|---|---|
| Webhook spikes | Inbox table + 200 fast | Partition inbox by month; move queue to Redis/Cloud Tasks |
| Matching cost | Rules first, LLM for leftovers only | Cache payer→customer mappings; batch LLM calls |
| Multi-merchant | Single merchant | `merchant_id` on every table (already in schema), RLS, HitPay platform OAuth for sub-merchants |
| Reporting | Live SQL | Materialised views for metrics |
| Region | SG + MY config | Per-merchant currency, rails, tax rules (InvoiceNow, MyInvois) |

## 9. Sources

- HitPay MCP server: https://docs.hitpayapp.com/apis/guide/mcp-server
- HitPay Build with AI: https://docs.hitpayapp.com/apis/guide/build-with-ai
- HitPay Stripe connection: https://docs.hitpayapp.com/connections/stripe/overview
- HitPay docs index: https://docs.hitpayapp.com/llms.txt · full text: https://docs.hitpayapp.com/llms-full.txt · OpenAPI: https://docs.hitpayapp.com/openapi.json
- HitPay Stripe one-time payments: https://docs.hitpayapp.com/connections/stripe/one-time-payments.md · auto-charge: https://docs.hitpayapp.com/connections/stripe/auto-charge.md · out-of-band: https://docs.hitpayapp.com/connections/stripe/out-of-band.md
- HitPay embedded QR: https://docs.hitpayapp.com/apis/guide/embedded-qr-code-payments.md · CLI: https://docs.hitpayapp.com/apis/guide/cli.md · sandbox: https://docs.hitpayapp.com/apis/guide/sandbox.md
- Stripe Custom Payment Methods: https://docs.stripe.com/payments/custom-payment-methods · Payment Records API: https://docs.stripe.com/payments/payment-records
- HitPay Claude Code plugin: https://github.com/hit-pay/claude-code-plugin
- Stripe Smart Retries: https://docs.stripe.com/billing/revenue-recovery/smart-retries
- Stripe automatic collection: https://docs.stripe.com/billing/automatic-collection
- Churnkey: https://churnkey.co/pricing · Baremetrics Recover: https://baremetrics.com/features/recover
- Taulia dynamic discounting: https://taulia.com/platform/payables/dynamic-discounting/
- Evidence figures (Xero SG 2025, Atradius SG 2025, Experian MY 2025, SPF 2025 scam statistics) come from the earlier research report *HitPay SME problem shortlist*.
