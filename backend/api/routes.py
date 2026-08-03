"""
FastAPI API Routes for AI Background Remover.
"""
import os
import uuid
import time
import shutil
import asyncio
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from PIL import Image

from services.background import remove_background
from services.image import (
    validate_image_file,
    sanitize_filename,
    generate_output_filename,
    create_white_background_image,
    create_thumbnail
)
from services.zip import create_zip_archive

logger = logging.getLogger("bg_remover.api.routes")
router = APIRouter(prefix="/api")

# Base storage directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# In-memory storage for active jobs
JOBS: Dict[str, dict] = {}

# ThreadPoolExecutor for heavy background AI processing
executor = ThreadPoolExecutor(max_workers=4)

class ProcessRequest(BaseModel):
    job_id: str
    output_format: str = "jpg"
    image_ids: Optional[List[str]] = None

class DownloadSelectedRequest(BaseModel):
    image_ids: List[str]

@router.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    """
    Accepts up to 20 images, validates file size and format, saves uploads,
    and returns initial job metadata.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
        
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 images allowed per batch.")
        
    job_id = str(uuid.uuid4())
    job_upload_dir = os.path.join(UPLOADS_DIR, job_id)
    job_output_dir = os.path.join(OUTPUTS_DIR, job_id)
    job_temp_dir = os.path.join(TEMP_DIR, job_id)
    
    os.makedirs(job_upload_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)
    os.makedirs(job_temp_dir, exist_ok=True)
    
    job_data = {
        "job_id": job_id,
        "status": "Waiting",
        "total_images": len(files),
        "completed_images": 0,
        "failed_images": 0,
        "start_time": None,
        "end_time": None,
        "processing_speed": 0.0,
        "is_cancelled": False,
        "images": {}
    }
    
    for file in files:
        image_id = str(uuid.uuid4())[:8]
        sanitized_name = sanitize_filename(file.filename or "image.jpg")
        
        # Read content to check size and validate
        content = await file.read()
        file_size = len(content)
        
        try:
            validate_image_file(file.filename or "image.jpg", file.content_type, file_size)
            
            # Save original upload
            upload_path = os.path.join(job_upload_dir, f"{image_id}_{sanitized_name}")
            with open(upload_path, "wb") as f:
                f.write(content)
                
            # Create thumbnail preview
            img = Image.open(upload_path)
            thumb = create_thumbnail(img)
            thumb_filename = f"thumb_{image_id}.jpg"
            thumb_path = os.path.join(job_temp_dir, thumb_filename)
            thumb.convert("RGB").save(thumb_path, "JPEG", quality=85)
            
            output_name = generate_output_filename(sanitized_name, "jpg")
            
            job_data["images"][image_id] = {
                "id": image_id,
                "original_filename": file.filename or "image.jpg",
                "sanitized_filename": sanitized_name,
                "output_filename": output_name,
                "file_size": file_size,
                "file_size_formatted": f"{file_size / (1024*1024):.2f} MB" if file_size >= 1024*1024 else f"{file_size / 1024:.1f} KB",
                "status": "Waiting",
                "progress": 0,
                "error": None,
                "upload_path": upload_path,
                "thumb_path": thumb_path,
                "output_path": None,
            }
        except Exception as e:
            logger.warning(f"File validation failed for {file.filename}: {e}")
            job_data["images"][image_id] = {
                "id": image_id,
                "original_filename": file.filename or "image.jpg",
                "sanitized_filename": sanitized_name,
                "output_filename": generate_output_filename(sanitized_name, "jpg"),
                "file_size": file_size,
                "file_size_formatted": f"{file_size / 1024:.1f} KB",
                "status": "Failed",
                "progress": 0,
                "error": str(e),
                "upload_path": None,
                "thumb_path": None,
                "output_path": None,
            }
            job_data["failed_images"] += 1

    JOBS[job_id] = job_data
    return JSONResponse(status_code=200, content=job_data)

def _process_single_image(job_id: str, image_id: str, output_format: str):
    """
    Synchronous processing unit run inside ThreadPoolExecutor.
    Removes background using rembg and composites onto pure white canvas.
    """
    if job_id not in JOBS:
        return
        
    job = JOBS[job_id]
    if job.get("is_cancelled"):
        return
        
    img_meta = job["images"].get(image_id)
    if not img_meta or img_meta["status"] == "Failed" or not img_meta["upload_path"]:
        return

    try:
        # Step 1: Removing Background
        img_meta["status"] = "Removing Background"
        img_meta["progress"] = 25
        
        orig_img = Image.open(img_meta["upload_path"])
        rgba_img = remove_background(orig_img)
        
        if job.get("is_cancelled"):
            return
            
        # Step 2: Adding White Background
        img_meta["status"] = "Adding White Background"
        img_meta["progress"] = 65
        
        white_img = create_white_background_image(rgba_img, output_format=output_format, quality=95)
        
        if job.get("is_cancelled"):
            return

        # Step 3: Compressing & Saving Output
        img_meta["status"] = "Compressing"
        img_meta["progress"] = 85
        
        output_filename = generate_output_filename(img_meta["original_filename"], output_format)
        img_meta["output_filename"] = output_filename
        
        job_output_dir = os.path.join(OUTPUTS_DIR, job_id)
        output_path = os.path.join(job_output_dir, output_filename)
        
        if output_format.lower() in ("jpg", "jpeg"):
            white_img.save(output_path, "JPEG", quality=95, optimize=True)
        else:
            rgba_img.save(output_path, "PNG", optimize=True)
            
        img_meta["output_path"] = output_path
        img_meta["status"] = "Completed"
        img_meta["progress"] = 100
        job["completed_images"] += 1

    except Exception as e:
        logger.error(f"Error processing image {image_id}: {e}", exc_info=True)
        img_meta["status"] = "Failed"
        img_meta["progress"] = 0
        img_meta["error"] = str(e)
        job["failed_images"] += 1

async def _process_job_worker(job_id: str, output_format: str, target_image_ids: Optional[List[str]] = None):
    """
    Background worker loop managing batch image processing tasks.
    """
    if job_id not in JOBS:
        return
        
    job = JOBS[job_id]
    job["status"] = "Processing"
    job["start_time"] = time.time()
    
    images_to_process = target_image_ids or list(job["images"].keys())
    
    loop = asyncio.get_event_loop()
    
    for img_id in images_to_process:
        if job.get("is_cancelled"):
            job["status"] = "Cancelled"
            break
            
        img_meta = job["images"].get(img_id)
        if not img_meta or img_meta["status"] in ("Completed", "Failed") and target_image_ids is None:
            continue
            
        # Run CPU/AI heavy task in threadpool
        await loop.run_in_executor(executor, _process_single_image, job_id, img_id, output_format)
        
        # Calculate speed
        elapsed = time.time() - job["start_time"]
        if elapsed > 0 and job["completed_images"] > 0:
            job["processing_speed"] = round(job["completed_images"] / elapsed, 2)
            
    job["end_time"] = time.time()
    if not job.get("is_cancelled"):
        if job["completed_images"] + job["failed_images"] >= job["total_images"]:
            job["status"] = "Completed" if job["failed_images"] == 0 else "Completed With Errors"

@router.post("/process")
async def process_images(req: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Triggers batch background image processing for the given job.
    """
    if req.job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    job = JOBS[req.job_id]
    if job["status"] == "Processing":
        return JSONResponse(status_code=200, content={"message": "Job is already processing."})
        
    job["is_cancelled"] = False
    background_tasks.add_task(_process_job_worker, req.job_id, req.output_format, req.image_ids)
    return JSONResponse(status_code=200, content={"message": "Processing started.", "job_id": req.job_id})

@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Returns real-time status and metadata for a job.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    job = JOBS[job_id]
    
    # Calculate overall progress percentage
    total = job["total_images"]
    done = job["completed_images"] + job["failed_images"]
    overall_progress = int((done / total) * 100) if total > 0 else 0
    
    response_data = {
        "job_id": job["job_id"],
        "status": job["status"],
        "overall_progress": overall_progress,
        "total_images": total,
        "completed_images": job["completed_images"],
        "failed_images": job["failed_images"],
        "remaining_images": total - done,
        "processing_speed": job["processing_speed"],
        "images": list(job["images"].values())
    }
    return JSONResponse(status_code=200, content=response_data)

@router.get("/preview/{job_id}/{image_id}/{preview_type}")
async def get_preview(job_id: str, image_id: str, preview_type: str):
    """
    Serves thumbnail, original, or processed output image.
    preview_type options: 'original', 'processed', 'thumb'
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    img_meta = JOBS[job_id]["images"].get(image_id)
    if not img_meta:
        raise HTTPException(status_code=404, detail="Image not found.")
        
    if preview_type == "thumb" and img_meta["thumb_path"] and os.path.exists(img_meta["thumb_path"]):
        return FileResponse(img_meta["thumb_path"], media_type="image/jpeg")
    elif preview_type == "original" and img_meta["upload_path"] and os.path.exists(img_meta["upload_path"]):
        return FileResponse(img_meta["upload_path"])
    elif preview_type == "processed" and img_meta["output_path"] and os.path.exists(img_meta["output_path"]):
        return FileResponse(img_meta["output_path"])
    else:
        # Fallback to thumbnail or upload if requested preview type isn't ready
        if img_meta["thumb_path"] and os.path.exists(img_meta["thumb_path"]):
            return FileResponse(img_meta["thumb_path"])
        elif img_meta["upload_path"] and os.path.exists(img_meta["upload_path"]):
            return FileResponse(img_meta["upload_path"])
            
    raise HTTPException(status_code=404, detail="Requested file not found.")

@router.get("/download/{job_id}/{image_id}")
async def download_single_image(job_id: str, image_id: str):
    """
    Downloads an individual processed image.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    img_meta = JOBS[job_id]["images"].get(image_id)
    if not img_meta or not img_meta["output_path"] or not os.path.exists(img_meta["output_path"]):
        raise HTTPException(status_code=404, detail="Processed file not available.")
        
    return FileResponse(
        img_meta["output_path"],
        filename=img_meta["output_filename"],
        media_type="application/octet-stream"
    )

@router.get("/download-zip/{job_id}")
async def download_all_zip(job_id: str):
    """
    Creates and returns a ZIP archive containing all completed images.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    job = JOBS[job_id]
    completed_paths = [
        meta["output_path"] for meta in job["images"].values()
        if meta["status"] == "Completed" and meta["output_path"] and os.path.exists(meta["output_path"])
    ]
    
    if not completed_paths:
        raise HTTPException(status_code=400, detail="No processed images available for download.")
        
    zip_filename = "Converted_Images.zip"
    zip_path = os.path.join(TEMP_DIR, job_id, zip_filename)
    create_zip_archive(completed_paths, zip_path)
    
    return FileResponse(
        zip_path,
        filename=zip_filename,
        media_type="application/zip"
    )

@router.post("/download-selected/{job_id}")
async def download_selected_zip(job_id: str, req: DownloadSelectedRequest):
    """
    Creates and returns a ZIP archive containing only selected completed images.
    """
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job ID not found.")
        
    job = JOBS[job_id]
    selected_paths = []
    
    for img_id in req.image_ids:
        meta = job["images"].get(img_id)
        if meta and meta["status"] == "Completed" and meta["output_path"] and os.path.exists(meta["output_path"]):
            selected_paths.append(meta["output_path"])
            
    if not selected_paths:
        raise HTTPException(status_code=400, detail="No valid processed images selected for download.")
        
    zip_filename = "Selected_Converted_Images.zip"
    zip_path = os.path.join(TEMP_DIR, job_id, zip_filename)
    create_zip_archive(selected_paths, zip_path)
    
    return FileResponse(
        zip_path,
        filename=zip_filename,
        media_type="application/zip"
    )

@router.delete("/cancel/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancels an active job and removes temp/upload/output directories.
    """
    if job_id in JOBS:
        JOBS[job_id]["is_cancelled"] = True
        JOBS[job_id]["status"] = "Cancelled"
        
    # Clean files
    for base in (UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR):
        target = os.path.join(base, job_id)
        if os.path.exists(target):
            try:
                shutil.rmtree(target)
            except Exception as e:
                logger.warning(f"Error deleting job dir {target}: {e}")
                
    if job_id in JOBS:
        del JOBS[job_id]
        
    return JSONResponse(status_code=200, content={"message": "Job cancelled and resources cleaned up."})
