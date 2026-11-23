import { api } from "../lib/api";

type Metrics = {
  recovered: number;
  failures: number;
  churned: number;
  recovery_rate: number;
  churn_rate: number;
  at_risk_minor: number;
};

export default async function Page() {
  let metrics: Metrics | null = null;
  let error = "";
  try {
    metrics = await api<Metrics>("/api/metrics");
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }
  return (
    <>
      <h1>Retriever</h1>
      <p>Failed payments rescued, unreferenced transfers queued, cash gap shown before rent day.</p>
      {error ? <p>{error}. Start the API with the command in the README.</p> : null}
      {metrics ? (
        <section className="grid">
          <article className="card"><h2>Recovered</h2><p>{metrics.recovered}</p></article>
          <article className="card"><h2>Failures</h2><p>{metrics.failures}</p></article>
          <article className="card"><h2>Recovery rate</h2><p>{(metrics.recovery_rate * 100).toFixed(0)}%</p></article>
          <article className="card"><h2>Churn rate</h2><p>{(metrics.churn_rate * 100).toFixed(0)}%</p></article>
          <article className="card"><h2>Still at risk</h2><p>{(metrics.at_risk_minor / 100).toFixed(2)}</p></article>
        </section>
      ) : null}
    </>
  );
}
