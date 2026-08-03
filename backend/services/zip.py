"""
ZIP Archive Service for batch downloading processed images.
"""
import os
import zipfile
import logging
from typing import List

logger = logging.getLogger("bg_remover.services.zip")

def create_zip_archive(file_paths: List[str], output_zip_path: str) -> str:
    """
    Creates a ZIP archive containing all specified files.
    """
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)
            else:
                logger.warning(f"File not found for zip packaging: {file_path}")
                
    return output_zip_path
