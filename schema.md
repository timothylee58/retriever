# Retriever: data model

Postgres 15+. Every table has `id uuid pk default gen_random_uuid()`, `merchant_id uuid not null`, `created_at timestamptz default now()`. Money is `amount_minor bigint` + `currency char(3)`.

## 1. Entity overview

```
merchants 1─* customers 1─* invoices 1─* payment_requests 1─* payment_attempts
                                │                                  │
                                │                                  └─* rescues
                                └─* allocations *─1 payments ─* match_suggestions
merchants 1─* payees 1─* payee_changes
merchants 1─* approvals        (match | discount | payee_release | refund)
customers 1─* subscriptions 1─* payment_attempts   (recurring billing)
payments  1─* refunds
merchants 1─* forecasts 1─* discount_offers
webhook_inbox ─► jobs ─► (domain updates) ─► events (append-only, everything)
```

## 2. Tables

### merchants
| Column | Type | Notes |
|---|---|---|
| name | text | |
| country | char(2) | `SG` or `MY` |
| default_currency | char(3) | `SGD` or `MYR` |
| timezone | text | `Asia/Singapore` / `Asia/Kuala_Lumpur` |
| hitpay_mode | text | `sandbox` \| `live` |
| settings | jsonb | `churn_after_days` (7), `auto_match_threshold` (0.9), `discount_max_pct` (2.0), `enabled_methods` (from HitPay dashboard), `fallback_order` e.g. `["paynow"]` SG / `["duitnow","tng","boost","fpx"]` MY |

### payment_method (enum, shared)
`paynow`, `duitnow`, `fpx`, `tng`, `boost`, `grabpay`, `shopeepay`, `card`, `atome`. Map provider strings to this enum only in `app/providers/`.

### customers
| Column | Type | Notes |
|---|---|---|
| display_name | text | |
| email, phone | text null | PII, minimal |
| aliases | text[] | Names seen on transfers, learned from approved matches |
| pause_chasing | bool | default false |
| last_success_method | payment_method null | Drives rescue fallback choice |

### invoices
| Column | Type | Notes |
|---|---|---|
| customer_id | uuid fk | |
| ref | text unique per merchant | e.g. `INV-104`; used as HitPay `reference_number` |
| amount_minor, currency | | |
| amount_paid_minor | bigint default 0 | Sum of allocations |
| issued_at, due_at | timestamptz | |
| status | `invoice_status` | see §3 |

### payment_requests
| Column | Type | Notes |
|---|---|---|
| invoice_id | uuid fk null | null for ad-hoc links |
| provider | `hitpay` \| `stripe` | |
| provider_request_id | text unique | |
| methods | payment_method[] | Sent as HitPay `payment_methods[]` ⚠ |
| subscription_id | uuid fk null | Set for recurring rescue links |
| url, qr_payload | text | |
| purpose | `primary` \| `rescue` \| `discount` | |
| expires_at | timestamptz null | |
| status | `request_status` | `open`, `paid`, `expired`, `cancelled` |

### payment_attempts
One try to pay (card authorisation, QR session).
| Column | Type | Notes |
|---|---|---|
| payment_request_id | uuid fk null | null for recurring auto-charges |
| subscription_id | uuid fk null | set for recurring charges |
| provider_attempt_id | text unique | Stripe PaymentIntent / HitPay charge id |
| method | payment_method | |
| amount_minor, currency | | |
| status | `attempt_status` | `pending`, `succeeded`, `failed`, `expired`, `abandoned` |
| failure_code | text null | Stripe `decline_code` or HitPay status |
| failure_class | `declined` \| `expired` \| `abandoned` \| null | Set by rescue agent |

### payments
Money that actually arrived, matched or not.
| Column | Type | Notes |
|---|---|---|
| provider | | |
| provider_payment_id | text unique | |
| amount_minor, currency | | |
| method | payment_method | |
| amount_refunded_minor | bigint default 0 | Sum of succeeded refunds |
| payer_name, payer_reference | text null | As received |
| received_at | timestamptz | |
| match_status | `match_status` | `unmatched`, `suggested`, `matched`, `rejected`, `ignored` |
| match_tier | smallint null | 1 exact ref, 2 rules, 3 LLM, 0 manual |

### allocations
| Column | Type | Notes |
|---|---|---|
| payment_id, invoice_id | uuid fk | One payment may cover many invoices and vice versa |
| amount_minor | bigint | Sum per payment ≤ payment amount |
| approved_by | text null | null only for tier-1/2 auto matches |

### match_suggestions
| Column | Type | Notes |
|---|---|---|
| payment_id | uuid fk | |
| invoice_id | uuid fk | |
| confidence | numeric(3,2) | 0–1 |
| reason | text | Plain English, shown to owner |
| model | text | LLM model id or `rules-v1` |

### rescues
| Column | Type | Notes |
|---|---|---|
| failed_attempt_id | uuid fk unique | One rescue per failure |
| fallback_request_id | uuid fk null | The PayNow/DuitNow link created |
| amount_minor, currency | | |
| message_draft | text | |
| message_channel | `dashboard` \| `email` \| `whatsapp` \| `telegram` | |
| status | `rescue_status` | see §3 |
| churned_at, recovered_at | timestamptz null | |

### payees and payee_changes (Protect, Phase 5)
| payees column | Type | | payee_changes column | Type |
|---|---|---|---|---|
| name | text | | payee_id | uuid fk |
| bank_name | text | | old_account_masked, new_account_masked | text (last 4 only) |
| account_masked | text | | source | `email`, `portal`, `manual` |
| verified_at | timestamptz null | | status | `held`, `verified`, `rejected` |
| | | | callback_note | text null |

### subscriptions (recurring billing, Phase 5)
| Column | Type | Notes |
|---|---|---|
| customer_id | uuid fk | |
| provider_recurring_id | text unique | HitPay recurring billing id ⚠ |
| plan_name | text | |
| amount_minor, currency | | |
| cycle | `weekly` \| `monthly` \| `yearly` | |
| mode | `auto_charge` \| `out_of_band` | QR methods are always `out_of_band` |
| method | payment_method | |
| status | `active` \| `past_due` \| `cancelled` | `past_due` while a rescue is open |
| next_charge_at | timestamptz | |

### refunds
| Column | Type | Notes |
|---|---|---|
| payment_id | uuid fk | |
| approval_id | uuid fk not null | Refund cannot exist without an approval |
| amount_minor | bigint | ≤ payment amount − already refunded |
| reason | text | |
| provider_refund_id | text unique null | |
| status | `requested` \| `approved` \| `submitted` \| `succeeded` \| `failed` | |

### approvals
| Column | Type | Notes |
|---|---|---|
| kind | `match` \| `discount` \| `payee_release` \| `refund` | |
| subject_id | uuid | payment, discount_offer, payee_change or refund |
| summary | text | One-line plain English |
| status | `pending` \| `approved` \| `rejected` \| `expired` | |
| decided_by, decided_at, decision_note | | |

### forecasts and discount_offers (EarlyBird)
| forecasts | Type | | discount_offers | Type |
|---|---|---|---|---|
| horizon_days | int (14) | | forecast_id, invoice_id | uuid fk |
| series | jsonb `[{date, balance_minor}]` | | discount_pct | numeric(4,2) |
| min_balance_minor | bigint | | discount_cost_minor | bigint |
| gap_minor | bigint | | gap_cost_minor | bigint (e.g. overdraft/financing cost avoided) |
| inputs | jsonb | | payment_request_id | uuid fk null |
| | | | status | `proposed`, `approved`, `sent`, `paid`, `rejected` |

Rule: offer only if `discount_cost_minor < gap_cost_minor` and `discount_pct ≤ settings.discount_max_pct`.

### webhook_inbox
| Column | Type | Notes |
|---|---|---|
| provider | text | |
| provider_event_id | text | unique with provider |
| signature_valid | bool | |
| raw_body | bytea | |
| received_at, processed_at | timestamptz | |
| error | text null | |

### jobs
| Column | Type | Notes |
|---|---|---|
| kind | text | `process_webhook`, `match_payment`, `rescue_attempt`, `churn_sweep`, `forecast` |
| payload | jsonb | |
| status | `queued`, `running`, `done`, `failed` | |
| attempts, run_after, locked_at | | Worker uses `FOR UPDATE SKIP LOCKED` |

### events (append-only audit)
| Column | Type | Notes |
|---|---|---|
| occurred_at | timestamptz | |
| actor | text | `system`, `agent:rescue`, `agent:matcher`, `user:<name>`, `provider:hitpay` |
| type | text | e.g. `invoice.issued`, `payment.matched`, `rescue.link_created`, `approval.approved` |
| subject_type, subject_id | text, uuid | |
| reason | text | Plain English for the audit view |
| payload | jsonb | Before/after snapshot |

Trigger: `BEFORE UPDATE OR DELETE ON events` raises an exception.

## 3. State machines

### invoice_status
```
draft ─issue─► issued ─due passes─► overdue
issued|overdue ─allocation < total─► partially_paid
issued|overdue|partially_paid ─allocations = total─► paid
any unpaid ─owner─► written_off
```

### attempt_status → rescue_status
```
attempt: pending ─► succeeded
         pending ─► failed | expired | abandoned ──► creates rescue

rescue:  opened ─link created─► offered ─paid─► recovered
         offered ─after churn_after_days─► churned ─paid later─► won_back
         opened|offered ─owner─► dismissed
```

### match_status
```
unmatched ─tier 1/2 ≥ threshold─► matched
unmatched ─tier 3─► suggested ─approve─► matched
                    suggested ─reject─► unmatched (owner picks invoice manually) | ignored
```

### payee_change
```
held ─callback verified + approve─► verified
held ─reject─► rejected
```

### refund
```
requested ─owner approves─► approved ─REST call─► submitted ─webhook/status─► succeeded
requested ─owner rejects─► (approval rejected, refund stays requested→closed)
submitted ─provider error─► failed
```

### subscription
```
active ─recurring charge fails─► past_due (rescue opened)
past_due ─rescue recovered─► active
past_due ─rescue churned─► past_due (owner decides cancel)
any ─owner/provider─► cancelled
```

## 4. Indexes

- `payments (merchant_id, match_status)`; `invoices (merchant_id, status, due_at)`; `rescues (merchant_id, status)`
- `events (merchant_id, subject_type, subject_id, occurred_at)`
- `jobs (status, run_after)` partial where `status = 'queued'`
- Unique: `webhook_inbox (provider, provider_event_id)`, `invoices (merchant_id, ref)`, `payment_requests (provider, provider_request_id)`

## 5. Derived metrics (SQL views)

| View | Definition |
|---|---|
| `v_recovery` | failures, recovered, churned, won_back, recovery_rate, churn_rate |
| `v_reconcile` | payments, auto_matched, suggested, unmatched, auto_match_rate, median time to match |
| `v_at_risk` | open rescues + unmatched payments + overdue invoices (amount) |
| `v_methods` | payments and recoveries by `payment_method` and country (which fallback actually converts) |
