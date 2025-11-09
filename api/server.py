"""
NovaAvatar FastAPI Server
REST API for avatar video generation.
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.orchestrator import PipelineOrchestrator, JobStatus, VideoJob
from services.content_scraper import ContentItem
from services.script_generator import ScriptStyle


# API Models
class ScrapeRequest(BaseModel):
    """Request to scrape content."""
    max_items: int = 10
    sources: Optional[List[str]] = None


class GenerateRequest(BaseModel):
    """Request to generate video from content."""
    content_title: str
    content_description: str
    style: str = ScriptStyle.PROFESSIONAL.value
    duration: int = 45


class ManualGenerateRequest(BaseModel):
    """Request to manually generate video."""
    prompt: str
    image_path: str
    audio_path: str
    num_steps: int = 25
    guidance_scale: float = 4.5


class JobResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: int
    video_file: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Initialize FastAPI app
app = FastAPI(
    title="NovaAvatar API",
    description="Automated avatar video generation API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = PipelineOrchestrator()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "NovaAvatar API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "scrape": "/api/scrape",
            "generate": "/api/generate",
            "jobs": "/api/jobs",
            "queue": "/api/queue"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "orchestrator": "ok",
            "redis": "ok" if orchestrator.enable_queue else "disabled"
        }
    }


@app.post("/api/scrape", response_model=List[dict])
async def scrape_content(request: ScrapeRequest):
    """
    Scrape content from configured sources.

    Returns list of scraped content items.
    """
    try:
        logger.info(f"Scraping content: max_items={request.max_items}")

        items = await orchestrator.scrape_content(
            max_items=request.max_items
        )

        # Convert to dict for JSON response
        return [item.dict() for item in items]

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate", response_model=JobResponse)
async def generate_video(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate video from content description.

    Runs in background and returns job ID for tracking.
    """
    try:
        logger.info(f"Generating video: {request.content_title}")

        # Create content item
        content_item = ContentItem(
            title=request.content_title,
            description=request.content_description,
            source="api",
            source_name="API Request"
        )

        # Start generation in background
        job = await orchestrator.create_video_from_content(
            content_item,
            style=ScriptStyle(request.style),
            duration=request.duration
        )

        return JobResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            video_file=job.video_file,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at
        )

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/manual", response_model=JobResponse)
async def generate_manual(request: ManualGenerateRequest):
    """Generate video from manual inputs (image + audio + prompt)."""
    try:
        logger.info("Manual video generation")

        # Validate files exist
        if not Path(request.image_path).exists():
            raise HTTPException(status_code=404, detail="Image file not found")

        if not Path(request.audio_path).exists():
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Generate video
        video = await orchestrator.avatar_service.generate_video(
            prompt=request.prompt,
            image_path=request.image_path,
            audio_path=request.audio_path
        )

        # Create job record
        import uuid
        job_id = str(uuid.uuid4())

        job = VideoJob(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            video_file=video.video_path,
            progress=100,
            metadata={"manual_creation": True}
        )

        orchestrator.jobs[job_id] = job
        orchestrator._save_jobs()

        return JobResponse(
            job_id=job.job_id,
            status=job.status.value,
            progress=job.progress,
            video_file=job.video_file,
            error=job.error,
            created_at=job.created_at,
            updated_at=job.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 100
):
    """
    List all jobs, optionally filtered by status.

    Args:
        status: Filter by job status (pending, completed, failed, etc.)
        limit: Maximum number of jobs to return
    """
    try:
        jobs = orchestrator.jobs.values()

        # Filter by status if provided
        if status:
            try:
                status_enum = JobStatus(status)
                jobs = [j for j in jobs if j.status == status_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        # Sort by creation time (newest first)
        jobs = sorted(jobs, key=lambda x: x.created_at, reverse=True)

        # Limit results
        jobs = list(jobs)[:limit]

        return [
            JobResponse(
                job_id=j.job_id,
                status=j.status.value,
                progress=j.progress,
                video_file=j.video_file,
                error=j.error,
                created_at=j.created_at,
                updated_at=j.updated_at
            )
            for j in jobs
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    job = orchestrator.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        video_file=job.video_file,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at
    )


@app.get("/api/queue", response_model=List[JobResponse])
async def get_review_queue():
    """Get all videos in review queue."""
    try:
        queue = orchestrator.get_review_queue()

        return [
            JobResponse(
                job_id=j.job_id,
                status=j.status.value,
                progress=j.progress,
                video_file=j.video_file,
                error=j.error,
                created_at=j.created_at,
                updated_at=j.updated_at
            )
            for j in queue
        ]

    except Exception as e:
        logger.error(f"Failed to get queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/queue/{job_id}/approve")
async def approve_video(job_id: str):
    """Approve a video from the review queue."""
    try:
        job = orchestrator.approve_video(job_id)

        return {
            "status": "approved",
            "job_id": job_id,
            "video_file": job.video_file
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its associated files."""
    try:
        orchestrator.delete_video(job_id)

        return {
            "status": "deleted",
            "job_id": job_id
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/{job_id}")
async def download_video(job_id: str):
    """Download the video file for a job."""
    job = orchestrator.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if not job.video_file:
        raise HTTPException(status_code=404, detail=f"Video not generated yet")

    video_path = Path(job.video_file)

    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Video file not found")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"avatar_{job_id}.mp4"
    )


@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image file."""
    try:
        # Save to uploads directory
        upload_dir = Path("storage/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Image uploaded: {file_path}")

        return {
            "status": "uploaded",
            "filename": file.filename,
            "path": str(file_path)
        }

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload an audio file."""
    try:
        # Save to uploads directory
        upload_dir = Path("storage/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Audio uploaded: {file_path}")

        return {
            "status": "uploaded",
            "filename": file.filename,
            "path": str(file_path)
        }

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # Setup logging
    logger.add(
        "logs/api_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )

    # Run server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
