import { ApprovalCard } from "../../../components/approval-card";
import { MetricTile } from "../../../components/metric-tile";

const rescues = [
  ["Offered", "INV-104", "S$420.00"],
  ["Recovered", "INV-098", "S$180.00"],
  ["Churned", "INV-091", "S$95.00"],
];

export default function DashboardPage() {
  return (
    <>
      <p className="banner">Simulated data. No real money moves.</p>
      <div className="desk-head">
        <h1>Overview</h1>
      </div>
      <div className="split">
        <section>
          <h2>Needs your yes</h2>
          <ApprovalCard />
        </section>
        <section className="card">
          <h2>14-day cash</h2>
          <p>Lowest balance S$2,140 on Thu 3 Dec, S$860 below your buffer.</p>
          <svg className="chart" viewBox="0 0 320 120" role="img" aria-label="Balance falls below the buffer on day 9">
            <rect x="0" y="48" width="320" height="28" fill="oklch(0.955 0.025 190)" opacity="0.7" />
            <polyline fill="none" stroke="oklch(0.51 0.09 190)" strokeWidth="2" points="0,40 40,46 80,52 120,60 160,78 200,96 240,88 280,70 320,64" />
            <circle cx="200" cy="96" r="4" fill="oklch(0.55 0.20 18)" />
          </svg>
          <p>Offer 1.5% (S$45) on INV-118. The discount costs less than the gap.</p>
        </section>
      </div>
      <section className="strip" aria-live="polite">
        <MetricTile label="Recovered" value="S$420.00" note="This dry run" />
        <MetricTile label="Still at risk" value="S$1,280.00" note="Open rescues and queue" />
        <MetricTile label="Recovery rate" value="33%" note="1 of 3 failures" />
        <MetricTile label="Involuntary churn" value="33%" note="Unpaid after 7 days" />
        <MetricTile label="Auto-match rate" value="2 of 3" note="Matched by rule" />
      </section>
      <section>
        <h2>Rescue timeline</h2>
        <div className="timeline">
          {rescues.map(([status, ref, amount]) => (
            <div className="row" key={ref}>
              <span>{status}</span>
              <span>{ref}</span>
              <span className="money">{amount}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
