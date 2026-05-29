import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, MarkerType } from "reactflow";
import { API } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type Round = {
  round: number;
  parent_round: number | null;
  candidate_prompt: string;
  detector_decision: "allow" | "block";
  detector_score: number | null;
  target_response: string;
  judge_score: number;
  success: boolean;
  extra?: { improvement?: string; depth?: number; on_topic?: boolean; detector_label?: string };
};

type Detail = { session_id: string; rounds: Round[] };

function nodeColor(r: Round): { bg: string; border: string; chip: string; label: string } {
  if (r.detector_decision === "block") {
    return { bg: "#2a1215", border: "#ef4444", chip: "#ef4444", label: "blocked" };
  }
  if (r.success) {
    return { bg: "#3b1d0a", border: "#f97316", chip: "#f97316", label: "success" };
  }
  if (r.judge_score >= 7) {
    return { bg: "#332508", border: "#f59e0b", chip: "#f59e0b", label: "high risk" };
  }
  if (r.judge_score >= 4) {
    return { bg: "#14240f", border: "#84cc16", chip: "#84cc16", label: "partial" };
  }
  return { bg: "#111827", border: "#64748b", chip: "#64748b", label: "low" };
}

function scoreBarColor(score: number): string {
  if (score >= 10) return "#f97316";
  if (score >= 7) return "#f59e0b";
  if (score >= 4) return "#84cc16";
  return "#64748b";
}

function shortText(text: string, max = 86): string {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max - 1)}...` : text;
}

export function SessionGraph({ sessionId }: { sessionId: string }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [selectedRound, setSelectedRound] = useState<Round | null>(null);

  useEffect(() => {
    setDetail(null);
    setSelectedRound(null);
    fetch(`${API}/sessions/${sessionId}`).then(r => r.json()).then((d: Detail) => {
      const rounds = [...(d.rounds || [])].sort((a, b) => a.round - b.round);
      setDetail({ ...d, rounds });
      setSelectedRound(rounds[0] || null);
    });
  }, [sessionId]);

  const sessionKind = detail?.rounds[0]?.parent_round === 1 ? "tap" : detail?.rounds.length
    ? detail.rounds.some(r => r.parent_round != null && r.parent_round !== r.round - 1) ? "tap" : "pair"
    : "session";

  const { nodes, edges } = useMemo(() => {
    if (!detail) return { nodes: [] as Node[], edges: [] as Edge[] };
    const roundSet = new Set(detail.rounds.map(r => r.round));
    const childrenByParent: Record<string, Round[]> = {};
    for (const r of detail.rounds) {
      const isRoot = r.parent_round == null || !roundSet.has(r.parent_round);
      const k = isRoot ? "root" : String(r.parent_round);
      (childrenByParent[k] ||= []).push(r);
    }
    const xByRound: Record<number, number> = {};
    const yByRound: Record<number, number> = {};
    const depthOfRound: Record<number, number> = {};

    function assign(parentKey: string, depth: number, yStart: number): number {
      const kids = childrenByParent[parentKey] || [];
      let y = yStart;
      for (const k of kids) {
        depthOfRound[k.round] = depth;
        const sub = assign(String(k.round), depth + 1, y);
        const ownY = sub > y ? (y + sub - 116) / 2 : y;
        xByRound[k.round] = depth * 290;
        yByRound[k.round] = ownY;
        y = sub + 132;
      }
      return Math.max(y, yStart + 132);
    }
    assign("root", 0, 0);

    const nodes: Node[] = detail.rounds.map(r => {
      const c = nodeColor(r);
      const selected = selectedRound?.round === r.round;
      return {
        id: String(r.round),
        position: { x: xByRound[r.round] ?? 0, y: yByRound[r.round] ?? 0 },
        data: {
          label: (
            <div className="text-[11px] leading-tight">
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="font-semibold text-zinc-50">round {r.round}</span>
                <span className="rounded px-1.5 py-0.5 text-[10px] uppercase tracking-wide"
                  style={{ background: `${c.chip}22`, color: c.chip }}>
                  {c.label}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-zinc-300">
                <div>
                  <div className="text-[9px] uppercase text-zinc-500">judge</div>
                  <div className="font-mono text-sm text-zinc-50">{r.judge_score}/10</div>
                </div>
                <div>
                  <div className="text-[9px] uppercase text-zinc-500">detector</div>
                  <div className="font-mono text-sm text-zinc-50">{r.detector_decision}</div>
                </div>
              </div>
              <div className="mt-2 h-1.5 rounded bg-zinc-950 overflow-hidden">
                <div className="h-full rounded"
                  style={{
                    width: `${Math.max(8, r.judge_score * 10)}%`,
                    background: scoreBarColor(r.judge_score),
                  }} />
              </div>
              <div className="mt-2 text-[10px] text-zinc-400">
                {shortText(r.candidate_prompt, 72)}
              </div>
            </div>
          ),
        },
        style: {
          background: c.bg, color: "#fafafa",
          border: `${selected ? 2 : 1}px solid ${selected ? "#e5e7eb" : c.border}`,
          borderRadius: 8,
          boxShadow: selected ? "0 0 0 3px rgba(229,231,235,0.12)" : "none",
          width: 220, padding: 10,
        },
      };
    });

    const edges: Edge[] = detail.rounds
      .filter(r => r.parent_round != null && roundSet.has(r.parent_round))
      .map(r => ({
        id: `e${r.parent_round}-${r.round}`,
        source: String(r.parent_round),
        target: String(r.round),
        animated: r.success || r.judge_score >= 8,
        style: {
          stroke: r.success ? "#f97316" : r.detector_decision === "block" ? "#ef4444" : "#71717a",
          strokeWidth: r.success ? 2.5 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: r.success ? "#f97316" : r.detector_decision === "block" ? "#ef4444" : "#71717a",
        },
      }));
    return { nodes, edges };
  }, [detail, selectedRound]);

  const visibleRound = selectedRound || detail?.rounds[0] || null;

  return (
    <div className="h-full flex flex-col bg-zinc-950/30">
      <div className="min-h-0 flex-1 border-b border-zinc-800 relative">
        <div className="absolute left-4 top-4 z-10 flex flex-wrap items-center gap-2 rounded-md border border-zinc-800 bg-zinc-950/90 px-3 py-2 text-xs shadow">
          <Badge variant="muted">{sessionKind}</Badge>
          <span className="text-zinc-400">{detail?.rounds.length ?? 0} nodes</span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="h-2.5 w-2.5 rounded-sm bg-[#64748b]" /> low
          </span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="h-2.5 w-2.5 rounded-sm bg-[#84cc16]" /> partial
          </span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="h-2.5 w-2.5 rounded-sm bg-[#ef4444]" /> blocked
          </span>
          <span className="flex items-center gap-1 text-zinc-400">
            <span className="h-2.5 w-2.5 rounded-sm bg-[#f97316]" /> success
          </span>
        </div>
        <ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.22 }}
          minZoom={0.25}
          maxZoom={1.5}
          nodesDraggable={false}
          panOnScroll
          zoomOnScroll
          zoomOnPinch
          selectionOnDrag={false}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, n) => {
            const r = detail?.rounds.find(x => String(x.round) === n.id);
            if (r) setSelectedRound(r);
          }}>
          <Background color="#27272a" gap={20} />
          <MiniMap position="bottom-right" nodeStrokeWidth={2} maskColor="rgba(0,0,0,0.5)" />
          <Controls position="bottom-left" />
        </ReactFlow>
      </div>
      <div className="max-h-[260px] overflow-auto p-4 text-xs">
        {visibleRound ? (
          <>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-wide text-zinc-500">selected node</div>
                <div className="text-lg font-semibold text-zinc-50">Round {visibleRound.round}</div>
              </div>
              <Badge variant={visibleRound.success ? "danger" : visibleRound.detector_decision === "block" ? "warning" : "muted"}>
                {visibleRound.success ? "jailbroken" : visibleRound.detector_decision}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-3 md:grid-cols-4">
              <div className="rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
                <div className="text-zinc-500">Judge</div>
                <div className="font-mono text-xl text-zinc-50">{visibleRound.judge_score}/10</div>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
                <div className="text-zinc-500">Detector Score</div>
                <div className="font-mono text-xl text-zinc-50">
                  {visibleRound.detector_score?.toFixed(2) ?? "-"}
                </div>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
                <div className="text-zinc-500">Parent</div>
                <div className="font-mono text-xl text-zinc-50">
                  {visibleRound.parent_round ?? "root"}
                </div>
              </div>
              <div className="rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
                <div className="text-zinc-500">Label</div>
                <div className="font-mono text-sm text-zinc-50 truncate">
                  {visibleRound.extra?.detector_label ?? "-"}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
              <DetailBlock title="Candidate Prompt" text={visibleRound.candidate_prompt} />
              <DetailBlock title="Target Response" text={visibleRound.target_response} />
              <DetailBlock title="Attacker Reasoning" text={visibleRound.extra?.improvement || "-"} />
            </div>
            {visibleRound.extra?.depth != null && (
              <div className="mt-3 rounded-md border border-zinc-800 bg-zinc-900/70 p-3">
                <div className="text-zinc-500">TAP Metadata</div>
                <div className="mt-1 font-mono text-zinc-200">
                  depth={visibleRound.extra.depth} · on_topic={String(visibleRound.extra.on_topic ?? true)}
                </div>
              </div>
            )}
          </>
        ) : <p className="text-zinc-500">Select a session to inspect its rounds.</p>}
      </div>
    </div>
  );
}

function DetailBlock({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <div className="mb-1 text-zinc-500">{title}</div>
      <pre className="max-h-[140px] overflow-auto rounded-md border border-zinc-800 bg-zinc-950 p-3 whitespace-pre-wrap leading-relaxed text-zinc-200">
        {text}
      </pre>
    </div>
  );
}
