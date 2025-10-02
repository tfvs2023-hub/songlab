"""YouTube Data API helper utilities."""
from __future__ import annotations

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Optional

load_dotenv()

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as exc:  # pragma: no cover - handled via runtime checks
    raise ImportError(
        "google-api-python-client is required. Install with 'pip install google-api-python-client'."
    ) from exc


@dataclass
class YouTubeVideo:
    """Simple container for video metadata."""

    video_id: str
    title: str
    channel: str
    description: str
    published_at: str


class YouTubeClient:
    """Minimal YouTube Data API wrapper for search operations."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key not provided. Set YOUTUBE_API_KEY environment variable.")
        self._service = None

    @property
    def service(self):
        if self._service is None:
            self._service = build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
        return self._service

    def search_videos(self, query: str, max_results: int = 5) -> List[YouTubeVideo]:
        """Search for videos matching the query string."""
        try:
            request = self.service.search().list(
                part="id,snippet",
                q=query,
                type="video",
                maxResults=max(1, min(max_results, 50)),
            )
            response = request.execute()
        except HttpError as exc:
            raise RuntimeError(f"YouTube API request failed: {exc}") from exc

        results: List[YouTubeVideo] = []
        for item in response.get("items", []):
            video_id = item["id"].get("videoId")
            snippet = item.get("snippet", {})
            results.append(
                YouTubeVideo(
                    video_id=video_id or "",
                    title=snippet.get("title", ""),
                    channel=snippet.get("channelTitle", ""),
                    description=snippet.get("description", ""),
                    published_at=snippet.get("publishedAt", ""),
                )
            )
        return results
