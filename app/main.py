from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, HTMLResponse
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import zipfile
import io
import asyncio
from pathlib import Path
import aiofiles
import uuid
from dataclasses import dataclass
import os
from pydantic import BaseModel

from app.services.external_api import ExternalAPI
from app.services.count_stat import calculate_stat
from app.database.db import Database

CANDIDATE_ID = str(uuid.uuid4())
db = Database()
app = FastAPI()

NOVOSIBIRSK_TZ = timezone(timedelta(hours=7))

@dataclass
class DownloadStatus:
    is_running: bool = False
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    total_downloaded: int = 0

download_status = DownloadStatus()

static_dir = os.path.join(os.path.dirname(__file__), "static")

class CalculateRequest(BaseModel):
    file_names: List[str]



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)

@app.get("/")
async def root():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/start-download")
async def start_download(background_tasks: BackgroundTasks):
    if download_status.is_running:
        return {"status": "already_running", "message": "Скачивание уже выполняется"}
    background_tasks.add_task(download_all_files)
    return {"status": "started"}

@app.get("/api/download-status")
async def get_status():
    total_in_db = db.get_total_count()
    return {
        "is_running": download_status.is_running,
        "total_downloaded": total_in_db,
        "total_files": None,
        "started_at": download_status.started_at.isoformat() if download_status.started_at else None,
        "finished_at": download_status.finished_at.isoformat() if download_status.finished_at else None,
    }

@app.get("/api/files")
async def get_files(page: int = 1, per_page: int = 10):
    offset = (page - 1) * per_page
    files = db.get_all_files(limit=per_page, offset=offset)
    total = db.get_total_count()
    
    return {
        "items": files,
        "total": total,
        "page": page,
        "per_page": per_page
    }

@app.post("/api/calculate")
async def calculate_stats(payload: CalculateRequest):
    total_stat, per_file = await calculate_stat(file_names=payload.file_names)
    return {
        "total_stats": total_stat,
        "per_file": per_file
    }

async def download_all_files():
    global download_status
    
    download_status.is_running = True
    download_status.started_at = datetime.now(NOVOSIBIRSK_TZ)
    download_status.finished_at = None

    client = ExternalAPI(
        base_url="http://91.199.149.128:18001",
        candidate_id=CANDIDATE_ID
    )
    
    Path("files").mkdir(exist_ok=True)
    
    while True:
        try:
            names = await client.get_names()
            
            if not names:
                print("Все файлы скачаны!")
                break
            
            batch = names[:3]
            print(f"Скачиваю: {batch}")
            
            zip_data = await client.download_files(batch)
            
            files_content = {}
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    content = zip_ref.read(file_name).decode('utf-8')
                    files_content[file_name] = content
                    
                    file_path = Path("files") / file_name
                    async with aiofiles.open(file_path, 'w') as f:
                        await f.write(content)
            
            now = datetime.now(NOVOSIBIRSK_TZ).isoformat()
            db.add_files([
                (file_name, content, now) 
                for file_name, content in files_content.items()
            ])
            
            await client.mark_files(batch)
            print(f"Отметил как скачанные: {batch}")
            download_status.total_downloaded = db.get_total_count()
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"Ошибка: {e}")
            await asyncio.sleep(5)
            break
        finally:
            download_status.is_running = False
            download_status.finished_at = datetime.now(NOVOSIBIRSK_TZ)
            download_status.total_downloaded = db.get_total_count()
            print("Процесс скачивания завершён")
            break