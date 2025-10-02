"""Example workflow combining YouTube and OpenAI helpers."""
from __future__ import annotations

from typing import Optional

from openai_client import OpenAIClient
from youtube_client import YouTubeClient


def summarize_top_youtube_video(query: str, *, include_description: bool = True) -> Optional[str]:
    """Search YouTube and summarize the first result using OpenAI."""
    youtube = YouTubeClient()
    openai_client = OpenAIClient()

    videos = youtube.search_videos(query, max_results=1)
    if not videos:
        return None

    top = videos[0]
    description = top.description if include_description else ""
    prompt = (
        f"Video title: {top.title}\n"
        f"Channel: {top.channel}\n"
        f"Published at: {top.published_at}\n"
        f"Description:\n{description}\n\n"
        "Summarize the key topic and suggest why it might be useful for vocal analysis."
    )
    return openai_client.summarize_text(prompt)
