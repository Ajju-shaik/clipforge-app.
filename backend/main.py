import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ClipForge API")

# Allow the frontend to communicate with the backend.
# We will restrict this to your website's domain later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("/tmp/clipforge_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

jobs = {}


@app.get("/")
def home():
    return {"message": "ClipForge API is running"}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ClipForge"}


@app.post("/api/jobs/upload")
async def upload_video(
    file: UploadFile = File(...),
    clip_count: int = Form(5),
    duration: str = Form("30-45 sec"),
    ratio: str = Form("9:16 Vertical"),
    language: str = Form("Auto-detect"),
    caption_preset: str = Form("clean"),
):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a video file."
        )

    job_id = str(uuid.uuid4())
    extension = Path(file.filename or "video.mp4").suffix or ".mp4"
    destination = UPLOAD_DIR / f"{job_id}{extension}"

    size = 0
    max_size = 100 * 1024 * 1024  # 100 MB test limit

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail="Video exceeds the 100 MB test limit."
                    )

                output.write(chunk)

    except Exception:
        destination.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    jobs[job_id] = {
        "job_id": job_id,
        "status": "received",
        "message": (
            "Video received. Processing engine is not connected yet."
        ),
        "filename": file.filename,
        "size_bytes": size,
        "preferences": {
            "clip_count": clip_count,
            "duration": duration,
            "ratio": ratio,
            "language": language,
            "caption_preset": caption_preset,
        },
    }

    return jobs[job_id]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return jobs[job_id]
