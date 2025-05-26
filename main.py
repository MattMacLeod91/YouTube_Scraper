# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_scraper import YoutubeScraper
from googleapiclient.errors import HttpError
from fastapi.responses import JSONResponse

app = FastAPI()

# ✅ CORS so Loveable can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📩 Request Schemas
class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    api_key: str
    published_after: str | None = None  # Optional ISO 8601 timestamp

class CommentRequest(BaseModel):
    video_id: str
    max_results: int = 100
    api_key: str

# 🔍 Search YouTube videos
@app.post("/api/youtube/search-videos")
async def search_videos(req: SearchRequest):
    scraper = YoutubeScraper(req.api_key)
    return scraper.search_videos(req.query, req.max_results, req.published_after)

    except HttpError as e:
        return JSONResponse(
            status_code=e.resp.status,
            content={"error": f"YouTube API error: {e.error_details if hasattr(e, 'error_details') else str(e)}"},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})

# 💬 Fetch comments
@app.post("/api/youtube/fetch-comments")
async def fetch_comments(req: CommentRequest):
    try:
        scraper = YoutubeScraper(req.api_key)
        return scraper.fetch_comments(req.video_id, req.max_results)
    except HttpError as e:
        return JSONResponse(
            status_code=e.resp.status,
            content={"error": f"YouTube API error: {e.error_details if hasattr(e, 'error_details') else str(e)}"},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Unexpected error: {str(e)}"})
