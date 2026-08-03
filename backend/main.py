"""
Main FastAPI Application Entry Point for AI Background Remover.
"""
import os
import time
import shutil
import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from api.routes import router as api_router, UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR, JOBS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bg_remover.main")

FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

async def cleanup_old_files_loop():
    """
    Background periodic task cleaning up job directories older than 1 hour (3600 seconds).
    """
    while True:
        try:
            await asyncio.sleep(600)  # Check every 10 minutes
            now = time.time()
            max_age = 3600  # 1 hour
            
            logger.info("Running scheduled directory cleanup task...")
            
            expired_jobs = []
            for job_id, job in list(JOBS.items()):
                start_time = job.get("start_time") or job.get("created_at") or now
                if now - start_time > max_age:
                    expired_jobs.append(job_id)
                    
            for job_id in expired_jobs:
                logger.info(f"Cleaning up expired job {job_id}")
                for base in (UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR):
                    path = os.path.join(base, job_id)
                    if os.path.exists(path):
                        try:
                            shutil.rmtree(path)
                        except Exception as e:
                            logger.warning(f"Failed to remove expired dir {path}: {e}")
                if job_id in JOBS:
                    del JOBS[job_id]
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Starting AI Background Remover Backend Service...")
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    cleanup_task = asyncio.create_task(cleanup_old_files_loop())
    
    yield
    
    # Shutdown tasks
    logger.info("Shutting down AI Background Remover Backend Service...")
    cleanup_task.cancel()

app = FastAPI(
    title="AI Background Remover API",
    description="High-performance background removal with pure white canvas replacement for product photography.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router)

# Mount frontend directory to serve single page web application
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR}. API only mode.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
