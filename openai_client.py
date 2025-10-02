"""OpenAI API helper utilities."""
from __future__ import annotations

import os
from typing import Optional

try:
    from openai import OpenAI
    from openai import APIError
except ImportError as exc:  # pragma: no cover
    raise ImportError("openai package is required. Install with 'pip install openai'.") from exc


class OpenAIClient:
    """Simple wrapper around OpenAI responses API."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        self._client = OpenAI(api_key=self.api_key)

    def summarize_text(self, text: str, *, model: str = "gpt-4o-mini", system_prompt: Optional[str] = None) -> str:
        """Generate a short summary for the provided text."""
        try:
            response = self._client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": system_prompt or "You are a helpful assistant that summarizes text concisely.",
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                max_output_tokens=200,
            )
        except APIError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc

        for item in response.output:
            if item.type == "message":
                segments = item.message.get("content", [])
                return "".join(segment.get("text", "") for segment in segments)
        return ""
