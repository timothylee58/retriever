---
name: Retriever
description: A quiet back office for SME payments. It recovers, matches and forecasts on its own, and only speaks when it needs a yes.
source:
  - apps/web/src/styles/tokens.css
  - apps/web/src/lib/motion.tsx
  - apps/web/components.json
generatedAt: "2026-11-23"
colors:
  background: "oklch(0.985 0.003 95)"
  foreground: "oklch(0.21 0.015 260)"
  card: "oklch(1 0 0)"
  muted-foreground: "oklch(0.50 0.015 260)"
  primary: "oklch(0.51 0.09 190)"
  primary-soft: "oklch(0.955 0.025 190)"
  success: "oklch(0.52 0.12 155)"
  warning: "oklch(0.70 0.15 75)"
  danger: "oklch(0.55 0.20 18)"
  info: "oklch(0.50 0.12 255)"
  border: "oklch(0.91 0.006 95)"
  input: "oklch(0.66 0.012 260)"
typography:
  metric: { fontFamily: "Inter Variable", fontSize: "32px", lineHeight: "36px", fontWeight: 600, numeric: tabular }
  title: { fontFamily: "Inter Variable", fontSize: "24px", lineHeight: "32px", fontWeight: 600 }
  heading: { fontFamily: "Inter Variable", fontSize: "18px", lineHeight: "28px", fontWeight: 600 }
  body: { fontFamily: "Inter Variable", fontSize: "14px", lineHeight: "20px", fontWeight: 400 }
  small: { fontFamily: "Inter Variable", fontSize: "13px", lineHeight: "18px", fontWeight: 400 }
  meta: { fontFamily: "Inter Variable", fontSize: "12px", lineHeight: "16px", fontWeight: 500 }
  ref: { fontFamily: "Geist Mono", fontSize: "13px", lineHeight: "20px", fontWeight: 400 }
radius: { sm: "6px", md: "8px", lg: "10px", xl: "14px", full: "9999px" }
spacing: { 1: "4px", 2: "8px", 3: "12px", 4: "16px", 5: "20px", 6: "24px", 8: "32px", 12: "48px" }
shadows:
  - { name: "float", value: "0 8px 24px -8px oklch(0.2 0.02 260 / 0.18), 0 1px 2px oklch(0.2 0.02 260 / 0.06)", purpose: "Popover, dropdown, command palette" }
  - { name: "sheet", value: "-12px 0 32px -12px oklch(0.2 0.02 260 / 0.2)", purpose: "Right-side rescue sheet" }
motion:
  - { name: "instant", value: "80ms", purpose: "Press feedback" }
  - { name: "fast", value: "150ms", purpose: "Hover, entry of small elements" }
  - { name: "base", value: "250ms", purpose: "Collapse, tab and dialog transitions" }
  - { name: "slow", value: "400ms", purpose: "Status change (invoice flips to paid)" }
  - { name: "hero", value: "600ms", purpose: "Recovered counter roll. Nothing is longer." }
  - { name: "ease-standard", value: "cubic-bezier(0.2, 0, 0, 1)", purpose: "Default" }
  - { name: "ease-exit", value: "cubic-bezier(0.4, 0, 1, 1)", purpose: "Leaving elements" }
breakpoints:
  - { name: "sm", value: "640px" }
  - { name: "md", value: "768px" }
  - { name: "lg", value: "1024px" }
  - { name: "xl", value: "1280px" }
icons:
  set: "lucide-react"
  source: "apps/web/src/components/ui"
  sizes: { sm: "16px", md: "20px" }
  style: { variant: "outline", strokeWidth: 1.75 }
  color: "currentColor"
components:
  button-primary:
    source: "apps/web/src/components/ui/button.tsx"
    backgroundColor: "{colors.primary}"
    textColor: "{colors.background}"
    radius: "{radius.md}"
    states: [hover, focus-visible, active, disabled, loading]
  approval-card:
    source: "apps/web/src/components/approval-card.tsx"
    backgroundColor: "{colors.card}"
    radius: "{radius.xl}"
    states: [default, hover, focus-visible, pending, approving, error]
---

# Retriever: design

Owner-facing web app for SG/MY SMEs. One question: **"Who owes me, what's broken, and what needs my yes?"** Built on shadcn/ui (Tailwind v4, OKLCH tokens) with Framer Motion. Companion files: `design-tokens.css` (theme, copy to `apps/web/src/styles/tokens.css`) and `motion.tsx` (motion primitives, copy to `apps/web/src/lib/motion.tsx`). Those two files are the source of truth for values; this document is the rulebook.

## 1. Design direction

**Creative North Star: "The Quiet Back Office."**

A good bookkeeper doesn't narrate. Things that resolve themselves show up as a quiet tick; only the things that need a human get a card. The interface should feel like a clean ledger with one warm, trustworthy accent, not a trading terminal and not a chatbot.

**Posture (Cooper).** Retriever is mostly *daemonic*: it works in the background and surfaces only when there's a problem. The dashboard is a *transient* visit: the owner opens it, clears the queue in under a minute, and leaves. So: obvious UI, few options, remembered choices, no dense expert chrome.

**Principles**
1. **Work queue first, charts second.** Finance dashboards are to-do lists wearing charts. The "Needs your yes" queue is the hero; the metric strip and forecast support it.
2. **Every number shows its source.** A small provenance tag (`HitPay · 2 min ago`, `Matched by rule`, `Suggested by AI`) sits on money figures and approvals. Trust comes from attribution, not decoration.
3. **Calm by default, motion only for meaning.** Motion confirms a state change (paid, approved, arrived). It never decorates. Nothing animates longer than 600 ms.
4. **AI is visible and bounded.** Tier-3 (LLM) suggestions always look different from rule matches and always need approval. Confidence is shown as a reason sentence, not just a percentage.
5. **One accent.** Teal is used for primary action and for "recovered money". Everything else is neutral plus semantic status colours.

**Anti-references (what it must not look like):** neon-on-black crypto dashboards; gradient hero cards; chat-bubble UI as the main surface; confetti or emoji celebration for money; dense bank-statement tables with no hierarchy.

**What we borrowed**

| Source | Pattern taken | Where it lands |
|---|---|---|
| Inspora (viewed live: white canvas, dark pill filter chips, soft-cornered cards, creator avatar on every card) | Pill filter chips above a feed; attribution on every item; labelled promotional/sponsor slot kept visually distinct; "New" badge; multi-item count; explicit loading text | Status filter chips on tables; provenance tag; **Simulated** (dry-run) banner as the distinct slot; "New" badge on fresh approvals; "+2 more" on grouped rescues; "Matching payments…" loading copy |
| Public fintech dashboard analyses (Mercury, Brex and similar, as analysed at adminlte.io/blog/fintech-dashboard-design-examples) | Work-queue-as-home, neutral palette with one accent, calm transitions | Overview layout, palette, motion rules |
| Mobbin "Finance sites" collection | **Not reviewed.** Mobbin blocks automated access (403) and its MCP needs a paid plan. Add 3–5 screenshots you like to `design/references/` and this table gets updated. | n/a |

Inspora is a gallery, so only its interaction structure transfers. Its type, colour and motion values were not verifiable from the page text and were not copied.

## 2. Information architecture

```
/                      landing page (F21): public front door, links into the demo
/dashboard             Overview: where the demo video starts
├── Needs your yes (approvals queue, max 5, "See all")
├── Metric strip: Recovered · Still at risk · Recovery rate · Involuntary churn · Auto-match rate
├── Rescue timeline (latest rescues with status chips)
└── 14-day cash forecast (EarlyBird) with gap band + offer card
/dashboard/queue       all approvals: matches, discounts, refunds (payee changes arrive in Phase 5)
/dashboard/invoices    table: ref, customer, amount, due, status, paid %, actions
/dashboard/payments    table: received, payer, amount, ref, match status, tier
/dashboard/rescues     table + detail sheet (failure reason, link, message, timeline)
/dashboard/audit       events feed, filter by subject; plain-English reasons
/dashboard/settings    currency, churn days, auto-match threshold, discount cap, tone
```

Navigation: left sidebar (shadcn `Sidebar`, collapsible to icons) on `lg+`; bottom tab bar (Overview, Queue, Payments, More) below `lg`. The Queue item carries a live count badge. The header holds command search and the theme toggle.

## 3. Landing page (F21)

Decision (23 Nov): the product gets a landing page, but the demo video opens straight on `/dashboard`. The landing page is the public front door for judges who open the submission link and for the README; it never appears in the 3-minute video. It is timeboxed to 90 minutes and is the first thing cut if the build runs behind (see the plan).

**Sections, top to bottom** (single column, max content width 1120, section gap 96 px desktop / 64 px mobile)

| # | Section | Content |
|---|---|---|
| 1 | Header | Wordmark, links (How it works, Methods, GitHub), `ThemeToggle`, primary button **Open the demo** → `/dashboard` |
| 2 | Hero | Headline "Get paid without chasing." Sub-line: Retriever recovers failed PayNow, DuitNow and card payments, matches stray transfers, and warns you before cash runs short. You approve only what's uncertain. Buttons: **Open the demo** (filled), **See how it works** (ghost). Beside or below it, a real `ApprovalCard` and a `MetricTile` fed by seeded data, labelled "Simulated" |
| 3 | The problem | Two or three figures, each linked to its source. Use only figures already sourced in the PRD (Xero SG 2025, Atradius SG 2025). Mei Ling's story as a one-paragraph pull quote, marked as illustrative |
| 4 | How it works | Four cards: Collect, Rescue, Reconcile, Forecast. One sentence each, one icon each |
| 5 | Methods | Wrapping grid (not a marquee): PayNow, DuitNow, FPX, Touch 'n Go, Boost, GrabPay, ShopeePay, cards. HitPay icon plus text label on each |
| 6 | Trust | Three statements taken from AGENTS.md: the AI never moves money, every action is in an append-only audit log, no card data is stored |
| 7 | Footer | "Built for HitPay Build Night", GitHub link, simulated-data note |

**Rules.** One filled teal element per section (the hero has two buttons, only **Open the demo** is filled). The hero preview uses the real components, not an image, so the landing page and the dashboard cannot drift apart. No stock photos, no gradient backgrounds, no logo wall. Landing copy follows the same plain-English rules as the app.

**Motion.** Sections enter once with `whileInView` using `fadeUp` (y 8 → 0, 150 ms, `viewport={{ once: true, margin: "-80px" }}`). The hero preview plays the real approval arrival once on load, then rests. No scroll-jacking, no parallax, no looping marquee. Under reduced motion everything renders in its final state.

## 4. Screens

**Overview, desktop (1280).** 12-column grid, 24 px gutters, max content width 1200. Order top to bottom: page header (title, `Simulated` banner if dry-run, command search) → **Needs your yes** (7 cols) beside **Forecast** (5 cols) → metric strip (5 tiles, full width) → rescue timeline. The queue sits top-left because that is where the eye lands first (F-pattern).

**Overview, mobile (390).** Single column: Needs your yes → metrics (2-column grid, compact) → rescues → forecast. Approve and Reject are full-width buttons at least 44 px tall. Sticky bottom tab bar; safe-area padding.

**Approval card** (custom, built on shadcn `Card` + `Button` + `Badge`)

```
┌───────────────────────────────────────────────────┐
│ ◉ Match suggestion · AI          New     2 min ago │
│ S$800.00  from "TAN AH KOW TRADING"                │
│ → INV-104 · Tan Trading Pte Ltd · S$800.00         │
│ 82% sure: amount matches exactly, payer name       │
│ matches a known alias, due 3 days ago.             │
│ HitPay · bank transfer · 14:02                     │
│ [ Approve ]  [ Pick another invoice ]  [ Reject ]  │
└───────────────────────────────────────────────────┘
```

Same layout for discounts ("Offer 1.5% (S$45) to get S$3,000 by Fri. Saves about S$70 of overdraft cost") and refunds. Rule: the header chip names the kind, the first line states the money, the reason is a full sentence, and the footer is provenance.

**Rescue detail sheet** (shadcn `Sheet`, right side, 480 px; full-screen on mobile). Order: failure reason in plain words ("Card declined: insufficient funds") → fallback method chips with the chosen one highlighted and the reason ("paid by DuitNow last time") → link + QR → drafted message with copy button → event timeline. Method chips use HitPay's official payment icons (16–24 px) with a text label, never icon alone.

**Refund dialog** (shadcn `Dialog`). Amount defaults to remaining refundable and is editable; reason; owner note. Submitting creates a card in the queue. Status chip walks `submitted → refunded`. Refunds are never one-click.

**Forecast card.** shadcn `chart` (Recharts): balance line in `chart-1`, shaded safety-buffer band in `chart-2` at 25% opacity, gap day marked in `chart-3` with a labelled point, offer card beneath. Text summary above the chart: "Lowest balance S$2,140 on Thu 3 Dec, S$860 below your buffer."

**Tables** (shadcn `Table` + TanStack Table). Filter chips above (status, method, tier), sticky header, money right-aligned in tabular figures, row height 48 px (56 px on touch). Row click opens a side sheet, not a new page.

## 5. Visual language

Values live in `design-tokens.css`. Roles and rules:

| Role | Token | Use |
|---|---|---|
| Canvas | `background` (warm off-white) / `card` (white) | Page, cards |
| Text | `foreground`, `muted-foreground` | Primary, secondary |
| Brand | `primary` (teal-700 family) | Primary buttons, focus ring, recovered money |
| Brand tint | `primary-soft` | Selected chip, paid-row flash, hover on queue cards |
| Success | `success` + soft pair | Paid, matched |
| Warning | `warning` + soft pair | At risk, awaiting approval |
| Danger | `danger` + soft pair | Failed, churned, rejected |
| Info | `info` + soft pair | Simulated data, neutral notices |

Contrast was computed for the light theme: body text 17:1, secondary text 5.8:1, primary button 5.2:1, every soft status pair 7.8–8.7:1. All pass WCAG 2.2 AA. Dark theme was measured too and also passes AA: text 17.8:1, primary 8.2:1, muted text on muted surface 6.45:1, success on background 8.3:1, danger on background 6.15:1, soft status pairs 9.6–10.7:1, primary-soft 10.3:1, input border on card 3.02:1 (the 3:1 non-text minimum). Both themes are in scope for the hackathon (decision 23 Nov). Light is the default and the theme used in the demo recording; dark is switched on with the header toggle and gets a visual QA pass in Phase 4 on the dashboard, queue and landing page.

**Theme toggle.** shadcn's `ThemeProvider` pattern with `next-themes` (`attribute="class"`, `defaultTheme="light"`, `enableSystem`, `disableTransitionOnChange`). The toggle is a three-option `DropdownMenu` (Light, Dark, System) on an icon `Button` with an `aria-label` of "Change theme". The first paint reads the stored choice before hydration, so there is no flash. Charts and status chips read tokens, never raw colours, so they switch with the class.

**Typography.** Inter Variable for UI, Geist Mono for references and IDs (`INV-104`, payment refs). All money uses `.money` (tabular figures, right-aligned). Scale: 32/36 metric, 24/32 title, 18/28 heading, 14/20 body, 13/18 small, 12/16 meta. Weights 400, 500, 600 only.

**Elevation.** Flat by default: 1 px borders, no resting shadows. `shadow-float` only on layers that float (popover, dropdown, command palette); `shadow-sheet` on the rescue sheet. Cards lift by border colour, not shadow, on hover.

**Radius.** Cards `xl` (14 px), controls `md` (8 px), chips and avatars `full`.

**Spacing.** 4 px scale. Card padding 20 px (16 px on mobile). Gap between cards 16 px. Section gap 24 px.

**Icons.** lucide-react, outline, 1.75 stroke, `currentColor`. Status uses icon + label + colour together.

**Named rules**
- **The One Accent Rule.** Teal appears on at most one filled element per card. Everything else is neutral.
- **The Money Rule.** Every amount shows its currency (`S$1,200.00`, `RM 1,200.00`), is right-aligned, and uses tabular figures.
- **The Never-Colour-Alone Rule.** Every status chip has an icon and a text label.
- **The Flat-By-Default Rule.** Shadows appear only on floating layers.

## 6. Interaction design

**Approval microinteraction (Saffer's four parts)**

| Part | Spec |
|---|---|
| Trigger | System: a new `approvals` row arrives (realtime). Manual: owner presses Approve, Reject, or `A` / `R` on the focused card |
| Rules | Tier-3 matches and discounts always need a human. Approving a match writes allocations and an event. Approving a refund creates a refund only if the approval row is `approved` (AGENTS.md rule 2). Rejecting asks for nothing, the reason is optional |
| Feedback | Arrive: slide down 8 px + fade, `New` badge for 10 s, queue count ticks. Approve: tick icon, card collapses, siblings close the gap. Error: card stays, inline message with retry |
| Loops and modes | No modes. Feedback is quieter the 5th time in a session: the tick stays, the toast is skipped |

**Undo versus confirm.** Reversible actions get **Undo**, not a confirmation dialog: approving a match shows an 8-second toast with Undo (it un-allocates). Irreversible actions get an explicit step: sending a discount offer to a customer and issuing a refund both open a confirm view that states amount, recipient and "this cannot be undone".

**Keyboard (perpetual-intermediate path).** `J` / `K` move through the queue, `A` approve, `R` reject, `Enter` open detail, `Cmd/Ctrl+K` command search (invoice ref, customer), `Esc` closes sheets. Every shortcut has a visible button; shortcuts are shown in tooltips.

**State matrix** (applies to approval card, metric tile, table row, method chip, forecast card)

| State | Treatment |
|---|---|
| Default | Border `border`, `card` background |
| Hover | Border darkens one step; queue cards get `primary-soft` background at 40% |
| Focus-visible | 2 px `ring`, 2 px offset, never removed |
| Active | Scale 0.98 for 80 ms on buttons |
| Disabled | 40% opacity, no pointer events, tooltip says why |
| Loading | shadcn `Skeleton` shaped like the final content; after 1 s add text ("Matching payments…") |
| Empty | One sentence plus the next action: "Nothing needs you. Retriever matched 14 payments today." |
| Error | `danger-soft` inline block, what happened in plain words, Retry |
| Dry-run | `info-soft` banner at the top: "Simulated data. No real money moves." |

**Responsiveness thresholds.** Under 100 ms no feedback needed. 100 ms to 1 s show a skeleton. Over 1 s show progress text. Optimistic updates for approve and reject; roll back with an error card if the server rejects.

## 7. Motion (Framer Motion)

Primitives live in `motion.tsx`: tokens, variants, `MotionProvider`, `RollingMoney`. Wrap the app root in `MotionProvider`. It uses `LazyMotion` with `domAnimation` in strict mode, so use `m.*` components, never `motion.*`. The `framer-motion` package is also published as `motion` (`import from "motion/react"`); the API is the same.

| Moment | Motion | Token |
|---|---|---|
| New approval arrives | `approvalCard` `hidden → show`: y −8 → 0, fade | `fast` 150 ms |
| Approve | Tick appears, card exits with height → 0, siblings slide up through `layout` | `base` 250 ms |
| Invoice flips to paid | Status chip `chipSwap` (scale 0.98 → 1, fade) plus the `row-paid-flash` CSS class (teal tint fading out) | `slow` 400 ms chip, 1.2 s tint |
| Recovered counter | `RollingMoney` spring, no bounce | `hero` ~600 ms |
| Rescue sheet opens | `sheetSlide`: x 24 → 0 with `spring.ui` | spring |
| Queue reorders | `layout` on cards, no custom easing | default |
| Page navigation | None. Content swaps instantly; skeletons handle waiting | n/a |
| Press | scale 0.98 | `instant` 80 ms |

**Rules**
- Animate only `transform` and `opacity` (plus height on collapse). Never animate layout properties on tables.
- Nothing blocks input. A user can click during any animation.
- `MotionConfig reducedMotion="user"` removes transform animations while keeping opacity. `RollingMoney` jumps straight to the value under reduced motion. The paid-row flash is disabled in CSS.
- No looping animation anywhere, no parallax, no confetti. The only continuous motion is the loading skeleton shimmer, and it stops under reduced motion.
- Stagger lists at 40 ms per item, capped at 8 items.

## 8. Demo choreography (3 minutes)

The video is judged on problem fit and craft, so the design has one deliberate **peak** and one deliberate **end** (peak-end rule).

| Time | Screen | Design moment |
|---|---|---|
| 0:00–0:20 | Opening story card (Mei Ling), cut to Overview | Calm, mostly empty queue. Establishes "silence is success" |
| 0:20–1:05 | Rescue: failed Stripe test card, sheet with method chips, PayNow link paid | **Peak:** the invoice row flips to paid, the Recovered counter rolls up, the tint fades. The one moment where all three motions play together |
| 1:05–1:45 | Payments: S$800 transfer with no reference, AI suggestion, one-key approve | Approval card arrives with `New`, reason sentence, Approve, Undo toast |
| 1:45–2:30 | Assistant reads HitPay data, forecast gap, discount proposal | Gap marker appears, offer card slides in, confirm step before sending |
| 2:30–2:40 | Architecture slide | Static |
| 2:40–3:00 | Audit trail with one approved refund, method coverage slide, real numbers from this run | **End:** a still, readable audit feed and the true totals. No animation, just proof |

Record at 1280×800 in the light theme with `prefers-reduced-motion` off. Seeded data stays labelled "Simulated" on screen in every take (AGENTS.md rule 10); the live take uses S$1 sandbox or live HitPay reads.

## 9. Copy and tone

- Plain English: "didn't go through", not "payment_intent failed".
- The agent explains itself: every automatic action has a one-line "why" in the audit feed.
- Rescue messages are polite, factual, one link. Tone setting: Friendly / Firm. Per-customer "Pause chasing".
- Buttons start with a verb: Approve, Reject, Send link, Copy message.
- Strings live in `messages/{en,zh,ms}.json`; English only for the demo.

## 10. Accessibility

- WCAG 2.2 AA contrast; visible focus ring; every action keyboard reachable; queue navigable with arrow keys or `J` / `K`.
- Touch targets at least 44×44 px.
- Charts have a text summary above them; chart colours are never the only carrier of meaning.
- `aria-live="polite"` on the metric strip and the queue count. Rolling numbers expose their final value through `aria-label`.
- Sheets and dialogs trap focus and return it to the trigger on close (shadcn defaults, do not override).
- Reduced motion honoured (see section 7).

## 11. Components (shadcn/ui and custom)

| Component | Source | Notes |
|---|---|---|
| Card, Button, Badge, Table, Tabs, Tooltip, Skeleton, Sheet, Dialog, Command, Sidebar, Sonner, Chart, Select, Input, Switch | shadcn/ui via `npx shadcn@latest add` | Restyle only through tokens, never by editing component internals |
| `ApprovalCard` | custom | Kinds: match, discount, refund. Variants by `kind` prop |
| `MetricTile` | custom | Label, `RollingMoney` or number, delta, provenance tag |
| `StatusChip` | custom on `Badge` | Icon + label + soft colour pair |
| `MethodChip` | custom | HitPay icon + method name; `selected` and `reason` props |
| `ProvenanceTag` | custom | `HitPay · 2 min ago`, `Matched by rule`, `Suggested by AI` |
| `DryRunBanner` | custom on `Alert` | `info-soft`, always at the top when `DRY_RUN` is true |
| `EventRow` | custom | Audit feed item with the plain-English reason |

## 12. Do's and Don'ts

**Do**
- **Do** put the approvals queue above the charts on Overview.
- **Do** show currency and use tabular figures on every amount.
- **Do** give every status an icon, a label and a colour.
- **Do** use Undo for reversible actions and an explicit confirm for refunds and customer-facing offers.
- **Do** keep every animation under 600 ms and only on transform, opacity, or collapse height.
- **Do** label AI-suggested matches as such, with a reason sentence.

**Don't**
- **Don't** use more than one filled teal element per card.
- **Don't** add resting shadows to cards.
- **Don't** use a method icon without its text label.
- **Don't** celebrate money with confetti, emoji or looping motion.
- **Don't** edit shadcn component internals to change colour or radius; change the token.
- **Don't** hardcode hex or px values in components when a token exists.

## 13. Known deviations

None yet: there is no implementation to audit. When `apps/web` exists, run the DESIGN.md audit against this file and record anything that drifts here.

## 14. Decisions and open items

Decided 23 Nov 2026:
1. **Landing page: yes (F21), but the demo opens straight on `/dashboard`.** The landing page is a timeboxed Could and is cut first if the 24 Nov 21:00 feature freeze is at risk (section 3).
2. **Light and dark both stay in scope**, with a header toggle. Light is the default and the recording theme; dark is QA'd in Phase 4 (section 5).

Still open:
- Which 3–5 Mobbin finance screens should replace the "not reviewed" row in section 1? Mobbin needs a paid plan and blocks automated access, so screenshots or links from you would be needed.
