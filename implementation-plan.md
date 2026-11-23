# Retriever: implementation plan

Now: **Mon 23 Nov, ~18:00 MYT/SGT.** Deadline: **Wed 25 Nov 23:59.** Target submission **Wed 18:00**.
Feature freeze: **Tue 24 Nov 21:00.** After that, only bug fixes and demo polish.

Starting point: Retriever scaffold already has FastAPI webhooks, rescue agent, forecast/discount logic, churn tracking, Retriever MCP server (6 tools), Next.js dashboard, Docker, CI, 19 passing tests (see `progress.md`). Tally's reconcile and guard modules are new.

## Phase 0: Verify the unknowns (Mon 18:00–21:00) · blocks everything

| # | Task | Done when |
|---|---|---|
| 0.1 | Create HitPay sandbox account (SG); enable methods in **Settings → Payment Methods**; API key in `.env`; create a webhook endpoint under **Developers → Webhook Endpoints** and store its salt as `HITPAY_WEBHOOK_SALT` | `curl` creates a payment request |
| 0.1b | Install HitPay tooling: Claude Code plugin (`/plugin marketplace add hit-pay/claude-code-plugin`, `/plugin install hitpay@hitpay-plugins`, `HITPAY_ENV=sandbox`), CLI (`npm i -g @hit-pay/cli`, `hitpay login`), hosted MCP (`claude mcp add --transport http hitpay https://mcp.hit-pay.com/`) | All three respond |
| 0.2 | `hitpay listen --forward-to http://localhost:8000/webhooks/hitpay` + `hitpay trigger`: capture real payloads into `tests/fixtures/hitpay/`; confirm `Hitpay-Signature` HMAC algorithm and status values | ⚠ removed in `architecture.md` §5 |
| 0.2b | List which methods the sandbox actually offers (PRD Q6); record refund and recurring endpoint fields from `openapi.json` (Q7, Q8) | Methods matrix "Sandbox" column filled |
| 0.3 | Confirm whether online payment failure/expiry webhooks exist | If not: enable polling fallback (`flow.md` §2) |
| 0.4 | Stripe test mode: webhook secret, `stripe listen`, decline test card → `payment_intent.payment_failed` fixture | Fixture saved |
| 0.5 | Connect hosted HitPay MCP to Claude on the live account; run `get_balances`, `list_payouts` | Screenshot for the video |
| 0.6 | Move Postgres schema to `schema.md` (migration `0002_reconcile_guard.sql`) | `alembic upgrade head` clean |

**Exit:** real fixtures for both providers; schema migrated; MCP reads proven.

## Phase 1: Collect + Reconcile (Mon 21:00 – Tue 11:00)

| # | Task | Feature |
|---|---|---|
| 1.1 | `providers/hitpay.create_payment_request(invoice)` with `reference_number`; store `payment_requests` | F1 |
| 1.2 | Invoice create endpoint + dashboard form + QR display | F1 |
| 1.3 | Harden ingest: raw-body signature check, `webhook_inbox` unique key, `jobs` queue with SKIP LOCKED worker | F2 |
| 1.4 | Matcher tier 1 (exact ref) + allocations + invoice status transitions | F3 |
| 1.5 | Matcher tier 2 (rules) + customer aliases | F3 |
| 1.6 | Matcher tier 3 (LLM) with Pydantic schema → `match_suggestions` + `approvals` | F4 |
| 1.7 | Approvals API (`/api/approvals/{id}/approve|reject`) + alias learning | F4 |
| 1.8 | `events` table + trigger; write events in every transition | F8 |
| 1.9 | Tests: matcher table tests (6 edge cases), webhook duplicate/invalid signature | — |

**Exit:** create invoice → pay in sandbox → auto-matched; unreferenced payment → queue → approved; all events visible.

## Phase 2: Rescue live (Tue 11:00–16:00)

| # | Task | Feature |
|---|---|---|
| 2.1 | Wire existing rescue agent to real HitPay fixtures (expired/abandoned) and Stripe decline codes | F5 |
| 2.2 | Stripe declined card → HitPay PayNow fallback link end to end | F11 |
| 2.3 | Rescue paid → reconcile → `recovered`; churn sweep + win-back | F6 |
| 2.4 | Method-aware fallback (`app/domain/fallback.py`) with SG/MY defaults, payer history, and `payment_methods[]` on the request; table tests for SG and MY | F18 |
| 2.5 | Refund with approval: `refunds` table, approval kind `refund`, HitPay REST refund, webhook/status confirm, partial refund maths | F20 |
| 2.7 | 1-hour timebox: Stripe Custom Payment Methods. Needs a business-verified Stripe account → create CPMs (PayNow first) → `cpmt_…` IDs in env → Payment Element with `type: 'embedded'` HitPay QR → record the payment with the Payment Records API. No verified account → drop F15 and keep F11 | F15 |

**Exit:** declined card → recovered revenue ticks on the dashboard from real events.

## Phase 3: EarlyBird + MCP + dashboard (Tue 16:00–21:00) · freeze at 21:00

| # | Task | Feature |
|---|---|---|
| 3.2 | EarlyBird forecast fed by `ingest_hitpay_snapshot` from Claude + HitPay MCP | F13, F14 |
| 3.3 | Discount proposal only when `discount_cost < gap_cost` | F13 |
| 3.4 | Dashboard: queue page, rescue sheet, forecast card, audit feed, metric strip from SQL views | F9 |

**Cut order if behind:** 3.3 discount → forecast chart polish → F20 refund. Never cut F2–F4, F5, F8.

## Phase 4: Demo (Tue 21:00 – Wed 18:00)

| # | Task |
|---|---|
| 4.1 | Seed script: 1 merchant (SG), 8 customers, 12 invoices, aliases, 1 supplier; label "simulated" |
| 4.2 | Dry-run the 3:00 script twice (`flow.md` §8); fix only what breaks |
| 4.3 | Record main take (screen + voiceover) and a **fallback take** from seeded data with providers stubbed |
| 4.4 | Edit to ≤ 3:00; captions; impact line uses numbers from this run |
| 4.5 | README: architecture diagram, setup, env vars, demo GIF; push repo public |
| 4.6 | Email ria@hit-pay.com, subject `Build Night Demo: Retriever by Timothy Lee`, video link + repo |

## Phase 5: After the deadline (if selected, before 2 Dec)

- **F12 Protect:** payee bank-detail guard + recurring billing rescue (one sandbox plan on ShopeePay/GrabPay/TnG).
- Malaysia live: MY HitPay merchant, DuitNow / FPX / Touch 'n Go / Boost verified end to end, MY seed data.
- WhatsApp/Telegram approvals and rescue messages (F16).
- Tone toggle and per-customer pause (F17).
- Multi-merchant: Supabase Auth + RLS, HitPay platform OAuth.
- Compliance roadmap: InvoiceNow (SG, mandatory by turnover band 2028–2031) and MyInvois (MY) readiness checks.
- Live presentation script for 2 Dec.

## Definition of done (every task)

Code + test + events written + `progress.md` updated + `pytest` and `next build` green.
