import { api } from "../../lib/api";

type EventRow = { occurred_at: string; actor: string; type: string; reason: string };

export default async function AuditPage() {
  const rows = await api<EventRow[]>("/api/events").catch(() => []);
  return (
    <>
      <h1>Audit trail</h1>
      <ul>
        {rows.map((row) => (
          <li key={`${row.occurred_at}-${row.type}`}>
            {row.occurred_at} · {row.actor} · {row.type} — {row.reason}
          </li>
        ))}
      </ul>
    </>
  );
}
