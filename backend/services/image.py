"""
Image Processing Service for white background compositing, format conversion, and validation.
"""
import os
import io
import logging
from PIL import Image, ImageOps, ImageFile

# Allow loading truncated images safely
ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger("bg_remover.services.image")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

def validate_image_file(filename: str, content_type: str, file_size: int):
    """
    Validates file extension, MIME type, and maximum file size (20MB).
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file format '{ext}'. Allowed: JPG, JPEG, PNG, WEBP.")
    
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Invalid content type '{content_type}'. Allowed images only.")
        
    if file_size > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds 20 MB limit ({file_size / (1024*1024):.1f} MB).")

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filename to prevent path traversal and shell safety.
    """
    basename = os.path.basename(filename)
    # Remove potentially dangerous characters
    cleaned = "".join(c for c in basename if c.isalnum() or c in ("-", "_", "."))
    if not cleaned:
        cleaned = "image.jpg"
    return cleaned

def generate_output_filename(original_filename: str, output_format: str = "jpg") -> str:
    """
    Generates output filename preserving original filename.
    Example: IMG_1023.jpg -> IMG_1023.jpg
    """
    base_name, original_ext = os.path.splitext(sanitize_filename(original_filename))
    if output_format.lower() in ("jpg", "jpeg"):
        ext = "jpg"
    elif output_format.lower() == "png":
        ext = "png"
    else:
        ext = original_ext.lstrip(".") or "jpg"
    return f"{base_name}.{ext}"

def create_white_background_image(rgba_img: Image.Image, output_format: str = "jpg", quality: int = 95) -> Image.Image:
    """
    Composites RGBA foreground onto a pure white background (#FFFFFF) preserving aspect ratio and original resolution.
    """
    # Ensure image is in RGBA mode
    if rgba_img.mode != "RGBA":
        rgba_img = rgba_img.convert("RGBA")

    width, height = rgba_img.size
    
    # Create pure white background canvas matching image size
    white_bg = Image.new("RGB", (width, height), (255, 255, 255))
    
    # Split alpha channel to use as mask
    alpha_channel = rgba_img.split()[3]
    
    # Paste RGBA image onto white background using alpha mask
    white_bg.paste(rgba_img, (0, 0), mask=alpha_channel)
    
    return white_bg

def create_thumbnail(img: Image.Image, max_size: tuple = (300, 300)) -> Image.Image:
    """
    Creates a high-quality thumbnail preview image.
    """
    thumb = img.copy()
    thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
    return thumb
