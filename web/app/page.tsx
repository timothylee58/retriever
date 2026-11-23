import { ApprovalCard } from "../components/approval-card";
import { MetricTile } from "../components/metric-tile";
import { ThemeToggle } from "../components/theme-toggle";
import { Landmark, Link2, LineChart, ScanSearch } from "lucide-react";

const steps = [
  { icon: Landmark, title: "Collect the invoice", body: "Each invoice leaves as a HitPay request carrying its own reference." },
  { icon: Link2, title: "Rescue the failure", body: "A declined card becomes a fresh PayNow or DuitNow link." },
  { icon: ScanSearch, title: "Reconcile the transfer", body: "A payment with no reference waits in the queue until you say yes." },
  { icon: LineChart, title: "Forecast the gap", body: "A discount is offered only when it costs less than the cash gap." },
];

const methods = ["PayNow", "DuitNow", "FPX", "Touch 'n Go", "Boost", "GrabPay", "ShopeePay", "Cards"];

export default function LandingPage() {
  return (
    <>
      <a className="skip" href="#top">Skip to content</a>
      <header className="site-header">
        <a className="wordmark" href="#top">Retriever</a>
        <nav className="site-nav" aria-label="Page">
          <a href="#how">How it works</a>
          <a href="#methods">Methods</a>
          <a href="https://github.com/timothylee58/retriever">GitHub</a>
        </nav>
        <ThemeToggle />
        <a className="btn btn-primary" href="/dashboard">Open the demo</a>
      </header>
      <main id="top">
        <section className="wrap hero">
          <div>
            <h1>Get paid without chasing.</h1>
            <p className="lede">
              Retriever recovers failed PayNow, DuitNow and card payments, matches stray transfers, and warns you before cash runs short. You approve only what is uncertain.
            </p>
            <div className="btn-row">
              <a className="btn btn-primary" href="/dashboard">Open the demo</a>
              <a className="btn btn-ghost" href="#how">See how it works</a>
            </div>
            <p className="fact">91% of Singapore SMEs say late payment affects them. Xero, 2025.</p>
          </div>
          <div>
            <p className="badge" style={{ display: "inline-block", marginBottom: 12 }}>Simulated</p>
            <ApprovalCard />
            <div style={{ height: 12 }} />
            <MetricTile label="Recovered" value="S$420.00" note="HitPay · this dry run" />
          </div>
        </section>

        <section className="section" id="problem">
          <div className="wrap">
            <h2>Late payment, unmatched transfers</h2>
            <p>The figures below are from the sources named in the product brief. Mei Ling is an illustrative persona, not a customer.</p>
            <div className="figures">
              <article className="figure"><strong>91%</strong><p>of Singapore SMEs say late payment affects them. Xero, 2025.</p></article>
              <article className="figure"><strong>43%</strong><p>say it affects them significantly. Xero, 2025.</p></article>
              <article className="figure"><strong>35%</strong><p>of B2B credit sales in Singapore are overdue on average. Atradius, 2025.</p></article>
            </div>
            <blockquote className="quote">
              Mei Ling runs a tuition centre in Petaling Jaya with a second branch in Singapore. By the 5th, declined cards, expired QR codes and a line that says “S$320 TAN” still sit in a spreadsheet.
              <span>Illustrative opening story from the product brief.</span>
            </blockquote>
          </div>
        </section>

        <section className="section" id="how">
          <div className="wrap">
            <h2>Four jobs, one queue</h2>
            <div className="cards">
              {steps.map((step) => (
                <article className="card" key={step.title}>
                  <step.icon aria-hidden size={20} strokeWidth={1.75} />
                  <h3>{step.title}</h3>
                  <p>{step.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="methods">
          <div className="wrap">
            <h2>PayNow through to cards</h2>
            <div className="methods">
              {methods.map((name) => (
                <p className="method" key={name}><span className="badge">HitPay</span>{name}</p>
              ))}
            </div>
          </div>
        </section>

        <section className="section" id="trust">
          <div className="wrap">
            <h2>What the agent will not do</h2>
            <div className="trust">
              <article className="card"><h3>No money movement</h3><p>The agent creates payment links. Refunds wait for your approval.</p></article>
              <article className="card"><h3>An audit row</h3><p>Every state change is appended. The log is not edited.</p></article>
              <article className="card"><h3>No card numbers</h3><p>Stripe and HitPay hold the card. Retriever stores the payer’s name and the outcome.</p></article>
            </div>
          </div>
        </section>
      </main>
      <footer className="wrap site-footer">
        <span>Built for HitPay Build Night</span>
        <a href="https://github.com/timothylee58/retriever">GitHub</a>
        <span>Figures on this page are sourced. The queue preview is simulated.</span>
      </footer>
    </>
  );
}
