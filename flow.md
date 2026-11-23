# Retriever: flows

Sequences for each module. Tables and statuses are defined in `schema.md`.

## 1. Collect (F1)

```
Owner            Dashboard        Retriever API          HitPay (sandbox)
  │ new invoice ─►│ POST /api/invoices ─►│
  │               │                  │ insert invoice (draft→issued)
  │               │                  │ POST /v1/payment-requests
  │               │                  │   reference_number=INV-104 ───►│
  │               │                  │◄────────── id, url, qr ─────────│
  │               │                  │ insert payment_requests; events
  │               │◄── link + QR ────│
  │◄── share link │
```

## 2. Webhook ingest (F2)

```
Provider ─POST /webhooks/{provider}─► API
  1. read raw body
  2. verify signature ── fail → 401, inbox row signature_valid=false
       HitPay: Hitpay-Signature = HMAC(raw body, salt of this webhook endpoint)
       Stripe: Stripe-Signature via stripe.Webhook.construct_event
  3. INSERT webhook_inbox ON CONFLICT (provider, provider_event_id) DO NOTHING
       └─ conflict → 200 (duplicate)
  4. INSERT jobs(kind=process_webhook)
  5. 200 OK  (target < 500 ms)

Worker ─claim job (SKIP LOCKED)─► normaliser
  ├─ success event  → upsert payment_attempts(succeeded) + payments → enqueue match_payment
  ├─ failure event  → payment_attempts(failed, failure_code) → enqueue rescue_attempt
  └─ unknown type   → mark processed, log event `webhook.ignored`
```

**No failure webhook from HitPay?** (PRD Q2) A scheduled job polls open `payment_requests` older than `N` minutes via `list_charges` / get request. Unpaid → `payment_attempts(abandoned)` → rescue.

## 3. Reconcile (F3, F4)

```
match_payment(payment)
  ├─ Tier 1: payer_reference == invoice.ref and currency matches
  │     → allocate min(payment, outstanding); invoice → paid | partially_paid
  │     → overpayment: allocate full, remainder stays unallocated + approval note
  ├─ Tier 2 (rules): exactly one open invoice with same amount and
  │     (payer_name ∈ customer.aliases) and due within ±30 days
  │     → confidence 0.95 → auto-allocate
  ├─ Tier 3 (LLM): candidates = top 5 open invoices by amount/name/date similarity
  │     → LLM returns {invoice_id | null, confidence, reason}
  │     → validated → match_suggestions + approvals(kind=match) → payment.suggested
  └─ nothing plausible → payment.unmatched (shown in queue for manual pick)

Owner approves suggestion
  → allocation(approved_by) → invoice status update
  → customer.aliases += payer_name   (learns for next time)
  → events: approval.approved, payment.matched
```

Edge cases covered by tests: partial payment, overpayment, one payment for two invoices (owner splits in queue), two payments for one invoice, wrong currency (never auto-match), duplicate webhook.

## 4. Rescue (F5, F6, F11)

```
rescue_attempt(attempt)
  1. classify failure_class
       Stripe decline_code (insufficient_funds, do_not_honor, expired_card, …) → declined
       HitPay expired / QR timeout                                         → expired
       polling timeout                                                     → abandoned
  2. customer.pause_chasing? → rescue(opened), no message, stop
  3. choose fallback method (app/domain/fallback.py)
       never the failed method
       → customer.last_success_method if enabled
       → country default: paynow (SG) | duitnow (MY)
       → MY B2B ≥ RM 5,000: fpx;  MY retail: tng | boost | grabpay as alternatives
     create fallback HitPay payment request
       payment_methods = [chosen, …alternatives], purpose=rescue, reference = invoice.ref
  4. LLM drafts message (tone from settings; facts injected, not generated)
       e.g. "Your card payment for INV-104 (S$420) didn't go through. Pay by PayNow here: <link>"
  5. rescue → offered; message_channel=dashboard (email if enabled); events

Payment arrives for fallback request → normal reconcile → rescue → recovered

Daily churn sweep (POST /api/churn/sweep)
  offered AND now - created_at > churn_after_days → churned
  churned AND later payment matched                → won_back
```

### 4b. Recurring billing rescue (F12 Protect, Phase 5)

```
HitPay recurring charge fails (webhook ⚠ or status poll, PRD Q8)
  → payment_attempts(failed, subscription_id) ; subscription → past_due
  → rescue_attempt as above, but the fallback link pays this cycle only
       auto_charge plan (card / GrabPay / ShopeePay / TnG): offer QR fallback for this cycle,
         plus "update your payment method" link
       out_of_band plan (PayNow / DuitNow): new QR for this cycle + reminder
  → paid → rescue recovered ; subscription → active ; next_charge_at unchanged
  → churned → owner decides: keep past_due or cancel (never auto-cancel)
```

### 4c. Stripe checkout with HitPay methods (F15, bonus)

```
Payer opens checkout ─► Stripe Payment Element
   cards → Stripe native
   PayNow / GrabPay / ShopeePay / FPX / TnG → Custom Payment Method (cpmt_…)
      type 'embedded' → handleRender(container) → Retriever creates HitPay payment
      request (reference = invoice.ref) → render HitPay QR inside the element
HitPay webhook (completed) ─► Retriever ─► reconcile as usual
                                       └─► Stripe Payment Records API: record external payment
Stripe card declines ─► payment_intent.payment_failed ─► rescue (§4) ─► HitPay QR fallback
```

## 5. Payee guard (F12 Protect, Phase 5)

```
Supplier "updates bank details" (seeded email / manual entry)
  → payee_changes(held) ; payables to that payee blocked
  → approvals(kind=payee_release) with task: "Call <supplier> on the number already on file"
Owner records callback note + approves → payee_changes(verified); payee.account updated; events
Owner rejects                          → rejected; events `guard.blocked_suspected_bec`
```

## 6. EarlyBird forecast and discount (F13)

```
forecast job (daily or on demand)
  start = current balance (HitPay MCP get_balances via ingest_hitpay_snapshot, or seeded)
  + scheduled payouts (list_payouts)
  + expected receipts: open invoices × payer's historical on-time ratio, on predicted date
  - known outgoings (seeded fixed costs)
  → series over 14 days; gap = max(0, buffer - min_balance)

if gap > 0:
  pick largest overdue invoice from a payer with good history
  discount_cost = invoice.amount × pct
  gap_cost      = gap × daily financing rate × days in gap  (configurable, e.g. card/overdraft APR)
  if discount_cost < gap_cost and pct ≤ discount_max_pct
     → discount_offers(proposed) + approvals(kind=discount)
Owner approves → HitPay payment request for (amount - discount), purpose=discount → sent
```

## 7. Operator assistant (F7, F14)

```
Owner in Claude: "How's cash this fortnight? Anything to chase?"
  Claude ─HitPay MCP─► get_balances, list_payouts, list_charges
  Claude ─Retriever MCP─► ingest_hitpay_snapshot(balances, payouts)
  Claude ─Retriever MCP─► get_cash_forecast → gap on day 9
  Claude ─Retriever MCP─► propose_discount_offer(INV-118, 1.5%) → approval created
  Claude ─HitPay MCP─► create_payment_link (only after owner says yes, S$1 test in demo)
```

## 7b. Refund with approval (F20)

```
Owner (or assistant via Retriever MCP) requests refund on payment P, amount A, reason R
  → check A ≤ P.amount − P.amount_refunded
  → refunds(requested) + approvals(kind=refund, summary="Refund S$A to <payer> for INV-104: <R>")
Owner approves (Dialog with note)
  → refunds(approved) → HitPay REST refund (idempotency key = refund.id) → submitted
  → webhook / status poll → succeeded → payments.amount_refunded_minor += A
  → invoice status re-evaluated (paid → partially_paid if needed); events at every step
Provider error → failed → approval card shows error + retry button (new approval required)
```

Neither the HitPay MCP server nor the Claude Code plugin can refund, by design. The only refund path is this approved REST call.

## 8. Demo sequence (3:00)

| Time | Beat | Flow |
|---|---|---|
| 0:00–0:20 | Mei Ling's Sunday (PRD §1 story): declined cards, expired QR, stray transfers | — |
| 0:20–1:05 | Stripe test card declines → Retriever classifies → PayNow link via HitPay → paid → recovered counter ticks | §4 |
| 1:05–1:45 | S$800 transfer with no reference → AI suggests INV-104 (0.82, amount + name) → one-tap approve | §3 |
| 1:45–2:30 | Claude reads balances/payouts via HitPay MCP → forecast gap → discount proposal | §6, §7 |
| 2:30–2:40 | Architecture slide: webhooks, ledger, HitPay MCP + Retriever MCP | — |
| 2:40–3:00 | Audit trail (incl. one approved refund) + method coverage slide (PayNow, DuitNow, FPX, TnG, Boost, GrabPay, ShopeePay, cards) + real numbers from this run + roadmap | §7b |
