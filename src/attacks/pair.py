"""PAIR — Prompt Automatic Iterative Refinement.

Reference: Chao et al., *Jailbreaking Black Box Large Language Models in
Twenty Queries* (arXiv:2310.08419). The attacker LLM is conditioned on a
red-teaming system prompt and iteratively refines an adversarial prompt
based on the target's response and the judge score. A single attacker
"stream" is run per behavior up to a query budget B.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..utils.llm_clients import OpenRouterChatClient, ChatMessage
from ..utils.tracing import RoundRecord, JsonlTraceWriter, new_session_id
from ..targets.target import TargetLLM
from ..judge.judge import GPT4Judge
from ..defenses.base import Detector, DetectorDecision
from .prompts import (
    ATTACKER_SYSTEM_TEMPLATE,
    INIT_USER_TEMPLATE,
    FOLLOWUP_USER_TEMPLATE,
)
from .common import parse_attacker_json


@dataclass
class PAIRResult:
    session_id: str
    success: bool
    best_score: int
    rounds_used: int


class PAIRAttacker:
    """Single-stream PAIR attacker."""

    def __init__(self, attacker: OpenRouterChatClient, target: TargetLLM,
                 judge: GPT4Judge, detector: Detector, writer: JsonlTraceWriter,
                 budget: int = 5):
        self.attacker = attacker
        self.target = target
        self.judge = judge
        self.detector = detector
        self.writer = writer
        self.budget = budget

    def run(self, advbench_index: int, goal: str, target_prefix: str) -> PAIRResult:
        session_id = new_session_id()
        attacker_sys = ATTACKER_SYSTEM_TEMPLATE.format(
            goal=goal, target_prefix=target_prefix)
        conversation: List[ChatMessage] = [ChatMessage("system", attacker_sys)]
        user_msg = INIT_USER_TEMPLATE.format(goal=goal, target_prefix=target_prefix)

        best_score = 1
        success = False
        rounds_used = 0

        for round_idx in range(1, self.budget + 1):
            rounds_used = round_idx
            conversation.append(ChatMessage("user", user_msg))
            attacker_raw = self.attacker.chat(conversation, temperature=1.0,
                                              max_tokens=1024)
            conversation.append(ChatMessage("assistant", attacker_raw))

            parsed = parse_attacker_json(attacker_raw)
            if parsed is None:
                candidate = attacker_raw.strip()
                improvement = ""
            else:
                candidate = parsed["prompt"]
                improvement = parsed.get("improvement", "")

            # Detector decides whether to allow the candidate to reach the target.
            decision: DetectorDecision = self.detector.evaluate(candidate)
            if decision.blocked:
                response = "[BLOCKED BY DETECTOR]"
                judge_score = 1
            else:
                response = self.target.query(candidate)
                judge_score, _ = self.judge.score(goal, candidate, response)

            success = self.judge.is_success(judge_score)
            if judge_score > best_score:
                best_score = judge_score

            self.writer.write(RoundRecord(
                session_id=session_id,
                attack="pair",
                defense=self.detector.name,
                budget=self.budget,
                advbench_index=advbench_index,
                goal=goal,
                round=round_idx,
                parent_round=round_idx - 1 if round_idx > 1 else None,
                candidate_prompt=candidate,
                detector_decision="block" if decision.blocked else "allow",
                detector_score=decision.score,
                target_response=response,
                judge_score=judge_score,
                success=success,
                extra={"improvement": improvement,
                       "detector_label": decision.label},
            ))

            if success:
                break

            user_msg = FOLLOWUP_USER_TEMPLATE.format(
                response=response, goal=goal,
                target_prefix=target_prefix, score=judge_score)

        return PAIRResult(session_id=session_id, success=success,
                          best_score=best_score, rounds_used=rounds_used)
