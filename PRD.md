# Retriever: product requirements

**Status:** Draft v1, Mon 23 Nov 2026
**Event:** HitPay Build Night (Singapore, with Stripe and SpaceXSI). Demo video (max 3:00) due **Wed 25 Nov 23:59 SGT** to ria@hit-pay.com, subject `Build Night Demo: Retriever by Timothy Lee`. Finalists are told by 27 Nov and present on 2 Dec.
**Judging:** technical depth, problem-solution fit, creativity. Must use HitPay's MCP server and AI tooling; Stripe through HitPay's Custom Payment Method connection earns bonus points.
**Merges:** *Retriever* (formerly "Cashflow Guardian": payment rescue, involuntary churn, EarlyBird forecast) and *Tally* (PayNow reconciliation, unclear-payment queue, bank-detail guard).

---

## 1. Problem

SMEs in Singapore and Malaysia get paid over QR rails (PayNow, DuitNow) and cards, and then lose money in three quiet places:

1. **Payments that never complete.** A card is declined or a PayNow/DuitNow QR expires, and nobody follows up. Stripe retries cards on the same method; nothing switches the customer to a QR rail, and HitPay has no documented dunning.
2. **Payments that arrive but can't be matched.** QR transfers often land with no reference or a wrong amount. The owner reconciles by hand from bank narrations. MAS lists request-to-pay and structured reconciliation data for PayNow as future work, not live features.
3. **Payments that go to the wrong place.** Fake invoices and changed supplier bank details (business email compromise) are among Singapore's top five scam types by losses.

On top of that, owners can't see a cash gap coming until it arrives.

**Opening story** (illustrative persona for the video, not a real customer)
> Mei Ling runs a tuition centre in Petaling Jaya with a second branch in Singapore. On the 1st of every month, 180 parents pay fees: some by card, most by PayNow or DuitNow QR. By the 5th, a dozen cards have been declined, a few QR codes have expired unpaid, and her bank app shows transfers like "S$320 TAN" that match no invoice. She spends her Sunday cross-checking WhatsApp screenshots against a spreadsheet, chasing parents who think they already paid, and still can't tell whether she can cover rent on the 15th. Retriever does that Sunday for her: it sends each failed payer a fresh PayNow or DuitNow link, matches the stray transfers, asks her only about the ones it isn't sure of, and warns her a week before cash runs short.

**Evidence** (sources in `architecture.md` §9)
- 91% of Singapore SMEs say late payment affects them, 43% significantly; 20% have no strategy for getting paid on time (Xero, 2025).
- 35% of B2B credit sales in Singapore are overdue on average; bad debt is about 6% of invoices (Atradius, 2025).
- Malaysian SMEs wait 64 days on average for payment (Experian, 2025).
- 52% of Singapore SMEs lack real-time financial information (Xero, 2025).

## 2. Positioning

> **Retriever gets SMEs paid.** It rescues payments that failed, matches payments that arrived without a reference, and warns about cash gaps early, all on HitPay. Next: it holds payments to suppliers whose bank details changed.

What we do *not* claim: that reminders, card retries or early-payment discounts are new. Xero and HitPay send reminders; Stripe Smart Retries handles card retries; 2/10 net 30 is decades old.

What is new:
- **Cross-method rescue:** a failed card or expired QR becomes a fresh PayNow/DuitNow link automatically.
- **Closing the loop on QR payments:** every request carries its invoice reference, and anything unmatched goes to a review queue instead of a spreadsheet.
- **A payment guard for SMEs (Phase 5):** bank-detail changes are held until verified out of band.
- **Forecast-triggered discounts:** an early-payment discount is offered only when it costs less than the cash gap it prevents.
- **Local rails and SME pricing**, not retry ML or enterprise dynamic discounting.

### Built on HitPay's full API suite

| HitPay capability | How Retriever uses it |
|---|---|
| **Payment requests** | Every invoice, rescue and discount is a payment request carrying the invoice reference |
| **Recurring billing** | Later: failed recurring charges rescued like one-off failures (F12) |
| **Refunds** | Available, but only after an owner approval; never by the agent alone (F20) |
| **Webhooks** | Single source of truth for payment state (`Hitpay-Signature`, per-endpoint salt) |
| **Business management** (balances, payouts, charges, orders, invoices, products via hosted MCP and REST) | Operator reads, EarlyBird forecast inputs, reconciliation of payouts |

### Local and global methods, out of the box

| Market | Methods Retriever can offer as primary or fallback |
|---|---|
| Singapore | PayNow QR, cards, GrabPay, ShopeePay, Atome |
| Malaysia | DuitNow QR, FPX, Touch 'n Go eWallet, Boost, GrabPay, ShopeePay, cards |
| Global | Cards (Visa, Mastercard, Amex) through HitPay, or Stripe with HitPay methods inside the Payment Element (Custom Payment Methods) |

Rescue picks the fallback by merchant country and the payer's history: a declined card in SG becomes PayNow; in MY it becomes DuitNow or the e-wallet the payer used before. Method availability per account is confirmed in the HitPay dashboard (**Settings → Payment Methods**); the sandbox supports only some of them (see Q6).

## 3. Users

| Persona | Context | Job to be done |
|---|---|---|
| **Owner-operator** (primary) | Tuition centre, clinic, F&B supplier, trading company, agency; 1–30 staff; SG or MY | "Tell me who owes me, fix what's broken, and only bother me when money needs a yes." |
| **Part-time bookkeeper** | Reconciles monthly in Xero or Excel | "Give me matched payments and an audit trail I can hand to the accountant." |
| **Payer** (secondary) | B2B buyer or retail customer | "Let me pay in one tap with the method I already use." |

## 4. Goals and non-goals

**Goals for the demo (25 Nov)**
- G1: Show one failed payment rescued end to end through a HitPay PayNow link (Stripe card failure → HitPay).
- G2: Show one payment with no reference matched by the agent and approved in one tap.
- G3: Show live HitPay MCP reads and link creation.
- G4: Show the audit trail for every action.
- G5 (stretch): Show the EarlyBird discount.

**Non-goals**
- Agent-initiated money movement. Refunds go through HitPay's REST API only after an owner approval; payouts and transfers are out of scope.
- Voluntary subscription churn (cancellations, downgrades). Failed recurring *charges* come later (F12).
- Multi-tenant auth, accounting integrations, ML retry timing.
- InvoiceNow / MyInvois e-invoicing (roadmap only).

## 5. Scope (MoSCoW)

Feature IDs are referenced in `implementation-plan.md` and `progress.md`.

### Must have
| ID | Module | Feature | Acceptance criteria |
|---|---|---|---|
| F1 | Collect | Create an invoice and a HitPay payment request with `reference_number = invoice.ref` | Request created in sandbox; QR/link shown; `payment_requests` row stored; `events` row written |
| F2 | Ingest | Webhook receiver for HitPay sandbox and Stripe test events | Signature verified; duplicate events ignored (unique `provider_event_id`); raw body stored in `webhook_inbox`; 200 returned in < 500 ms |
| F3 | Reconcile | Deterministic matcher | Exact reference → invoice marked `paid` (or `partially_paid`); no manual step |
| F4 | Reconcile | Unclear-payment queue | Unreferenced or mismatched payment → LLM proposes `{invoice_id, confidence, reason}`; below 0.9 goes to the queue; owner approves or rejects; decision logged |
| F5 | Rescue | Recovery agent | Failed/expired/abandoned attempt classified; fallback HitPay PayNow link created; message drafted and shown as "sent" (email optional) |
| F6 | Rescue | Involuntary churn tracking | `POST /api/churn/sweep` marks rescues unpaid after `CHURN_AFTER_DAYS` (default 7); rates shown on dashboard; later payment counts as win-back |
| F7 | MCP | Live HitPay MCP calls | `get_balances`, `list_payouts`, `list_charges`, `create_payment_link` shown working on a live account (S$1 tests) |
| F8 | Audit | Append-only `events` log | Every state change and agent decision has an event with actor, reason and payload; UI shows it in plain English |
| F9 | UI | Owner dashboard | Cards: recovered revenue, still at risk, recovery rate, involuntary churn rate, unmatched payments; rescue timeline; queue |
| F10 | Demo | 3-minute video | Submitted with the required subject line by Wed 18:00 SGT |

### Should have
| ID | Module | Feature |
|---|---|---|
| F11 | Rescue | Stripe card failure (`payment_intent.payment_failed`, test card) → HitPay PayNow fallback, end to end (bonus points) |
| F13 | Forecast | EarlyBird: 14-day cash forecast from payouts + open invoices; on a gap, offer a discount link for the largest overdue invoice only if `discount_cost < gap_cost` |
| F14 | Retriever MCP | Retriever's own MCP server (6 tools) so an assistant can query and act on Retriever |
| F18 | Rails | Method-aware fallback: PayNow (SG), DuitNow / FPX / Touch 'n Go / Boost / GrabPay (MY), chosen by country and payer history; SGD and MYR |
| F20 | Refund | Refund request → owner approval → HitPay REST refund → webhook confirms → `events`; partial refunds supported |

### Could have
| ID | Feature |
|---|---|
| F15 | Stripe Custom Payment Methods: HitPay PayNow/GrabPay/ShopeePay/FPX/Touch 'n Go inside Stripe's Payment Element (`type: 'embedded'` QR), recorded back to Stripe with the Payment Records API. Needs a business-verified Stripe account and a `cpmt_…` ID per method |
| F16 | Telegram or WhatsApp delivery of rescue messages and owner approvals |
| F17 | Reminder drafts with friendly/firm tone toggle and per-customer "pause chasing" |

### Later (Phase 5, after the demo)
| ID | Feature |
|---|---|
| F12 | **Protect**: (a) supplier bank-detail change held until verified by phone, release needs owner approval; (b) failed recurring charge opens a one-cycle rescue, plan stays active. Shares the rescue and approval code, so both ship together |

### Won't have (this round)
Payouts and transfers, multi-tenant auth, accounting sync, ML retry timing, voluntary subscription churn, InvoiceNow/MyInvois submission.

## 6. Key metrics

Shown on the dashboard and used in the video's impact line. All are computed from the demo run, never invented.

| Metric | Definition |
|---|---|
| Recovered revenue | Sum of `amount_minor` of rescues with status `recovered` or `won_back` |
| Still at risk | Sum of open rescues + unmatched payments + overdue invoices |
| Recovery rate | recovered failures / all failures |
| Involuntary churn rate | churned failures / all failures |
| Auto-match rate | payments matched without human input / all payments |
| Time to match | median seconds from webhook to `matched` |

## 7. Compliance and risk requirements

| Requirement | Why | How |
|---|---|---|
| No agent-initiated money movement | Trust; HitPay's MCP server and plugin exclude refunds and money movement by design | Agent may only *create* payment links/requests. Refunds (REST API) and payee releases need a human approval event; payouts are out of scope |
| Human approval for money-adjacent actions | Wrong chasing of a VIP client or wrong match is costly | Matches below threshold, discounts, payee changes go to the queue |
| Audit trail kept 5 years | SG Companies Act s.199 and IRAS record-keeping; MY commonly 7 years (unverified) | Append-only `events`; no updates or deletes |
| Personal data minimised | SG PDPA (fines up to 10% of SG turnover or S$1m); MY PDPA amendments 2025 | Store payer name/email/phone only; never store card data (Stripe/HitPay hold it); redact PII in LLM prompts where possible |
| Webhooks authenticated | Forged "paid" events | HMAC/signature verification; reject unsigned |
| Bank-detail changes verified out of band | BEC is a top-5 SG scam type | F12 Protect (Phase 5); callback recorded in `events` |
| Currency and rounding correctness | Money bugs | Integer minor units; currency stored per row |

## 8. Assumptions and open questions

| # | Question | Default if unresolved | Owner / when |
|---|---|---|---|
| Q1 | ~~HitPay webhook signature scheme~~ **Resolved:** `Hitpay-Signature` header, HMAC over the raw request body, with the salt of that webhook endpoint (**Developers → Webhook Endpoints**). Still confirm the hash algorithm and payload shape with `hitpay trigger` | — | Mon night |
| Q2 | HitPay failure status values (failed / expired / pending) and whether a failure webhook exists for online payments | Fallback: treat a link unpaid after N minutes (polled via `list_charges` / `get_payment_link`) as abandoned/expired | Mon night |
| Q3 | Payment request fields for reference and expiry | Use `reference_number`, `expiry_date` if present | Mon night |
| Q4 | Stripe Custom Payment Method available in test mode | Skip F15; do F11 with plain Stripe test card failures | Tue, 1-hour timebox |
| Q5 | MY merchant sandbox support for DuitNow/FPX | Demo in SGD; MY shown as config + roadmap | Post-demo |
| Q6 | Which methods work in the HitPay sandbox (earlier research: cards, PayNow, ShopeePay, GrabPay, GrabPay PayLater, Atome, DOKU QRIS; recurring only ShopeePay, GrabPay, Touch 'n Go) | Demo PayNow + card; show DuitNow/Boost/TnG as fallback options in config | Mon night |
| Q7 | Refund endpoint fields and whether partial refunds and refund webhooks work in sandbox | Demo one full refund with approval | Tue |
| Q8 | Recurring billing failure event name and retry behaviour | Poll recurring billing status if no event | Tue |

## 9. Release plan

See `implementation-plan.md`. Features freeze **Tue 24 Nov 21:00**. Wednesday is recording, editing and submission (target 18:00, buffer to 23:59).
