# main.py (YouTube Only)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_scraper import YoutubeScraper # Import the YoutubeScraper
from googleapiclient.errors import HttpError # For handling YouTube API errors

app = FastAPI()

# --- Models ---
class ScrapeConfigRequest(BaseModel):
    """
    Configuration for YouTube scraping.
    """
    platform_config: dict # The actual configuration for the YoutubeScraper

# --- YouTube Scraping ---
@app.post("/scrape_youtube")
async def scrape_youtube_endpoint(request: ScrapeConfigRequest):
    """
    Endpoint to scrape data from YouTube.
    The 'platform_config' should contain the YouTube API key and sources.
    Example platform_config for YouTube:
    {
        "youtube_api_key": "YOUR_YOUTUBE_DATA_API_KEY",
        "sources": [
            {
                "type": "search_videos",
                "query": "fastapi tutorial",
                "max_results": 3
            },
            {
                "type": "video_comments",
                "video_id": "SOME_VIDEO_ID",
                "max_results": 5
            }
        ]
    }
    """
    try:
        scraper = YoutubeScraper(request.platform_config)
        data = scraper.fetch_data()
        return {"status": "success", "platform": "YouTube", "data": data}
    except ValueError as ve: # Catch specific errors like missing API key
        raise HTTPException(status_code=400, detail=str(ve))
    except HttpError as he: # Catch Google API specific HTTP errors
        error_content = he.content.decode() if he.content else "No further details."
        raise HTTPException(status_code=he.resp.status, detail=f"YouTube API error: {error_content}")
    except Exception as e:
        # Consider logging the full traceback here for debugging
        # import traceback
        # print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error during YouTube scraping: {str(e)}")

@app.get("/")
async def root():
    return {"message": "YouTube Scraper API is running. Use /scrape_youtube."}

# To run this app (if you save it as main.py):
# uvicorn main:app --reload
