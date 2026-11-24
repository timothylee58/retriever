"use client";

import type { CSSProperties } from "react";
import { ramp, useClock } from "./clock";

const paper = "oklch(0.985 0.003 95)";
const ink = "oklch(0.21 0.015 260)";
const muted = "oklch(0.42 0.015 260)";
const card = "#fff";
const line = "oklch(0.91 0.006 95)";
const teal = "oklch(0.45 0.09 190)";
const tealSoft = "oklch(0.955 0.025 190)";
const danger = "oklch(0.55 0.2 18)";

function money(n: number) {
  return `S$${n.toFixed(2)}`;
}

export default function DemoReel() {
  const clock = useClock();
  const progress = Math.min(1, clock / 72000);
  const open = ramp(clock, 0, 280);
  const amount = ramp(clock, 1200, 1100, 1);
  const fail = ramp(clock, 11000, 420);
  const failCount = ramp(clock, 11800, 900, 1);
  const arrow = ramp(clock, 13600, 500, 1);
  const link = ramp(clock, 14800, 420);
  const note = ramp(clock, 19000, 360);
  const match = ramp(clock, 28000, 420);
  const rows = [ramp(clock, 29200, 320), ramp(clock, 30400, 320)];
  const paid = ramp(clock, 33000, 700, 1);
  const matchNote = ramp(clock, 36000, 360);
  const queue = ramp(clock, 48000, 420);
  const queueCard = ramp(clock, 50000, 400);
  const end = ramp(clock, 62000, 420);

  const slide = (n: number, from = 28) => ({
    opacity: n,
    transform: `translateY(${(1 - n) * from}px)`,
  });

  const frame: CSSProperties = {
    position: "absolute",
    inset: 0,
    background: paper,
    padding: "78px 88px 64px",
    boxSizing: "border-box",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
  };

  return (
    <main
      style={{
        width: 1600,
        height: 900,
        overflow: "hidden",
        position: "relative",
        background: paper,
        color: ink,
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <style>{`nextjs-portal{display:none !important}`}</style>
      <div style={{ position: "absolute", top: 0, left: 0, height: 6, width: `${progress * 100}%`, background: teal }} />

      <section style={{ ...frame, ...slide(open, 16) }}>
        <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.03em" }}>Demo</div>
        <h1 style={{ fontSize: 56, lineHeight: "64px", letterSpacing: "-0.04em", margin: "16px 0 0", maxWidth: 1200 }}>
          One fee. Card fails. PayNow pays it. The ledger marks it paid.
        </h1>
        <article
          style={{
            marginTop: 36,
            background: card,
            border: `1px solid ${line}`,
            borderRadius: 14,
            padding: "28px 32px",
            maxWidth: 720,
            boxShadow: "0 12px 28px -18px oklch(0.2 0.02 260 / 0.35)",
          }}
        >
          <div style={{ fontSize: 22 }}>Invoice issued · INV-DEMO-1</div>
          <div style={{ fontSize: 64, fontWeight: 600, marginTop: 8, fontVariantNumeric: "tabular-nums" }}>{money(420 * amount)}</div>
          <div style={{ fontSize: 22, color: muted, marginTop: 8 }}>Singapore sandbox · PayNow request created</div>
        </article>
      </section>

      <section style={{ ...frame, ...slide(fail) }}>
        <div style={{ fontSize: 28, fontWeight: 600 }}>Demo · card to PayNow</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 140px 1fr", gap: 8, marginTop: 28, alignItems: "center" }}>
          <article style={{ background: card, border: `1px solid ${line}`, borderRadius: 14, padding: 28, transform: `translateX(${(1 - fail) * -36}px)` }}>
            <div style={{ color: danger, fontSize: 22, fontWeight: 600 }}>generic_decline</div>
            <div style={{ fontSize: 56, fontWeight: 600, marginTop: 8, fontVariantNumeric: "tabular-nums" }}>{money(420 * failCount)}</div>
            <div style={{ fontSize: 24, marginTop: 8 }}>INV-104C · Visa ···· 0002</div>
          </article>
          <div style={{ height: 4, background: teal, width: `${arrow * 100}%`, justifySelf: "center", borderRadius: 2 }} />
          <article
            style={{
              opacity: link,
              transform: `translateX(${(1 - link) * 40}px)`,
              background: card,
              border: `1px solid ${teal}`,
              borderRadius: 14,
              padding: 28,
            }}
          >
            <div style={{ color: teal, fontSize: 22, fontWeight: 600 }}>PayNow rescue · offered</div>
            <div style={{ fontSize: 30, fontWeight: 600, lineHeight: "38px", marginTop: 12 }}>
              Your card payment for INV-104C didn’t go through.
            </div>
            <div style={{ marginTop: 18, background: tealSoft, color: teal, borderRadius: 8, padding: "14px 16px", fontSize: 22 }}>
              Pay by PayNow
            </div>
          </article>
        </div>
        <p style={{ ...slide(note, 12), fontSize: 24, lineHeight: "34px", marginTop: 24, maxWidth: 1100 }}>
          Same invoice. New rail. The link is a live HitPay sandbox checkout, not a retry of the declined card.
        </p>
      </section>

      <section style={{ ...frame, ...slide(match) }}>
        <div style={{ fontSize: 28, fontWeight: 600 }}>Demo · payment returns</div>
        <h2 style={{ fontSize: 46, letterSpacing: "-0.03em", margin: "12px 0 22px" }}>The checkout names the invoice. Nobody types the match.</h2>
        <div style={{ background: card, border: `1px solid ${line}`, borderRadius: 14, overflow: "hidden" }}>
          {[
            ["payment.received", "PayNow · S$420.00 · INV-DEMO-1"],
            ["payment.matched", "Exact reference. Tier 1. No approval."],
          ].map(([type, reason], i) => (
            <div key={type} style={{ ...slide(rows[i], 12), display: "grid", gridTemplateColumns: "340px 1fr", gap: 16, padding: "20px 28px", borderBottom: `1px solid ${line}`, fontSize: 26 }}>
              <span>{type}</span>
              <span>{reason}</span>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "22px 28px", fontSize: 32, background: `oklch(0.955 0.025 190 / ${paid})` }}>
            <span>INV-DEMO-1</span>
            <span style={{ color: teal, fontWeight: 600, fontVariantNumeric: "tabular-nums", transform: `scale(${0.94 + paid * 0.06})` }}>
              {paid > 0.82 ? `paid · ${money(420 * Math.min(1, paid))}` : "issued · S$420.00"}
            </span>
          </div>
        </div>
        <p style={{ ...slide(matchNote, 10), fontSize: 24, lineHeight: "34px", marginTop: 20, maxWidth: 1100 }}>
          HitPay posted the completed payment. The signature checked. The reference was the invoice number.
        </p>
      </section>

      <section style={{ ...frame, ...slide(queue) }}>
        <div style={{ fontSize: 28, fontWeight: 600 }}>Demo · payment with no invoice name</div>
        <h2 style={{ fontSize: 46, letterSpacing: "-0.03em", margin: "12px 0 24px", maxWidth: 1180 }}>
          The payment still arrives. It waits for a yes.
        </h2>
        <article style={{ ...slide(queueCard, 18), background: card, border: `1px solid ${line}`, borderRadius: 14, padding: 32, maxWidth: 980, boxShadow: "0 12px 28px -18px oklch(0.2 0.02 260 / 0.35)" }}>
          <div style={{ fontSize: 22 }}>Needs a yes</div>
          <div style={{ fontSize: 52, fontWeight: 600, fontVariantNumeric: "tabular-nums", marginTop: 6 }}>S$1.00</div>
          <p style={{ fontSize: 26, lineHeight: "36px", margin: "12px 0 0" }}>
            INV-WH-1 names no open invoice. Closest amount is INV-RESTART. Mei Ling approves or rejects it.
          </p>
        </article>
      </section>

      <section style={{ ...frame, ...slide(end) }}>
        <div style={{ fontSize: 28, fontWeight: 600 }}>Demo</div>
        <h2 style={{ fontSize: 56, lineHeight: "66px", letterSpacing: "-0.04em", margin: "14px 0", maxWidth: 1180 }}>
          The payment flow writes a PayNow link. It does not move the money.
        </h2>
        <p style={{ fontSize: 28, lineHeight: "40px", maxWidth: 1000, color: muted, margin: 0 }}>
          Append-only events. Refunds wait for a person. Card numbers stay at Stripe and HitPay.
        </p>
      </section>
    </main>
  );
}
