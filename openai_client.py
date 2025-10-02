"""OpenAI API helper utilities."""
from __future__ import annotations

import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

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
        messages = [
            {
                "role": "system",
                "content": system_prompt or "You are a helpful assistant that summarizes text concisely.",
            },
            {
                "role": "user",
                "content": text,
            },
        ]

        try:
            if hasattr(self._client, "responses"):
                response = self._client.responses.create(
                    model=model,
                    input=[
                        {
                            "role": item["role"],
                            "content": item["content"],
                        }
                        for item in messages
                    ],
                    max_output_tokens=200,
                )
                for item in response.output:
                    if item.type == "message":
                        segments = item.message.get("content", [])
                        return "".join(segment.get("text", "") for segment in segments)
                return ""

            chat_client = getattr(self._client, "chat", None)
            if chat_client and hasattr(chat_client, "completions"):
                chat_model = model if model and not model.startswith("gpt-4o") else "gpt-3.5-turbo"
                completion = chat_client.completions.create(
                    model=chat_model,
                    messages=messages,
                    max_tokens=200,
                )
                choice = completion.choices[0]
                content = getattr(choice.message, "content", "") if hasattr(choice, "message") else getattr(choice, "text", "")
                return content.strip()

            import openai as openai_module  # type: ignore

            if hasattr(openai_module, "ChatCompletion"):
                chat_model = model if model and not model.startswith("gpt-4o") else "gpt-3.5-turbo"
                completion = openai_module.ChatCompletion.create(
                    model=chat_model,
                    messages=messages,
                    max_tokens=200,
                )
                return completion["choices"][0]["message"]["content"].strip()

            raise RuntimeError("OpenAI client does not expose a supported responses/chat API.")
        except APIError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc}") from exc
