import logging
import os
import time
from typing import Dict, List, Optional, Tuple

try:
    from googleapiclient.discovery import build  # type: ignore
    from googleapiclient.errors import HttpError  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency
    build = None  # type: ignore
    HttpError = Exception  # type: ignore
    _GOOGLE_API_IMPORT_ERROR = exc
else:
    _GOOGLE_API_IMPORT_ERROR = None

logger = logging.getLogger(__name__)


class YouTubeService:
    """YouTube 추천 서비스"""

    DEFAULT_CACHE_TTL = 900  # seconds
    # Use an inline SVG data URI as a fallback thumbnail to avoid external DNS/image fetch
    FALLBACK_THUMBNAIL = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' width='480' height='360'>"
        "<rect width='100%' height='100%' fill='%23dddddd'/>"
        "<text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle'"
        " font-family='Arial, Helvetica, sans-serif' font-size='20' fill='%23666'>YouTube Search</text>"
        "</svg>"
    )
    KEYWORD_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
        "brightness": {
            "very_low": ["어두운 음색 밝히기", "포먼트 조절 보컬 레슨"],
            "low": ["음색 밝기 트레이닝", "밝은 톤 만들기"],
            "neutral": ["음색 밸런스 연습", "톤 컬러 컨트롤"],
            "high": ["밝은 음색 컨트롤", "하이라이트 톤 안정화"],
            "very_high": ["밝은 톤 안정화", "고음 밝기 제어"],
        },
        "thickness": {
            "very_low": ["체스트 보이스 강화", "저음 공명 확장"],
            "low": ["두께감 보컬 트레이닝", "성대 접촉 강화 연습"],
            "neutral": ["음색 밸런스 훈련", "믹스 보이스 빌드업"],
            "high": ["두꺼운 음색 정리", "고음에서의 벨팅 조절"],
            "very_high": ["두꺼운 음색 컨트롤", "성대 압력 완화"],
        },
        "loudness": {
            "very_low": ["복식호흡 발성", "소리 키우기 트레이닝"],
            "low": ["호흡 지지 강화", "발성 파워 업"],
            "neutral": ["다이내믹 컨트롤 연습", "볼륨 밸런스 트레이닝"],
            "high": ["파워 제어 연습", "다이내믹 유지 팁"],
            "very_high": ["음압 조절 훈련", "발성 파워 안정화"],
        },
        "clarity": {
            "very_low": ["딕션 강화 연습", "발음 명료도 훈련"],
            "low": ["또렷한 발음 만들기", "성대 떨림 안정화"],
            "neutral": ["발음과 톤 밸런스", "발성 기본기 정리"],
            "high": ["발음 디테일 살리기", "호흡과 딕션 조화"],
            "very_high": ["선명도 유지 노하우", "발음 과다 제어법"],
        },
        "default": {
            "neutral": ["보컬 훈련", "발성 연습"],
        },
    }

    def __init__(
        self, api_key: Optional[str] = None, cache_ttl: Optional[int] = None
    ) -> None:
        self.api_key = (api_key or os.getenv("YOUTUBE_API_KEY", "")).strip()

        if cache_ttl is not None:
            self.cache_ttl = cache_ttl
        else:
            ttl_env = os.getenv("YOUTUBE_CACHE_TTL")
            try:
                self.cache_ttl = int(ttl_env) if ttl_env else self.DEFAULT_CACHE_TTL
            except (TypeError, ValueError):
                self.cache_ttl = self.DEFAULT_CACHE_TTL
                if ttl_env:
                    logger.warning(
                        "Invalid YOUTUBE_CACHE_TTL value '%s'. Using default %s seconds.",
                        ttl_env,
                        self.DEFAULT_CACHE_TTL,
                    )

        self._youtube = None
        self._cache: Dict[str, Tuple[float, List[Dict]]] = {}
        self._last_error: Optional[str] = None

        if not self.api_key:
            logger.warning(
                "YouTube API key not configured. Recommendations will fall back to search URLs."
            )
        if _GOOGLE_API_IMPORT_ERROR is not None:
            logger.warning(
                "googleapiclient is not available: %s", _GOOGLE_API_IMPORT_ERROR
            )

    def _ensure_client(self):
        if self._youtube is not None:
            return self._youtube

        if build is None:
            raise RuntimeError(
                f"googleapiclient is not available: {_GOOGLE_API_IMPORT_ERROR}"
            )
        if not self.api_key:
            raise RuntimeError("YouTube API key is not configured.")

        try:
            self._youtube = build("youtube", "v3", developerKey=self.api_key)
            self._last_error = None
            return self._youtube
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            logger.error("Failed to initialize YouTube client: %s", exc)
            raise

    def _build_fallback(self, keyword: str, reason: Optional[str] = None) -> Dict:
        query = keyword.replace(" ", "+")
        description = "YouTube에서 직접 검색해보세요"
        if reason:
            description = f"{description} ({reason})"
        return {
            "videoId": None,
            "title": f"{keyword} 검색하기",
            "description": description,
            "thumbnail": self.FALLBACK_THUMBNAIL,
            "channelTitle": "YouTube",
            "url": f"https://www.youtube.com/results?search_query={query}",
        }

    @property
    def youtube(self):
        """Legacy accessor kept for backward compatibility."""
        try:
            return self._ensure_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube client unavailable via legacy accessor: %s", exc)
            return None

    @staticmethod
    def _score_band(score: float) -> str:
        if score <= -60:
            return "very_low"
        if score <= -25:
            return "low"
        if score >= 60:
            return "very_high"
        if score >= 25:
            return "high"
        return "neutral"

    def _keywords_for_axis(self, axis: str, score: float) -> List[str]:
        templates = self.KEYWORD_TEMPLATES.get(axis, self.KEYWORD_TEMPLATES["default"])
        band = self._score_band(score)
        keywords = (
            templates.get(band)
            or templates.get("neutral")
            or self.KEYWORD_TEMPLATES["default"]["neutral"]
        )
        return keywords

    def search_videos(self, keyword: str, max_results: int = 3) -> List[Dict]:
        keyword = (keyword or "").strip()
        if not keyword:
            return []

        cache_key = f"{keyword}:{max_results}"
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < self.cache_ttl:
            return cached[1]

        try:
            youtube = self._ensure_client()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "YouTube client unavailable for keyword '%s': %s", keyword, exc
            )
            return [self._build_fallback(keyword, reason=str(exc))]

        try:
            search_response = (
                youtube.search()
                .list(
                    q=f"{keyword} 보컬 레슨",
                    part="id,snippet",
                    maxResults=max_results,
                    type="video",
                    relevanceLanguage="ko",
                    regionCode="KR",
                    safeSearch="moderate",
                )
                .execute()
            )
        except HttpError as exc:  # type: ignore[misc]
            logger.warning("YouTube API HttpError for '%s': %s", keyword, exc)
            return [self._build_fallback(keyword, reason="API 호출 오류")]
        except Exception as exc:  # noqa: BLE001
            logger.warning("YouTube API error for '%s': %s", keyword, exc)
            return [self._build_fallback(keyword, reason=str(exc))]

        videos: List[Dict] = []
        for item in search_response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue

            snippet = item.get("snippet", {})
            thumbnails = snippet.get("thumbnails", {})
            thumbnail = thumbnails.get("high", {}).get("url") or thumbnails.get(
                "default", {}
            ).get("url")

            videos.append(
                {
                    "videoId": video_id,
                    "title": snippet.get("title"),
                    "description": (snippet.get("description") or "")[:200],
                    "thumbnail": thumbnail or self.FALLBACK_THUMBNAIL,
                    "channelTitle": snippet.get("channelTitle"),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                }
            )

        if videos:
            self._cache[cache_key] = (now, videos)
            logger.info("YouTube API: Found %s videos for '%s'", len(videos), keyword)
            return videos

        logger.info("YouTube API returned no videos for '%s'.", keyword)
        # If no videos found, return a fallback search entry (but caller may filter these out)
        return [self._build_fallback(keyword, reason="검색 결과가 없습니다.")]

    def get_recommended_videos(self, scores: Dict, max_results: int = 6) -> List[Dict]:
        if not scores:
            logger.warning("No scores provided for YouTube recommendations.")
            return []

        numeric_scores = {
            axis: float(value)
            for axis, value in scores.items()
            if isinstance(value, (int, float))
        }

        if not numeric_scores:
            logger.warning("Scores did not contain numeric values for recommendations.")
            return []

        sorted_axes = sorted(numeric_scores.items(), key=lambda item: item[1])
        selected_axes = [axis for axis, _ in sorted_axes[:2]] or [sorted_axes[0][0]]

        keywords: List[str] = []
        for axis in selected_axes:
            keywords.extend(self._keywords_for_axis(axis, numeric_scores[axis]))

        if not keywords:
            keywords = self.KEYWORD_TEMPLATES["default"]["neutral"]

        videos: List[Dict] = []
        seen_ids = set()

        # First pass: try to gather real video results (with videoId)
        for keyword in keywords:
            results = self.search_videos(keyword, max_results=3)
            for video in results:
                video_id = video.get("videoId")
                # prefer entries with a concrete videoId
                if not video_id:
                    continue
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                videos.append(video)
                if len(videos) >= max_results:
                    break
            if len(videos) >= max_results:
                break

        # If not enough real videos found, allow fallback search URLs to fill remaining slots
        if len(videos) < max_results:
            for keyword in keywords:
                results = self.search_videos(keyword, max_results=3)
                for video in results:
                    video_id = video.get("videoId") or video.get("url")
                    if not video_id or video_id in seen_ids:
                        continue
                    seen_ids.add(video_id)
                    videos.append(video)
                    if len(videos) >= max_results:
                        break
                if len(videos) >= max_results:
                    break

        # Ensure each returned item has a url and videoId if possible
        normalized: List[Dict] = []
        for v in videos[:max_results]:
            vid = v.get("videoId")
            url = v.get("url")
            if not vid and url and "watch?v=" in url:
                # extract videoId from URL
                try:
                    vid = url.split("watch?v=")[-1].split("&")[0]
                except Exception:
                    vid = None

            normalized.append(
                {
                    "videoId": vid,
                    "title": v.get("title"),
                    "description": v.get("description"),
                    "thumbnail": v.get("thumbnail")
                    or (
                        f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                        if vid
                        else self.FALLBACK_THUMBNAIL
                    ),
                    "channelTitle": v.get("channelTitle"),
                    "url": v.get("url")
                    if v.get("url")
                    else (
                        f"https://www.youtube.com/watch?v={vid}"
                        if vid
                        else f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}"
                    ),
                }
            )

        return normalized
