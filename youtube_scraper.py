# youtube_scraper.py
from googleapiclient.discovery import build
from isodate import parse_duration

class YoutubeScraper:
    def __init__(self, api_key):
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def search_videos(self, query, max_results=10):
        search_response = self.youtube.search().list(
            q=query,
            type="video",
            part="id",
            maxResults=max_results
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
        if not video_ids:
            return {"videos": [], "total_results": 0}

        videos_response = self.youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()

        def format_duration(iso_str):
            try:
                seconds = int(parse_duration(iso_str).total_seconds())
                minutes = seconds // 60
                secs = seconds % 60
                return f"{minutes:02}:{secs:02}"
            except:
                return "00:00"

        videos = []
        for item in videos_response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            videos.append({
                "video_id": item["id"],
                "title": snippet.get("title", ""),
                "channel_name": snippet.get("channelTitle", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration": format_duration(content.get("duration", "")),
                "published_at": snippet.get("publishedAt", ""),
                "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", "")
            })

        return {
            "videos": videos,
            "total_results": len(videos)
        }

    def fetch_comments(self, video_id, max_results=100):
        comments = []
        next_page_token = None
        total_fetched = 0

        while total_fetched < max_results:
            request = self.youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_results - total_fetched),
                pageToken=next_page_token
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "comment_id": item["id"],
                    "author_name": snippet.get("authorDisplayName", ""),
                    "comment_text": snippet.get("textDisplay", ""),
                    "like_count": int(snippet.get("likeCount", 0)),
                    "published_at": snippet.get("publishedAt", ""),
                    "is_reply": False
                })

            total_fetched += len(response.get("items", []))
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        # Fetch video title for metadata
        video_data = self.youtube.videos().list(
            part="snippet",
            id=video_id
        ).execute()
        video_title = video_data["items"][0]["snippet"]["title"] if video_data["items"] else "Unknown Title"

        return {
            "comments": comments,
            "video_metadata": {
                "video_id": video_id,
                "title": video_title
            },
            "total_comments": len(comments),
            "has_more": bool(next_page_token)
        }
