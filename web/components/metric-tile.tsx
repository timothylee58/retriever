export function MetricTile({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note: string;
}) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong className="money">{value}</strong>
      <small>{note}</small>
    </article>
  );
}
