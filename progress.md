# Retriever: progress

Update at the end of every task. Newest entries at the top of the log.

**Last updated:** Mon 23 Nov 2026, 18:50
**Current phase:** Phase 1–3 dry-run scaffold (no live HitPay/Stripe)
**Next milestone:** feature freeze Tue 24 Nov 21:00 · submit Wed 25 Nov 18:00 (hard deadline 23:59)

## Status by phase

| Phase | Status | Notes |
|---|---|---|
| Scaffold (pre-merge) | ⚠️ docs only | The “19 tests” scaffold was not in this folder. Rebuilt from the specs. 11 tests pass. |
| 0 Verify unknowns | ⏳ in progress | |
| 1 Collect + Reconcile | ⬜ not started | New from Tally |
| 2 Rescue live | 🟡 partial | Logic built, not run against real HitPay/Stripe |
| 3 EarlyBird + MCP + dashboard | 🟡 partial | Forecast/discount + MCP server built |
| 4 Demo | ⬜ not started | |

## Features

| ID | Feature | Status |
|---|---|---|
| F1 | Invoice + HitPay payment request with reference | ⬜ |
| F2 | Webhook ingest (verify, inbox, queue) | 🟡 receivers exist; signature scheme unverified; inbox/queue not built |
| F3 | Deterministic matcher | ⬜ |
| F4 | Unclear-payment queue + approvals | ⬜ |
| F5 | Recovery agent | 🟡 built, dry-run only |
| F6 | Involuntary churn tracking + sweep | ✅ built (`POST /api/churn/sweep`) |
| F7 | Live HitPay MCP calls | ⬜ |
| F8 | Append-only events | ⬜ |
| F9 | Dashboard | 🟡 metric cards, rescue timeline, forecast chart, discount panel built; queue + audit pages missing |
| F10 | Demo video | ⬜ |
| F11 | Stripe card → HitPay PayNow fallback | ⬜ |
| F12 | Protect: payee guard + recurring rescue | ⏸ moved to Phase 5 |
| F13 | EarlyBird forecast + discount | 🟡 logic built; not fed real balances |
| F14 | Retriever MCP server (6 tools) | 🟡 built; tool names to reconcile with `architecture.md` §6 |
| F15 | Stripe Custom Payment Method | ⬜ timebox Tue |
| F16–F17 | WhatsApp, tone toggle | ⬜ post-deadline |
| F18 | Method-aware fallback (PayNow, DuitNow, FPX, TnG, Boost, GrabPay, ShopeePay) | ⬜ |
| F20 | Refund with approval | ⬜ |

## Blockers and unverified items

- [x] HitPay webhook signature: `Hitpay-Signature`, HMAC over raw body with the endpoint's salt (Q1). Confirm algorithm with `hitpay trigger`
- [ ] HitPay failure/expiry status values; failure webhook for online payments? (Q2)
- [ ] Payment request fields for reference and expiry (Q3)
- [ ] Stripe CPM (Q4): needs business-verified Stripe account and `cpmt_…` IDs; check verification status first
- [ ] Sandbox method coverage: DuitNow, FPX, Boost (Q6)
- [ ] Refund endpoint fields, partial refunds, refund webhook (Q7)
- [ ] Recurring billing failure event (Q8), Phase 5
- [ ] Rescue messages shown in dashboard only, not emailed (decide: Resend or keep "sent" panel)
- [ ] Scaffold repo has nothing committed yet: make the first commit before merging Tally modules

## Log

- **Mon 23 Nov 18:50**: Dry-run scaffold for F1–F6, F8, F9, F11, F13, F14, F18, F20. Grok with rules fallback. Challenges in `CHALLENGES.md`. Live sandbox, MCP OAuth, F15, and the video are still open. GitHub token for `timothylee58` was invalid at publish time.

- **Mon 23 Nov 18:30**: Cut scope: Guard and recurring rescue merged into F12 Protect, moved to Phase 5. Added opening SME story to PRD §1.

- **Mon 23 Nov 18:15**: Added HitPay full API suite (payment requests, recurring billing, refunds, webhooks, business management) and SG/MY method coverage. New F18–F20, `subscriptions` and `refunds` tables, refund and recurring flows, Stripe CPM details. Q1 resolved.

- **Mon 23 Nov 18:00**: Merged Tally scope into Retriever. Wrote PRD, architecture, AGENTS, schema, flow, design, implementation plan. Next: Phase 0.1–0.2.
- **Mon 23 Nov (evening, earlier)**: Retriever scaffold: backend, dashboard, Docker, CI, README; 19 tests; dry-run smoke test.
