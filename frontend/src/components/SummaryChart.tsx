import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

type Row = { attack: string; defense: string; budget: number; ASR: number };

export function SummaryChart({ rows }: { rows: Row[] }) {
  // Pivot: x = defense, series = attack@budget
  const defenses = Array.from(new Set(rows.map(r => r.defense)));
  const series = Array.from(new Set(rows.map(r => `${r.attack}_B${r.budget}`))).sort();
  const data = defenses.map(d => {
    const row: any = { defense: d };
    for (const s of series) {
      const [att, b] = s.split("_B");
      const r = rows.find(x => x.defense === d && x.attack === att && x.budget === Number(b));
      row[s] = r ? Number((r.ASR * 100).toFixed(1)) : 0;
    }
    return row;
  });
  const colors = ["#f87171", "#fbbf24", "#60a5fa", "#34d399", "#a78bfa", "#fb7185"];
  return (
    <div className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
          <XAxis dataKey="defense" stroke="#a1a1aa" />
          <YAxis stroke="#a1a1aa" unit="%" />
          <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #3f3f46" }}
                   formatter={(v: any) => `${v}%`} />
          <Legend />
          {series.map((s, i) => (
            <Bar key={s} dataKey={s} fill={colors[i % colors.length]} radius={[6, 6, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
