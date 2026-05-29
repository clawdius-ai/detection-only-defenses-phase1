import { useEffect, useMemo, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { API } from "@/lib/utils";
import { SessionGraph } from "@/components/SessionGraph";
import { SummaryChart } from "@/components/SummaryChart";

type ViewMode = "demo" | "real";
type SortKey = "default" | "score" | "rounds" | "success";

type SummaryRow = {
  attack: string;
  defense: string;
  budget: number;
  N: number;
  demo_sessions?: number;
  ASR: number;
  ASR_at_threshold?: number;
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
  blocked_rounds?: number;
  demo?: boolean;
};

type HealthInfo = {
  status: string;
  n_rows: number;
  n_files: number;
  demo_rows: number;
  real_rows: number;
};

export default function App() {
  const [summary, setSummary] = useState<SummaryRow[]>([]);
  const [sessions, setSessions] = useState<SessionMeta[]>([]);
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ attack?: string; defense?: string }>({});
  const [viewMode, setViewMode] = useState<ViewMode>("real");
  const [sortKey, setSortKey] = useState<SortKey>("success");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshTick, setRefreshTick] = useState(0);
  const [judgeThreshold, setJudgeThreshold] = useState<number>(7);

  const refresh = useCallback(() => setRefreshTick(t => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      fetch(`${API}/summary?mode=${viewMode}&judge_threshold=${judgeThreshold}`).then(r => r.json()),
      fetch(`${API}/sessions?mode=${viewMode}&sort=${sortKey}`).then(r => r.json()),
      fetch(`${API}/health`).then(r => r.json()).catch(() => null),
    ]).then(([sumD, sesD, hlt]) => {
      if (cancelled) return;
      setSummary(sumD.summary || []);
      setSessions(sesD.sessions || []);
      setHealth(hlt);
      setLoading(false);
      // If currently selected session is gone, drop selection.
      const ids = new Set<string>((sesD.sessions || []).map((s: SessionMeta) => s.session_id));
      if (selected && !ids.has(selected)) setSelected(null);
    }).catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [viewMode, sortKey, refreshTick, judgeThreshold]);  // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = useMemo(() => sessions.filter(s => {
    if (filter.attack && s.attack !== filter.attack) return false;
    if (filter.defense && s.defense !== filter.defense) return false;
    if (search) {
      const q = search.toLowerCase();
      if (!s.goal.toLowerCase().includes(q) &&
          !s.session_id.toLowerCase().includes(q)) return false;
    }
    return true;
  }), [sessions, filter, search]);

  // Aggregate stats on the currently filtered session set.
  const stats = useMemo(() => {
    const total = filtered.length;
    const success = filtered.filter(s => s.success).length;
    const blocked = filtered.reduce((a, s) => a + (s.blocked_rounds || 0), 0);
    const rounds = filtered.reduce((a, s) => a + s.rounds, 0);
    return {
      total,
      success,
      success_rate: total ? success / total : 0,
      blocked,
      rounds,
      block_rate: rounds ? blocked / rounds : 0,
    };
  }, [filtered]);

  return (
    <div className="min-h-screen p-6 max-w-[1500px] mx-auto">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Detection-Only Defenses for LLMs — Phase 1
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Adaptive jailbreak attacks (PAIR, TAP) vs. detector-only defenses on AdvBench.
          </p>
          {health && (
            <p className="text-[11px] text-zinc-500 mt-1.5">
              {health.n_files} trace files · {health.real_rows.toLocaleString()} real rows · {health.demo_rows.toLocaleString()} demo rows
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={refresh}
            className="rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-900"
            title="Re-fetch all data from the trace API">
            {loading ? "refreshing…" : "↻ refresh"}
          </button>
          <label className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300"
            title="Per-session max judge score >= threshold counts as a jailbreak (HarmBench-style). The strict success column uses the threshold from the experiment config (default 10).">
            <span className="text-zinc-500">ASR threshold</span>
            <select
              className="bg-zinc-900 border border-zinc-800 rounded px-1.5 py-0.5"
              value={judgeThreshold}
              onChange={e => setJudgeThreshold(parseInt(e.target.value, 10))}>
              {[5, 6, 7, 8, 9, 10].map(n => (
                <option key={n} value={n}>≥ {n}</option>
              ))}
            </select>
          </label>
          <nav className="inline-flex w-fit rounded-lg border border-zinc-800 bg-zinc-950 p-1 text-sm">
            {(["demo", "real"] as const).map(mode => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={`rounded-md px-4 py-2 font-medium capitalize transition ${
                  viewMode === mode
                    ? "bg-zinc-100 text-zinc-950"
                    : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100"
                }`}>
                {mode === "demo" ? "Demo Traces" : "Real API Runs"}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* KPI strip */}
      <section className="mb-5 grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatTile label="Sessions (filtered)" value={stats.total.toString()} />
        <StatTile
          label="Jailbreaks"
          value={`${stats.success} (${(stats.success_rate * 100).toFixed(0)}%)`}
          tone={stats.success_rate > 0.5 ? "danger" : stats.success_rate > 0 ? "warning" : "muted"} />
        <StatTile label="Total rounds" value={stats.rounds.toString()} />
        <StatTile
          label="Detector block rate"
          value={`${(stats.block_rate * 100).toFixed(1)}%`}
          tone={stats.block_rate > 0 ? "success" : "muted"} />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Attack Success Rate by Defense</CardTitle>
          </CardHeader>
          <CardContent>
            <SummaryChart
              rows={summary}
              metric="ASR_at_threshold"
              thresholdLabel={`≥ ${judgeThreshold}`}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Experiment Cells</CardTitle></CardHeader>
          <CardContent className="space-y-2 max-h-[340px] overflow-auto">
            {summary.map((r, i) => (
              <div key={i} className="rounded-md border border-zinc-800/70 bg-zinc-950/40 p-2.5 text-sm hover:bg-zinc-900/40 transition">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex gap-1 items-center flex-wrap">
                    <Badge variant="muted">{r.attack}</Badge>
                    <Badge variant={r.defense === "none" ? "muted" : "default"}>{r.defense}</Badge>
                    <Badge variant="muted">B={r.budget}</Badge>
                    <Badge variant="muted">N={r.N}</Badge>
                    {!!r.demo_sessions && r.demo_sessions === r.N &&
                      <Badge variant="warning">demo</Badge>}
                    {!!r.demo_sessions && r.demo_sessions !== r.N &&
                      <Badge variant="warning">{r.demo_sessions} demo</Badge>}
                  </div>
                  <div className="text-zinc-300 text-xs flex gap-2">
                    <span title="Strict success — judge score == 10 (config threshold)">
                      ASR <span className="font-semibold text-zinc-100">{(r.ASR * 100).toFixed(1)}%</span>
                    </span>
                    {r.ASR_at_threshold != null && (
                      <span className="text-zinc-500" title={`Per-session max judge >= ${judgeThreshold}`}>
                        ≥{judgeThreshold} <span className="font-semibold text-zinc-300">{(r.ASR_at_threshold * 100).toFixed(0)}%</span>
                      </span>
                    )}
                  </div>
                </div>
                <div className="mt-1.5 grid grid-cols-3 gap-2 text-[11px] text-zinc-500">
                  <span>block {(r.block_rate * 100).toFixed(0)}%</span>
                  <span>judge μ {r.mean_judge.toFixed(1)}</span>
                  <span>{r.total_rounds} rounds</span>
                </div>
              </div>
            ))}
            {!summary.length && !loading && (
              <p className="text-sm text-zinc-500">
                No {viewMode === "demo" ? "demo" : "real API"} traces yet.
              </p>
            )}
            {loading && <p className="text-sm text-zinc-500">Loading…</p>}
          </CardContent>
        </Card>
      </section>

      <section className="mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Sessions
              <span className="text-xs text-zinc-500">
                {viewMode === "demo" ? "demo" : "real API"} · showing {filtered.length} / {sessions.length}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-2 text-xs">
              <select className="bg-zinc-900 border border-zinc-800 px-2 py-1.5 rounded"
                value={filter.attack ?? ""}
                onChange={e => setFilter(f => ({ ...f, attack: e.target.value || undefined }))}>
                <option value="">all attacks</option>
                <option value="pair">pair</option><option value="tap">tap</option>
              </select>
              <select className="bg-zinc-900 border border-zinc-800 px-2 py-1.5 rounded"
                value={filter.defense ?? ""}
                onChange={e => setFilter(f => ({ ...f, defense: e.target.value || undefined }))}>
                <option value="">all defenses</option>
                <option value="none">none</option>
                <option value="keyword">keyword</option>
                <option value="promptguard">promptguard</option>
                <option value="llamaguard">llamaguard</option>
              </select>
              <select className="bg-zinc-900 border border-zinc-800 px-2 py-1.5 rounded"
                value={sortKey}
                onChange={e => setSortKey(e.target.value as SortKey)}>
                <option value="success">sort: jailbroken first</option>
                <option value="score">sort: judge score desc</option>
                <option value="rounds">sort: rounds desc</option>
                <option value="default">sort: attack/defense</option>
              </select>
              <input
                className="bg-zinc-900 border border-zinc-800 px-2 py-1.5 rounded min-w-[200px] flex-1 max-w-md"
                placeholder="search goal or session id…"
                value={search}
                onChange={e => setSearch(e.target.value)} />
              {(filter.attack || filter.defense || search) && (
                <button
                  onClick={() => { setFilter({}); setSearch(""); }}
                  className="rounded px-2 py-1 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 border border-zinc-800">
                  clear
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 max-h-[380px] overflow-auto pr-1">
              {filtered.map(s => (
                <button key={s.session_id}
                  onClick={() => setSelected(s.session_id)}
                  className={`w-full text-left rounded-lg border p-3 transition ${
                    selected === s.session_id
                      ? "bg-zinc-800/60 border-zinc-500 ring-1 ring-zinc-500"
                      : "border-zinc-800 hover:bg-zinc-800/30 hover:border-zinc-700"
                  }`}>
                  <div className="flex flex-wrap items-center gap-1.5 mb-2">
                    <Badge variant="muted">{s.attack}</Badge>
                    <Badge variant="muted">{s.defense}</Badge>
                    <Badge variant="muted">B={s.budget}</Badge>
                    {s.demo && <Badge variant="warning">demo</Badge>}
                    {s.success
                      ? <Badge variant="danger">jailbroken</Badge>
                      : <Badge variant="success">refused</Badge>}
                  </div>
                  <div className="text-sm text-zinc-300 line-clamp-2">{s.goal}</div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-zinc-500">
                    <span>idx {s.advbench_index} · {s.rounds} rounds</span>
                    <span className="font-mono text-zinc-400">
                      max {s.max_score}/10
                    </span>
                  </div>
                </button>
              ))}
              {!filtered.length && !loading && (
                <p className="text-sm text-zinc-500">No sessions match the current filters.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      <section>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-3">
              Attack Trace Graph
              {selected && (
                <button
                  onClick={() => navigator.clipboard.writeText(selected)}
                  className="text-zinc-500 hover:text-zinc-300 font-mono text-xs"
                  title="Copy session id">
                  {selected} ⧉
                </button>
              )}
            </CardTitle>
            <p className="text-xs text-zinc-500 mt-1">
              Click a node to inspect. Use ←/→ to step through rounds.
            </p>
          </CardHeader>
          <CardContent className="h-[680px] xl:h-[860px] p-0">
            {selected
              ? <SessionGraph sessionId={selected} />
              : <div className="h-full flex items-center justify-center text-sm text-zinc-500">
                  Select a session to view its attack trace.
                </div>}
          </CardContent>
        </Card>
      </section>

      <footer className="mt-8 text-xs text-zinc-500">
        AdvBench harmful_behaviors · attacker = Mixtral-8x22B-Instruct via OpenRouter ·
        target/judge = GPT-4o · detectors = PromptGuard / Llama-Guard-3 / keyword.
      </footer>
    </div>
  );
}

function StatTile({
  label, value, tone = "muted",
}: { label: string; value: string; tone?: "muted" | "danger" | "warning" | "success" }) {
  const toneClass: Record<string, string> = {
    muted:   "border-zinc-800 bg-zinc-950/50",
    danger:  "border-rose-900/60 bg-rose-950/30",
    warning: "border-amber-900/60 bg-amber-950/20",
    success: "border-emerald-900/60 bg-emerald-950/20",
  };
  const valueClass: Record<string, string> = {
    muted:   "text-zinc-100",
    danger:  "text-rose-200",
    warning: "text-amber-200",
    success: "text-emerald-200",
  };
  return (
    <div className={`rounded-lg border px-4 py-3 ${toneClass[tone]}`}>
      <div className="text-[11px] uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={`text-xl font-semibold mt-1 ${valueClass[tone]}`}>{value}</div>
    </div>
  );
}
