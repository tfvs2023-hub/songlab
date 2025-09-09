from googleapiclient.discovery import build
from typing import List, Dict

class YouTubeService:
    def __init__(self):
        self.api_key = "AIzaSyBjA6trv3wFn0OMLRMc82QIome84rdLc5k"
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    def search_videos(self, keyword: str, max_results: int = 3) -> List[Dict]:
        """
        YouTube에서 키워드로 동영상 검색
        """
        try:
            # YouTube API 호출
            search_response = self.youtube.search().list(
                q=keyword + " 보컬 레슨",
                part='id,snippet',
                maxResults=max_results,
                type='video',
                relevanceLanguage='ko',
                regionCode='KR'
            ).execute()
            
            videos = []
            for item in search_response.get('items', []):
                video = {
                    'videoId': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'][:200],
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'channelTitle': item['snippet']['channelTitle'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                }
                videos.append(video)
            
            return videos
            
        except Exception as e:
            print(f"YouTube API error: {e}")
            # 에러 시 기본 검색 URL 반환
            return [{
                'videoId': None,
                'title': f"{keyword} 검색하기",
                'description': "YouTube에서 직접 검색해보세요",
                'thumbnail': "https://via.placeholder.com/480x360?text=YouTube+Search",
                'channelTitle': "YouTube",
                'url': f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}"
            }]