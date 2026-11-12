/** Small bars for a series of periods. The last period is in full colour, the rest are muted. */
export default function Sparkline({
  values,
  label,
  height = 40,
}: {
  values: number[];
  label: string;
  height?: number;
}) {
  const max = Math.max(...values, 1);
  return (
    <div role="img" aria-label={label} style={{ display: "flex", alignItems: "flex-end", gap: 3, height }}>
      {values.map((v, i) => (
        <span
          key={i}
          style={{
            display: "block",
            width: 9,
            height: Math.max(2, Math.round((v / max) * height)),
            borderRadius: "2px 2px 0 0",
            background: i === values.length - 1 ? "var(--data-1)" : "var(--data-muted)",
          }}
        />
      ))}
    </div>
  );
}
