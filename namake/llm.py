"""Model backends. The real one runs Gemma locally through llama.cpp; tests use FakeLLM."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_MODEL = os.environ.get(
    "NAMAKE_MODEL",
    str(Path(__file__).resolve().parent.parent / "models" / "gemma-3-1b-it-Q4_K_M.gguf"),
)


class LocalLLM:
    """Gemma 3 1B (GGUF) on CPU. No network calls, nothing leaves the machine."""

    def __init__(self, model_path: str = DEFAULT_MODEL, threads: int | None = None):
        from llama_cpp import Llama  # imported lazily so tests don't need it

        if not Path(model_path).exists():
            raise SystemExit(
                f"Model not found at {model_path}.\n"
                "Download it once (about 800 MB):\n"
                "  curl -L -o models/gemma-3-1b-it-Q4_K_M.gguf "
                "https://huggingface.co/unsloth/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf\n"
                "or point NAMAKE_MODEL at another GGUF file."
            )
        self._llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=threads or max(1, (os.cpu_count() or 4) - 1),
            verbose=False,
        )

    def chat(self, messages: list[dict], max_tokens: int = 350, temperature: float = 0.2) -> str:
        out = self._llm.create_chat_completion(
            messages=messages, temperature=temperature, max_tokens=max_tokens
        )
        return out["choices"][0]["message"]["content"].strip()


class FakeLLM:
    """Returns canned replies in order. Records what it was asked."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict], max_tokens: int = 350, temperature: float = 0.2) -> str:
        self.calls.append(messages)
        return self.replies.pop(0) if self.replies else ""
