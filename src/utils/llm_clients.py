"""LLM API clients for OpenAI (target/judge) and OpenRouter (attacker)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Dict, Optional

import httpx
from openai import OpenAI


def _read_dotenv_var(name: str) -> Optional[str]:
    """Read a variable from a project-local .env without trusting environ.

    Managed sandbox environments may inject `OPENAI_API_KEY` that points at
    a zero-credit project; the .env shipped with the repo is the source of
    truth for credentials.
    """
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(here, ".env")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
    except OSError:
        return None
    return None


@dataclass
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class OpenAIChatClient:
    """Wrapper around OpenAI chat completions used for target and judge."""

    def __init__(self, model: str, api_key: Optional[str] = None,
                 temperature: float = 0.0, max_tokens: int = 512):
        # Priority: explicit arg > .env file > env var. This order matters
        # because managed sandbox environments may inject an OPENAI_API_KEY
        # env var that points at a different (zero-credit) project.
        if not api_key:
            api_key = _read_dotenv_var("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: List[ChatMessage], temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        for attempt in range(4):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[m.to_dict() for m in messages],
                    temperature=self.temperature if temperature is None else temperature,
                    max_tokens=self.max_tokens if max_tokens is None else max_tokens,
                )
                return resp.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        return ""


class OpenRouterChatClient:
    """Wrapper around OpenRouter chat completions used for the attacker LLM."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model: str, api_key: Optional[str] = None,
                 temperature: float = 1.0, max_tokens: int = 1024,
                 referer: str = "https://github.com/clawdius-ai",
                 title: str = "Detection-Only Defenses Phase 1"):
        if not api_key:
            api_key = _read_dotenv_var("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": referer,
            "X-Title": title,
            "Content-Type": "application/json",
        }

    def chat(self, messages: List[ChatMessage], temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> str:
        payload = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        for attempt in range(4):
            try:
                with httpx.Client(timeout=120.0) as client:
                    resp = client.post(self.BASE_URL, headers=self.headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"] or ""
            except Exception:  # noqa: BLE001
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        return ""
