"""
ZIP Archive Service for batch downloading processed images directly in memory or to disk.
"""
import io
import os
import zipfile
import logging
from typing import List, Tuple

logger = logging.getLogger("bg_remover.services.zip")

def create_zip_bytes(file_entries: List[Tuple[str, bytes]]) -> bytes:
    """
    Creates an in-memory ZIP archive from a list of (filename, file_bytes) tuples.
    Returns the ZIP archive as raw bytes.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename, file_bytes in file_entries:
            zipf.writestr(filename, file_bytes)
            
    return zip_buffer.getvalue()

def create_zip_archive_from_files(file_paths: List[str], output_zip_path: str) -> str:
    """
    Creates a ZIP archive on disk from existing file paths.
    """
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)
    return output_zip_path
