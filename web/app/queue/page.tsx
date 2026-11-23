import { api } from "../../lib/api";

type Item = { id: string; kind: string; summary: string; status: string; payer_name: string | null };

export default async function QueuePage() {
  const items = await api<Item[]>("/api/queue").catch(() => []);
  return (
    <>
      <h1>Review queue</h1>
      <ul>
        {items.map((item) => (
          <li key={item.id}>{item.kind}: {item.summary}</li>
        ))}
      </ul>
      {items.length === 0 ? <p>Nothing is waiting for a decision.</p> : null}
    </>
  );
}
