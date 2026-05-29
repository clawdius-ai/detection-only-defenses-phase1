import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
         CartesianGrid, Legend, LabelList } from "recharts";

type Row = {
  attack: string;
  defense: string;
  budget: number;
  N: number;
  ASR: number;
  ASR_at_threshold?: number;
  block_rate?: number;
  mean_judge?: number;
};

type Metric = "ASR" | "ASR_at_threshold";

const SERIES_COLORS: Record<string, string> = {
  pair_B5:  "#f87171",   // red-400
  pair_B10: "#dc2626",   // red-600
  tap_B5:   "#60a5fa",   // blue-400
  tap_B10:  "#2563eb",   // blue-600
};
const FALLBACK_COLORS = ["#fbbf24", "#34d399", "#a78bfa", "#fb7185"];

// Stable defense ordering so the chart x-axis is predictable.
const DEFENSE_ORDER = ["none", "keyword", "promptguard", "llamaguard"];

export function SummaryChart({
  rows,
  metric = "ASR_at_threshold",
  thresholdLabel,
}: { rows: Row[]; metric?: Metric; thresholdLabel?: string }) {
  const pickValue = (r: Row): number => {
    if (metric === "ASR_at_threshold" && r.ASR_at_threshold != null) {
      return r.ASR_at_threshold;
    }
    return r.ASR;
  };
  const defenses = Array.from(new Set(rows.map(r => r.defense)))
    .sort((a, b) => {
      const ia = DEFENSE_ORDER.indexOf(a);
      const ib = DEFENSE_ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
  const series = Array.from(new Set(rows.map(r => `${r.attack}_B${r.budget}`))).sort();

  const data = defenses.map(d => {
    const row: Record<string, number | string> = { defense: d };
    for (const s of series) {
      const [att, b] = s.split("_B");
      const r = rows.find(x => x.defense === d && x.attack === att && x.budget === Number(b));
      // Use null-ish 0 if no data so empty bars are visible (but tooltip will note "no data").
      row[s] = r ? Number((pickValue(r) * 100).toFixed(1)) : 0;
      row[`${s}__N`] = r ? r.N : 0;
    }
    return row;
  });

  const colorFor = (key: string, idx: number) =>
    SERIES_COLORS[key] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    return (
      <div className="rounded-md border border-zinc-700 bg-zinc-900/95 px-3 py-2 text-xs shadow">
        <div className="mb-1 font-semibold text-zinc-100">defense: {label}</div>
        {payload.map((p: any) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4">
            <span style={{ color: p.color }}>{p.dataKey}</span>
            <span className="font-mono text-zinc-100">
              {p.value}%{p.payload[`${p.dataKey}__N`]
                ? ` (N=${p.payload[`${p.dataKey}__N`]})`
                : ""}
            </span>
          </div>
        ))}
      </div>
    );
  };

  const label = metric === "ASR_at_threshold"
    ? `ASR @ judge ${thresholdLabel ?? "≥ 7"}`
    : "ASR (strict, judge = 10)";
  return (
    <div className="h-[320px]">
      <div className="px-1 pb-1 text-[11px] uppercase tracking-wide text-zinc-500">{label}</div>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 14, right: 12, bottom: 4, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis dataKey="defense" stroke="#a1a1aa" />
          <YAxis stroke="#a1a1aa" domain={[0, 100]} unit="%" />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {series.map((s, i) => (
            <Bar key={s} dataKey={s} fill={colorFor(s, i)} radius={[6, 6, 0, 0]}
                 minPointSize={3}>
              <LabelList
                dataKey={s}
                position="top"
                formatter={(v: any) => (typeof v === "number" && v > 0 ? `${v}%` : "")}
                fill="#e4e4e7"
                fontSize={10}
              />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
