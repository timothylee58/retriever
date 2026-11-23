import { api } from "../../../lib/api";

type Rescue = { id: string; status: string; amount_minor: number; currency: string; message_draft: string | null };

export default async function RescuesPage() {
  const rows = await api<Rescue[]>("/api/rescues").catch(() => []);
  return (
    <>
      <h1>Rescues</h1>
      <ul>
        {rows.map((row) => (
          <li key={row.id}>
            {row.status} · {row.currency} {(row.amount_minor / 100).toFixed(2)}
            <div>{row.message_draft}</div>
          </li>
        ))}
      </ul>
    </>
  );
}
