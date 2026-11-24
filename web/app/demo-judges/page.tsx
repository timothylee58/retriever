"use client";

import type { CSSProperties } from "react";
import { ramp, useClock } from "../demo-reel/clock";

const paper = "oklch(0.985 0.003 95)";
const ink = "oklch(0.21 0.015 260)";
const muted = "oklch(0.46 0.015 260)";
const card = "#fff";
const line = "oklch(0.91 0.006 95)";
const teal = "oklch(0.45 0.09 190)";
const tealSoft = "oklch(0.955 0.025 190)";
const danger = "oklch(0.55 0.2 18)";

function money(n: number) {
  return `S$${n.toFixed(2)}`;
}

export default function JudgesReel() {
  const clock = useClock();
  const progress = Math.min(1, clock / 24000);
  const title = ramp(clock, 0, 280);
  const cards = [ramp(clock, 900, 380), ramp(clock, 1500, 380), ramp(clock, 2100, 380)];
  const rescue = ramp(clock, 4600, 420);
  const count = ramp(clock, 5200, 900, 1);
  const arrow = ramp(clock, 6400, 420, 1);
  const link = ramp(clock, 7000, 420);
  const match = ramp(clock, 10800, 420);
  const rows = [ramp(clock, 11400, 320), ramp(clock, 12200, 320)];
  const paid = ramp(clock, 13600, 500, 1);
  const queue = ramp(clock, 16800, 420);
  const end = ramp(clock, 20600, 420);

  const slide = (n: number, from = 28) => ({
    opacity: n,
    transform: `translateY(${(1 - n) * from}px)`,
  });

  const frame: CSSProperties = {
    position: "absolute",
    inset: 0,
    background: paper,
    padding: "72px 88px 56px",
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
        background: paper,
        color: ink,
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
        position: "relative",
      }}
    >
      <style>{`nextjs-portal{display:none !important}`}</style>
      <div style={{ position: "absolute", top: 0, left: 0, height: 6, width: `${progress * 100}%`, background: teal }} />

      <section style={{ ...frame, ...slide(title, 16) }}>
        <header style={{ display: "flex", justifyContent: "space-between", position: "absolute", top: 36, left: 88, right: 88 }}>
          <strong style={{ fontSize: 22, letterSpacing: "-0.03em" }}>Retriever</strong>
          <span style={{ color: muted, fontSize: 18 }}>Sandbox · 24 Nov 2026</span>
        </header>
        <div style={{ fontSize: 22, color: muted, marginBottom: 12 }}>Mei Ling’s Sunday</div>
        <h1 style={{ fontSize: 60, lineHeight: "68px", letterSpacing: "-0.04em", fontWeight: 600, margin: 0, maxWidth: 1200 }}>
          Fees arrive by card and PayNow. Failures sit in a spreadsheet.
        </h1>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 18, marginTop: 36 }}>
          {[
            ["Card declined", "Nobody follows up."],
            ["QR expired", "The parent thinks it is paid."],
            ["S$320 TAN", "No invoice on the bank line."],
          ].map(([heading, body], i) => (
            <article
              key={heading}
              style={{
                ...slide(cards[i]),
                background: card,
                border: `1px solid ${line}`,
                borderRadius: 14,
                padding: 22,
                boxShadow: cards[i] > 0.2 ? "0 10px 28px -18px oklch(0.2 0.02 260 / 0.35)" : "none",
              }}
            >
              <div style={{ height: 3, width: `${cards[i] * 100}%`, background: i === 2 ? teal : danger, marginBottom: 14 }} />
              <div style={{ fontSize: 28, fontWeight: 600 }}>{heading}</div>
              <p style={{ fontSize: 20, color: muted, margin: "8px 0 0" }}>{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section style={{ ...frame, ...slide(rescue) }}>
        <div style={{ fontSize: 20, color: muted }}>A declined card becomes PayNow</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 120px 1fr", gap: 8, marginTop: 28, alignItems: "center" }}>
          <article style={{ background: card, border: `1px solid ${line}`, borderRadius: 14, padding: 28, transform: `translateX(${(1 - rescue) * -40}px)` }}>
            <div style={{ color: danger, fontWeight: 600, fontSize: 18 }}>generic_decline</div>
            <div style={{ fontSize: 52, fontWeight: 600, marginTop: 8, fontVariantNumeric: "tabular-nums" }}>{money(420 * count)}</div>
            <div style={{ fontSize: 22, marginTop: 6 }}>INV-104C · Visa ···· 0002</div>
          </article>
          <div style={{ height: 3, background: teal, width: `${arrow * 100}%`, justifySelf: "center" }} />
          <article
            style={{
              opacity: link,
              transform: `translateX(${(1 - link) * 48}px)`,
              background: card,
              border: `1px solid ${teal}`,
              borderRadius: 14,
              padding: 28,
            }}
          >
            <div style={{ color: teal, fontWeight: 600 }}>Rescue · offered</div>
            <div style={{ fontSize: 28, fontWeight: 600, lineHeight: "36px", marginTop: 10 }}>
              Your card payment for INV-104C didn’t go through.
            </div>
            <div style={{ marginTop: 16, background: tealSoft, color: teal, borderRadius: 8, padding: "12px 14px", fontSize: 18 }}>
              Pay by PayNow
            </div>
          </article>
        </div>
      </section>

      <section style={{ ...frame, ...slide(match) }}>
        <div style={{ fontSize: 20, color: muted }}>The checkout carries the invoice number</div>
        <h2 style={{ fontSize: 48, margin: "8px 0 22px", letterSpacing: "-0.03em" }}>No one typed the match.</h2>
        <div style={{ background: card, border: `1px solid ${line}`, borderRadius: 14, overflow: "hidden" }}>
          {[
            ["payment.received", "PayNow · S$420.00 · INV-DEMO-1"],
            ["payment.matched", "Exact reference. Tier 1. No approval."],
          ].map(([type, reason], i) => (
            <div key={type} style={{ ...slide(rows[i], 10), display: "grid", gridTemplateColumns: "320px 1fr", padding: "18px 24px", borderBottom: `1px solid ${line}`, fontSize: 24 }}>
              <span>{type}</span>
              <span>{reason}</span>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "space-between", padding: "20px 24px", fontSize: 30, background: `oklch(0.955 0.025 190 / ${paid})` }}>
            <span>INV-DEMO-1</span>
            <span style={{ color: teal, fontWeight: 600, fontVariantNumeric: "tabular-nums", transform: `scale(${0.96 + paid * 0.04})` }}>
              {paid > 0.8 ? `paid · ${money(420 * paid)}` : "issued · S$420.00"}
            </span>
          </div>
        </div>
      </section>

      <section style={{ ...frame, ...slide(queue) }}>
        <div style={{ fontSize: 20, color: muted }}>Unnamed transfer</div>
        <h2 style={{ fontSize: 46, margin: "8px 0 22px", letterSpacing: "-0.03em", maxWidth: 1100 }}>
          It asks. A guess never marks an invoice paid.
        </h2>
        <article style={{ ...slide(queue, 20), background: card, border: `1px solid ${line}`, borderRadius: 14, padding: 28, maxWidth: 920 }}>
          <div style={{ color: muted, fontSize: 18 }}>Needs a yes</div>
          <div style={{ fontSize: 44, fontWeight: 600, fontVariantNumeric: "tabular-nums", marginTop: 6 }}>S$1.00</div>
          <p style={{ fontSize: 24, lineHeight: "34px", margin: "12px 0 0" }}>
            INV-WH-1 names no open invoice. Closest amount is INV-RESTART. Waiting.
          </p>
        </article>
      </section>

      <section style={{ ...frame, ...slide(end) }}>
        <div style={{ fontSize: 22, color: muted }}>Retriever</div>
        <h2 style={{ fontSize: 58, lineHeight: "68px", letterSpacing: "-0.04em", margin: "12px 0", maxWidth: 1100 }}>
          It writes the PayNow link. It does not move the money.
        </h2>
        <p style={{ fontSize: 26, color: muted, maxWidth: 900 }}>
          Append-only events. Refunds wait for a person. Card numbers stay at Stripe and HitPay.
        </p>
      </section>
    </main>
  );
}
