import { ApprovalCard } from "../../../components/approval-card";
import { MetricTile } from "../../../components/metric-tile";
import { api } from "../../../lib/api";

type Metrics = {
  recovered: number;
  failures: number;
  churned: number;
  recovery_rate: number;
  churn_rate: number;
  at_risk_minor: number;
};

type Rescue = {
  id: string;
  status: string;
  amount_minor: number;
  currency: string;
};

type QueueItem = { id: string; summary: string };

function money(minor: number, currency = "SGD") {
  const symbol = currency === "MYR" ? "RM " : "S$";
  return `${symbol}${(minor / 100).toFixed(2)}`;
}

export default async function DashboardPage() {
  const metrics = await api<Metrics>("/api/metrics").catch(() => null);
  const rescues = await api<Rescue[]>("/api/rescues").catch(() => []);
  const queue = await api<QueueItem[]>("/api/queue").catch(() => []);
  const rate = metrics ? `${Math.round(metrics.recovery_rate * 100)}%` : "—";
  const churn = metrics ? `${Math.round(metrics.churn_rate * 100)}%` : "—";

  return (
    <>
      <p className="banner">Sandbox. A PayNow checkout counts only after a signed webhook.</p>
      <div className="desk-head">
        <h1>Overview</h1>
      </div>
      <div className="split">
        <section>
          <h2>Needs your yes</h2>
          {queue.length === 0 ? <ApprovalCard /> : queue.map((item) => <p key={item.id}>{item.summary}</p>)}
        </section>
        <section className="card">
          <h2>14-day cash</h2>
          <p>Forecast stays on the simulated card until a HitPay balance snapshot is ingested.</p>
        </section>
      </div>
      <section className="strip" aria-live="polite">
        <MetricTile label="Recovered" value={String(metrics?.recovered ?? 0)} note="Rescues paid after the link" />
        <MetricTile label="Still at risk" value={metrics ? money(metrics.at_risk_minor) : "—"} note="Open rescues and unpaid invoices" />
        <MetricTile label="Recovery rate" value={rate} note={`${metrics?.recovered ?? 0} of ${metrics?.failures ?? 0} failures`} />
        <MetricTile label="Involuntary churn" value={churn} note={`${metrics?.churned ?? 0} unpaid after the window`} />
        <MetricTile label="Failures" value={String(metrics?.failures ?? 0)} note="Declines that opened a rescue" />
      </section>
      <section>
        <h2>Rescue timeline</h2>
        <div className="timeline">
          {rescues.length === 0 ? <p>No rescues yet.</p> : null}
          {rescues.map((row) => (
            <div className="row" key={row.id}>
              <span>{row.status}</span>
              <span>{row.currency}</span>
              <span className="money">{money(row.amount_minor, row.currency.trim())}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
