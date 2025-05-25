# youtube_scraper.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YoutubeScraper:
    def __init__(self, config):
        """
        Initializes the YoutubeScraper.

        Args:
            config (dict): Configuration dictionary. Expected to contain:
                - youtube_api_key (str): Your YouTube Data API v3 key.
                - sources (list): A list of sources to scrape. Each source is a dict.
        """
        if "youtube_api_key" not in config:
            raise ValueError("YouTube API key ('youtube_api_key') not found in config.")
        
        self.api_key = config["youtube_api_key"]
        try:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")
            raise
            
        self.config = config
        self.results = []

    def _parse_datetime(self, datetime_str):
        """Helper to parse YouTube's datetime string to ISO format."""
        try:
            # Example: 2023-10-26T14:00:00Z
            dt_obj = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt_obj.isoformat()
        except ValueError:
            logger.warning(f"Could not parse datetime string: {datetime_str}")
            return datetime_str # Return original if parsing fails

    def fetch_data(self):
        """
        Fetches data from YouTube based on the configuration.
        Iterates through sources defined in the config.
        """
        self.results = [] # Clear previous results
        for source in self.config.get("sources", []):
            source_type = source.get("type")
            try:
                if source_type == "search_videos":
                    self._fetch_videos_by_search(source)
                elif source_type == "video_comments":
                    self._fetch_video_comments(source)
                # Add more source types here in the future, e.g., channel_videos
                else:
                    logger.warning(f"Unsupported YouTube source type: {source_type}")
            except HttpError as e:
                logger.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
                self.results.append({
                    "platform": "YouTube",
                    "source_name": source.get("query") or source.get("video_id", "N/A"),
                    "error": f"An HTTP error {e.resp.status} occurred: {e.content.decode()}",
                    "signal_batch": []
                })
            except Exception as e:
                logger.error(f"An unexpected error occurred while fetching from source {source}: {e}")
                self.results.append({
                    "platform": "YouTube",
                    "source_name": source.get("query") or source.get("video_id", "N/A"),
                    "error": str(e),
                    "signal_batch": []
                })
        return self.results

    def _fetch_videos_by_search(self, source):
        """
        Fetches videos based on a search query.

        Args:
            source (dict): Source configuration. Expected to contain:
                - query (str): The search term.
                - max_results (int, optional): Maximum number of videos to fetch. Defaults to 5.
        """
        query = source.get("query")
        if not query:
            logger.warning("Search query is missing for 'search_videos' source.")
            return

        max_results = source.get("max_results", 5)
        
        logger.info(f"Searching YouTube for: '{query}' (max_results: {max_results})")

        search_response = self.youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video'
        ).execute()

        video_ids = [item['id']['videoId'] for item in search_response.get('items', []) if item['id']['kind'] == 'youtube#video']

        if not video_ids:
            logger.info(f"No videos found for query: {query}")
            self.results.append({
                "platform": "YouTube",
                "source_type": "search_videos",
                "source_name": query,
                "signal_batch": []
            })
            return

        video_details_response = self.youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        ).execute()
        
        batch = {
            "platform": "YouTube",
            "source_type": "search_videos",
            "source_name": query,
            "signal_batch": []
        }

        for video_item in video_details_response.get('items', []):
            snippet = video_item.get('snippet', {})
            statistics = video_item.get('statistics', {})
            content_details = video_item.get('contentDetails', {})

            batch["signal_batch"].append({
                "video_id": video_item.get('id'),
                "video_title": snippet.get('title'),
                "description": snippet.get('description'),
                "channel_id": snippet.get('channelId'),
                "channel_title": snippet.get('channelTitle'),
                "published_at": self._parse_datetime(snippet.get('publishedAt')),
                "thumbnail_url": snippet.get('thumbnails', {}).get('default', {}).get('url'),
                "url": f"https://www.youtube.com/watch?v={video_item.get('id')}",
                "duration": content_details.get('duration'), # PTnMNS format
                "view_count": int(statistics.get('viewCount', 0)),
                "like_count": int(statistics.get('likeCount', 0)),
                # "dislike_count": statistics.get('dislikeCount'), # Dislike count is often not available
                "comment_count": int(statistics.get('commentCount', 0)),
                "tags": snippet.get('tags', [])
            })
        self.results.append(batch)

    def _fetch_video_comments(self, source):
        """
        Fetches top-level comments for a specific video.

        Args:
            source (dict): Source configuration. Expected to contain:
                - video_id (str): The ID of the YouTube video.
                - max_results (int, optional): Maximum number of comments to fetch. Defaults to 10.
        """
        video_id = source.get("video_id")
        if not video_id:
            logger.warning("Video ID is missing for 'video_comments' source.")
            return

        max_results = source.get("max_results", 10)
        logger.info(f"Fetching comments for YouTube video ID: '{video_id}' (max_results: {max_results})")

        try:
            comment_threads_response = self.youtube.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=max_results,
                textFormat='plainText' # or 'html'
            ).execute()
        except HttpError as e:
            if e.resp.status == 403: # Comments disabled
                 logger.warning(f"Comments are disabled for video ID: {video_id}. Error: {e.content.decode()}")
                 self.results.append({
                    "platform": "YouTube",
                    "source_type": "video_comments",
                    "source_name": f"video_id_{video_id}",
                    "video_id": video_id,
                    "error": "Comments are disabled for this video.",
                    "signal_batch": []
                })
                 return
            raise # Re-raise other HttpErrors

        batch = {
            "platform": "YouTube",
            "source_type": "video_comments",
            "source_name": f"video_id_{video_id}",
            "video_id": video_id,
            "signal_batch": []
        }

        for item in comment_threads_response.get('items', []):
            top_level_comment = item['snippet']['topLevelComment']['snippet']
            comment_data = {
                "comment_id": item['snippet']['topLevelComment']['id'],
                "author_display_name": top_level_comment.get('authorDisplayName'),
                "author_profile_image_url": top_level_comment.get('authorProfileImageUrl'),
                "author_channel_url": top_level_comment.get('authorChannelUrl'), # May not always be present
                "text_display": top_level_comment.get('textDisplay'),
                "like_count": top_level_comment.get('likeCount', 0),
                "published_at": self._parse_datetime(top_level_comment.get('publishedAt')),
                "updated_at": self._parse_datetime(top_level_comment.get('updatedAt')),
                "total_reply_count": item['snippet'].get('totalReplyCount', 0),
                "replies": [] # Placeholder for actual replies if needed later
            }
            
            # Fetch replies if present and needed (adds API cost)
            # if item.get('replies') and item['snippet']['totalReplyCount'] > 0:
            #     for reply_item in item['replies']['comments']:
            #         reply_snippet = reply_item['snippet']
            #         comment_data['replies'].append({
            #             "comment_id": reply_item['id'],
            #             "author_display_name": reply_snippet.get('authorDisplayName'),
            #             "text_display": reply_snippet.get('textDisplay'),
            #             "like_count": reply_snippet.get('likeCount', 0),
            #             "published_at": self._parse_datetime(reply_snippet.get('publishedAt')),
            #         })
            batch["signal_batch"].append(comment_data)
        
        self.results.append(batch)

if __name__ == '__main__':
    # Example Usage (requires a valid API key and a config.json file)
    # Create a config.json file like this:
    # {
    #   "youtube_api_key": "YOUR_YOUTUBE_DATA_API_KEY",
    #   "sources": [
    #     {
    #       "type": "search_videos",
    #       "query": "python programming tutorial for beginners",
    #       "max_results": 2
    #     },
    #     {
    #       "type": "video_comments",
    #       "video_id": "VIDEO_ID_FROM_SEARCH_OR_KNOWN_VIDEO", 
    #       "max_results": 3
    #     }
    #   ]
    # }
    import json
    try:
        with open('config.json', 'r') as f:
            sample_config = json.load(f)
        
        # Make sure to replace "VIDEO_ID_FROM_SEARCH_OR_KNOWN_VIDEO" with an actual video ID
        # For testing, you might want to run the search first, get a video ID, then run comments.
        # Example: find a video_id from the search results above and plug it in
        # sample_config["sources"][1]["video_id"] = "some_actual_video_id" 
        
        if not sample_config.get("youtube_api_key") or sample_config["youtube_api_key"] == "YOUR_YOUTUBE_DATA_API_KEY":
            print("Please add your YouTube Data API Key to config.json")
        elif len(sample_config["sources"]) > 1 and sample_config["sources"][1]["video_id"] == "VIDEO_ID_FROM_SEARCH_OR_KNOWN_VIDEO":
             print("Please update 'VIDEO_ID_FROM_SEARCH_OR_KNOWN_VIDEO' in config.json with an actual video ID to test comments.")
        else:
            scraper = YoutubeScraper(sample_config)
            data = scraper.fetch_data()
            print(json.dumps(data, indent=2))

    except FileNotFoundError:
        print("Create a 'config.json' file with your API key and sources to run this example.")
    except Exception as e:
        print(f"An error occurred: {e}")

