# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from youtube_scraper import YoutubeScraper
from googleapiclient.errors import HttpError

app = FastAPI()

# CORS so Loveable can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Schemas
class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    api_key: str
    published_after: str | None = None

class CommentRequest(BaseModel):
    video_id: str
    max_results: int = 100
    api_key: str

# Search Endpoint
@app.post("/api/youtube/search-videos")
async def search_videos(req: SearchRequest):
    try:
        scraper = YoutubeScraper(req.api_key)
        return scraper.search_videos(req.query, req.max_results, req.published_after)
    except HttpError as e:
        return JSONResponse(status_code=500, content={"error": f"YouTube API error: {str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})

# Comment Endpoint
@app.post("/api/youtube/fetch-comments")
async def fetch_comments(req: CommentRequest):
    try:
        scraper = YoutubeScraper(req.api_key)
        return scraper.fetch_comments(req.video_id, req.max_results)
    except HttpError as e:
        return JSONResponse(status_code=500, content={"error": f"YouTube API error: {str(e)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
