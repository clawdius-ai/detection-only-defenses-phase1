"""Generate the Phase 1 presentation as a PowerPoint (.pptx) file.

The deck mirrors the structure of report/phase1_report.md and is uploaded
to Google Slides by opening it through Google Drive -> Open with Google
Slides.

Output: report/phase1_slides.pptx
"""
from __future__ import annotations

import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


OUTPUT = "report/phase1_slides.pptx"


SLIDES = [
    {
        "title": "Detection-Only Defenses for LLMs",
        "subtitle": ("Phase 1 — Adaptive Jailbreak Attacks (PAIR, TAP) "
                     "vs. Detector-Only Defenses on AdvBench"),
        "kind": "title",
    },
    {
        "title": "1. Problem",
        "bullets": [
            "LLMs are aligned to refuse harmful or restricted content.",
            "Adaptive jailbreak attacks iteratively refine prompts based on "
            "the target's outputs.",
            "Detector-only defenses act only on routing (allow / block / refuse); "
            "they do not modify the prompt or intervene inside generation.",
            "Goal: evaluate the limits of detector-only defenses against "
            "adaptive attacks.",
        ],
    },
    {
        "title": "2. Experimental Setup",
        "bullets": [
            "Dataset: AdvBench harmful_behaviors.csv (first 100; N=20 for "
            "cost-bounded first pass).",
            "Attacker: Mixtral-8x22B-Instruct via OpenRouter "
            "(Vicuna-13B no longer served; open-weight substitute).",
            "Target: GPT-4o (gpt-4o-2024-08-06) via OpenAI.",
            "Judge: GPT-4o, 1–10 rubric, success threshold = 10.",
            "Budgets: B ∈ {5, 10} target queries per behavior.",
        ],
    },
    {
        "title": "3. Adaptive Attack Baselines",
        "bullets": [
            "PAIR (Chao et al., 2023): single attacker stream, JSON output "
            "{improvement, prompt}. B caps the refinement rounds.",
            "TAP (Mehrotra et al., 2024): tree search with branching b, width w.",
            "Pre-target pruning via on-topic check (off-topic candidates discarded).",
            "Post-target pruning keeps top-w leaves by judge score.",
            "B caps the total number of target queries.",
        ],
    },
    {
        "title": "4. Detector-Only Defense Baselines",
        "bullets": [
            "none — control baseline (no defense).",
            "keyword — conservative AdvBench-derived blocklist (lower bound).",
            "PromptGuard — meta-llama/Prompt-Guard-86M (HuggingFace).",
            "Llama-Guard-3 — meta-llama/llama-guard-3-8b via OpenRouter "
            "(stronger competitive baseline).",
            "Blocked prompts never reach the target; their judge score is 1.",
        ],
    },
    {
        "title": "5. Pipeline",
        "bullets": [
            "AdvBench behavior → Attacker → candidate adversarial prompt.",
            "Candidate → Detector → allow / block decision.",
            "If allowed: candidate → Target LLM → response.",
            "(Goal, candidate, response) → Judge LLM → integer score 1–10.",
            "Score = 10 → session marked jailbroken; otherwise feedback loops "
            "into the attacker for the next round.",
            "PAIR runs this loop as a linear chain; TAP runs it as a tree.",
        ],
    },
    {
        "title": "6. Trace Schema (per round)",
        "bullets": [
            "session_id, attack, defense, budget, advbench_index, goal.",
            "round, parent_round (linear for PAIR, tree edges for TAP).",
            "candidate_prompt, detector_decision, detector_score.",
            "target_response, judge_score, success flag, attacker reasoning.",
            "Stored as append-only JSONL → full reproducibility.",
        ],
    },
    {
        "title": "7. Metrics",
        "bullets": [
            "ASR — Attack Success Rate: fraction of behaviors jailbroken "
            "(judge score 10 in at least one round).",
            "Block Rate — fraction of (session × round) prompts blocked by "
            "the detector.",
            "Mean Max Judge Score — mean over behaviors of the maximum judge "
            "score observed per session.",
            "Average Queries per Behavior — mean target queries used (early "
            "termination allowed on success).",
        ],
    },
    {
        "title": "8. Deliverables (this repository)",
        "bullets": [
            "github.com/clawdius-ai/detection-only-defenses-phase1",
            "src/ — PAIR + TAP + detectors + GPT-4o target/judge.",
            "configs/ — 10 YAML cells covering the full experimental grid.",
            "scripts/ — run_experiment.py · run_all.sh · aggregate_results.py.",
            "backend/ — FastAPI trace API.",
            "frontend/ — React + Vite + Tailwind + ReactFlow dashboard.",
            "n8n/ — orchestration workflow (Vicuna-Mixtral / Llama-Guard / "
            "GPT-4o target+judge).",
            "report/ — Phase 1 markdown report.",
        ],
    },
    {
        "title": "9. Interactive Dashboard",
        "bullets": [
            "ASR bar chart per defense × attack × budget.",
            "Session list with attack / defense filters.",
            "Round-level attack trace graph:",
            "   PAIR → linear chain.",
            "   TAP  → branching tree (pre/post-target pruning visible).",
            "Node color encodes judge score and detector decision.",
            "Side panel surfaces candidate prompt, target response, attacker "
            "reasoning per round.",
        ],
    },
    {
        "title": "10. Limitations & Phase 2 Outlook",
        "bullets": [
            "Vicuna-13B substituted with Mixtral-8x22B-Instruct (deviation "
            "documented in report).",
            "Phase 1 run on N=20 prompts for cost; pipeline scales to N=100 "
            "without code changes.",
            "StrongREJECT and JBB-Behaviors loaders planned for Phase 2.",
            "Phase 2 (Mitacs plan alignment): build interaction graphs from "
            "session traces, apply graph-based anomaly detection, ship visual "
            "analytics dashboard.",
        ],
    },
    {
        "title": "References",
        "bullets": [
            "Chao et al. Jailbreaking Black Box Large Language Models in "
            "Twenty Queries. arXiv:2310.08419 (PAIR).",
            "Mehrotra et al. Tree of Attacks: Jailbreaking Black-Box LLMs "
            "Automatically. arXiv:2312.02119 (TAP).",
            "Zou et al. Universal and Transferable Adversarial Attacks on "
            "Aligned Language Models. arXiv:2307.15043 (AdvBench).",
            "Inan et al. Llama Guard: LLM-based Input-Output Safeguard for "
            "Human-AI Conversations. arXiv:2312.06674.",
        ],
    },
]


def _set_title(slide, text):
    slide.shapes.title.text = text
    for p in slide.shapes.title.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(28)
            r.font.bold = True
            r.font.color.rgb = RGBColor(0xFA, 0xFA, 0xFA)


def _add_bullets(slide, bullets):
    body = slide.placeholders[1]
    tf = body.text_frame
    tf.word_wrap = True
    tf.text = bullets[0]
    for r in tf.paragraphs[0].runs:
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(0xE5, 0xE7, 0xEB)
    for line in bullets[1:]:
        p = tf.add_paragraph()
        p.text = line
        for r in p.runs:
            r.font.size = Pt(16)
            r.font.color.rgb = RGBColor(0xE5, 0xE7, 0xEB)


def main():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    for sl in SLIDES:
        if sl.get("kind") == "title":
            layout = prs.slide_layouts[0]
        else:
            layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(layout)

        # Dark background
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0x0B, 0x0B, 0x10)

        _set_title(slide, sl["title"])
        if sl.get("kind") == "title":
            # Use subtitle placeholder.
            sub = slide.placeholders[1]
            sub.text = sl["subtitle"]
            for p in sub.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(18)
                    r.font.color.rgb = RGBColor(0xA1, 0xA1, 0xAA)
        else:
            _add_bullets(slide, sl["bullets"])

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    prs.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
