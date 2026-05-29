import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Background, Controls, MiniMap, Node, Edge, MarkerType } from "reactflow";
import { API } from "@/lib/utils";

type Round = {
  round: number;
  parent_round: number | null;
  candidate_prompt: string;
  detector_decision: "allow" | "block";
  detector_score: number | null;
  target_response: string;
  judge_score: number;
  success: boolean;
  extra?: { improvement?: string; depth?: number };
};

type Detail = { session_id: string; rounds: Round[] };

function nodeColor(r: Round): { bg: string; border: string } {
  if (r.detector_decision === "block") return { bg: "#3f1d1d", border: "#dc2626" };
  if (r.success) return { bg: "#7c2d12", border: "#f97316" };
  if (r.judge_score >= 7) return { bg: "#78350f", border: "#f59e0b" };
  if (r.judge_score >= 4) return { bg: "#365314", border: "#84cc16" };
  return { bg: "#1f2937", border: "#475569" };
}

export function SessionGraph({ sessionId }: { sessionId: string }) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [hoverRound, setHoverRound] = useState<Round | null>(null);

  useEffect(() => {
    fetch(`${API}/sessions/${sessionId}`).then(r => r.json()).then(setDetail);
  }, [sessionId]);

  const { nodes, edges } = useMemo(() => {
    if (!detail) return { nodes: [] as Node[], edges: [] as Edge[] };
    // Layered layout: x by depth/round, y by sibling index.
    const childrenByParent: Record<string, Round[]> = {};
    for (const r of detail.rounds) {
      const k = String(r.parent_round ?? "root");
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
        const ownY = sub > y ? (y + sub - 90) / 2 : y;
        xByRound[k.round] = depth * 320;
        yByRound[k.round] = ownY;
        y = sub + 100;
      }
      return Math.max(y, yStart + 100);
    }
    assign("root", 0, 0);

    const nodes: Node[] = detail.rounds.map(r => {
      const c = nodeColor(r);
      return {
        id: String(r.round),
        position: { x: xByRound[r.round] ?? 0, y: yByRound[r.round] ?? 0 },
        data: {
          label: (
            <div className="text-[11px] leading-tight">
              <div className="font-semibold mb-1">round {r.round}</div>
              <div>judge: <span className="font-mono">{r.judge_score}/10</span></div>
              <div>det: <span className="font-mono">{r.detector_decision}</span></div>
              {r.success && <div className="text-orange-300">JAILBROKEN</div>}
            </div>
          ),
        },
        style: {
          background: c.bg, color: "#fafafa",
          border: `1px solid ${c.border}`, borderRadius: 12,
          width: 180, padding: 8,
        },
      };
    });

    const edges: Edge[] = detail.rounds
      .filter(r => r.parent_round != null)
      .map(r => ({
        id: `e${r.parent_round}-${r.round}`,
        source: String(r.parent_round),
        target: String(r.round),
        animated: r.success,
        style: { stroke: "#71717a" },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#71717a" },
      }));
    return { nodes, edges };
  }, [detail]);

  return (
    <div className="h-full flex">
      <div className="flex-1 border-r border-zinc-800">
        <ReactFlow nodes={nodes} edges={edges} fitView
          onNodeMouseEnter={(_, n) => {
            const r = detail?.rounds.find(x => String(x.round) === n.id);
            if (r) setHoverRound(r);
          }}>
          <Background color="#27272a" gap={20} />
          <MiniMap nodeStrokeWidth={2} maskColor="rgba(0,0,0,0.5)" />
          <Controls />
        </ReactFlow>
      </div>
      <div className="w-[360px] overflow-auto p-4 text-xs space-y-3">
        {hoverRound ? (
          <>
            <div><div className="text-zinc-400">round</div>
              <div className="font-mono">{hoverRound.round}</div></div>
            <div><div className="text-zinc-400">judge score</div>
              <div className="font-mono">{hoverRound.judge_score}/10</div></div>
            <div><div className="text-zinc-400">detector</div>
              <div className="font-mono">
                {hoverRound.detector_decision} ({hoverRound.detector_score?.toFixed(2) ?? "-"})
              </div></div>
            <div><div className="text-zinc-400">candidate prompt</div>
              <pre className="bg-zinc-900 p-2 rounded whitespace-pre-wrap">{hoverRound.candidate_prompt}</pre></div>
            <div><div className="text-zinc-400">target response</div>
              <pre className="bg-zinc-900 p-2 rounded whitespace-pre-wrap">{hoverRound.target_response}</pre></div>
            {hoverRound.extra?.improvement && (
              <div><div className="text-zinc-400">attacker reasoning</div>
                <pre className="bg-zinc-900 p-2 rounded whitespace-pre-wrap">{hoverRound.extra.improvement}</pre></div>
            )}
          </>
        ) : <p className="text-zinc-500">Hover a node to inspect its round.</p>}
      </div>
    </div>
  );
}
