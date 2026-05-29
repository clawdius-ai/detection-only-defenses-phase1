"""PromptGuard detector.

Loads the public ``meta-llama/Llama-Prompt-Guard-2-86M`` classifier (or the
older ``meta-llama/Prompt-Guard-86M``) via the HuggingFace ``transformers``
pipeline. The model returns labels in {BENIGN, INJECTION, JAILBREAK}. A
prompt is blocked when the model returns INJECTION or JAILBREAK with a
probability above ``threshold``.
"""
from __future__ import annotations

from typing import Optional

from .base import DetectorDecision


class PromptGuardDetector:
    name = "promptguard"

    def __init__(self, model_name: str = "meta-llama/Prompt-Guard-86M",
                 threshold: float = 0.5, device: Optional[str] = None):
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.threshold = threshold
        self.id2label = self.model.config.id2label

    def evaluate(self, prompt: str) -> DetectorDecision:
        with self.torch.no_grad():
            enc = self.tokenizer(prompt or "", return_tensors="pt",
                                  truncation=True, max_length=512)
            enc = {k: v.to(self.device) for k, v in enc.items()}
            logits = self.model(**enc).logits[0]
            probs = self.torch.softmax(logits, dim=-1).cpu().numpy().tolist()
        # Find probability mass on non-benign classes.
        non_benign_prob = 0.0
        top_label = "BENIGN"
        top_prob = 0.0
        for idx, prob in enumerate(probs):
            label = self.id2label.get(idx, str(idx)).upper()
            if prob > top_prob:
                top_prob = float(prob)
                top_label = label
            if "BENIGN" not in label:
                non_benign_prob += float(prob)
        blocked = non_benign_prob >= self.threshold
        return DetectorDecision(
            blocked=blocked,
            score=non_benign_prob,
            label=top_label.lower(),
        )
