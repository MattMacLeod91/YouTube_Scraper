# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_scraper import YoutubeScraper

app = FastAPI()

# ✅ Enable CORS so Loveable frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict to specific domains later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📩 Request body structure (frontend will send this)
class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    api_key: str  # 🔐 passed from Loveable

class CommentRequest(BaseModel):
    video_id: str
    max_results: int = 100
    api_key: str  # 🔐 passed from Loveable

# 🔍 Search YouTube videos
@app.post("/api/youtube/search-videos")
async def search_videos(req: SearchRequest):
    scraper = YoutubeScraper(req.api_key)
    return scraper.search_videos(req.query, req.max_results)

# 💬 Fetch comments from a video
@app.post("/api/youtube/fetch-comments")
async def fetch_comments(req: CommentRequest):
    scraper = YoutubeScraper(req.api_key)
    return scraper.fetch_comments(req.video_id, req.max_results)
