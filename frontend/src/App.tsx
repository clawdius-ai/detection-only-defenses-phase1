import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { API } from "@/lib/utils";
import { SessionGraph } from "@/components/SessionGraph";
import { SummaryChart } from "@/components/SummaryChart";

type SummaryRow = {
  attack: string;
  defense: string;
  budget: number;
  N: number;
  ASR: number;
  block_rate: number;
  mean_judge: number;
  total_rounds: number;
};

type SessionMeta = {
  session_id: string;
  attack: string;
  defense: string;
  budget: number;
  advbench_index: number;
  goal: string;
  max_score: number;
  success: boolean;
  rounds: number;
};

export default function App() {
  const [summary, setSummary] = useState<SummaryRow[]>([]);
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ attack?: string; defense?: string }>({});

  useEffect(() => {
    fetch(`${API}/summary`).then(r => r.json()).then(d => setSummary(d.summary || []));
    fetch(`${API}/sessions`).then(r => r.json()).then(d => setSessions(d.sessions || []));
  }, []);

  const filtered = useMemo(() => sessions.filter(s =>
    (!filter.attack || s.attack === filter.attack) &&
    (!filter.defense || s.defense === filter.defense)
  ), [sessions, filter]);

  return (
    <div className="min-h-screen p-6 max-w-[1400px] mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Detection-Only Defenses for LLMs — Phase 1
        </h1>
        <p className="text-sm text-zinc-400 mt-1">
          Adaptive jailbreak attacks (PAIR, TAP) vs. detector-only defenses on AdvBench.
        </p>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Attack Success Rate by Defense</CardTitle></CardHeader>
          <CardContent><SummaryChart rows={summary} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Experiment Cells</CardTitle></CardHeader>
          <CardContent className="space-y-2 max-h-[320px] overflow-auto">
            {summary.map((r, i) => (
              <div key={i} className="flex items-center justify-between text-sm gap-2">
                <div className="flex gap-1 items-center">
                  <Badge variant="muted">{r.attack}</Badge>
                  <Badge variant={r.defense === "none" ? "muted" : "default"}>{r.defense}</Badge>
                  <Badge variant="muted">B={r.budget}</Badge>
                </div>
                <div className="text-zinc-300">
                  ASR <span className="font-semibold">{(r.ASR * 100).toFixed(1)}%</span>
                  {" · "}block {(r.block_rate * 100).toFixed(0)}%
                </div>
              </div>
            ))}
            {!summary.length && <p className="text-sm text-zinc-500">No traces yet. Run experiments first.</p>}
          </CardContent>
        </Card>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-1">
          <CardHeader><CardTitle>Sessions</CardTitle></CardHeader>
          <CardContent className="space-y-2 max-h-[640px] overflow-auto">
            <div className="flex gap-2 mb-3 text-xs">
              <select className="bg-zinc-800 px-2 py-1 rounded"
                onChange={e => setFilter(f => ({ ...f, attack: e.target.value || undefined }))}>
                <option value="">all attacks</option>
                <option value="pair">pair</option><option value="tap">tap</option>
              </select>
              <select className="bg-zinc-800 px-2 py-1 rounded"
                onChange={e => setFilter(f => ({ ...f, defense: e.target.value || undefined }))}>
                <option value="">all defenses</option>
                <option value="none">none</option>
                <option value="keyword">keyword</option>
                <option value="promptguard">promptguard</option>
                <option value="llamaguard">llamaguard</option>
              </select>
            </div>
            {filtered.map(s => (
              <button key={s.session_id}
                onClick={() => setSelected(s.session_id)}
                className={`w-full text-left rounded-lg border border-zinc-800 p-2 hover:bg-zinc-800/40 ${
                  selected === s.session_id ? "bg-zinc-800/60" : ""
                }`}>
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="muted">{s.attack}</Badge>
                  <Badge variant="muted">{s.defense}</Badge>
                  <Badge variant="muted">B={s.budget}</Badge>
                  {s.success
                    ? <Badge variant="danger">jailbroken</Badge>
                    : <Badge variant="success">refused</Badge>}
                </div>
                <div className="text-xs text-zinc-400 truncate">{s.goal}</div>
                <div className="text-[10px] text-zinc-500 mt-1">
                  rounds {s.rounds} · max score {s.max_score}
                </div>
              </button>
            ))}
            {!filtered.length && <p className="text-sm text-zinc-500">No sessions.</p>}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              Attack Trace Graph {selected && <span className="text-zinc-500 ml-2 text-xs">{selected}</span>}
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[640px] p-0">
            {selected ? <SessionGraph sessionId={selected} />
              : <div className="h-full flex items-center justify-center text-sm text-zinc-500">
                  Select a session to view its attack trace.
                </div>}
          </CardContent>
        </Card>
      </section>

      <footer className="mt-8 text-xs text-zinc-500">
        AdvBench harmful_behaviors · attacker = Vicuna-13B (OpenRouter) ·
        target/judge = GPT-4 · detectors = PromptGuard / Llama-Guard-3 / keyword.
      </footer>
    </div>
  );
}
