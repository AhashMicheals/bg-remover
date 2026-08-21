"""
Image Processing Service for white background compositing, custom colors,
background image replacement, format conversion, and Streamlit export utilities.
"""
import os
import io
import logging
from typing import Tuple, Optional, Union
from PIL import Image, ImageOps, ImageFile, ImageFilter

ImageFile.LOAD_TRUNCATED_IMAGES = True

logger = logging.getLogger("bg_remover.services.image")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes filename for clean downloading and disk safety.
    """
    basename = os.path.basename(filename)
    cleaned = "".join(c for c in basename if c.isalnum() or c in ("-", "_", "."))
    if not cleaned:
        cleaned = "image.png"
    return cleaned

def generate_output_filename(original_filename: str, output_format: str = "jpg", suffix: str = "_nobg") -> str:
    """
    Generates clean output filename. Example: product.jpg -> product_nobg.jpg
    """
    base_name, _ = os.path.splitext(sanitize_filename(original_filename))
    fmt = output_format.lower()
    if fmt in ("jpg", "jpeg"):
        ext = "jpg"
    elif fmt == "webp":
        ext = "webp"
    else:
        ext = "png"
    return f"{base_name}{suffix}.{ext}"

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Converts '#FFFFFF' or 'FFFFFF' to (255, 255, 255).
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) != 6:
        return (255, 255, 255)
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def apply_background(
    rgba_img: Image.Image,
    bg_mode: str = "white",
    bg_color_hex: str = "#FFFFFF",
    custom_bg_img: Optional[Image.Image] = None,
    edge_feather: int = 0
) -> Image.Image:
    """
    Applies the chosen background mode to a transparent RGBA image.
    Modes:
      - 'transparent': Keeps transparent RGBA
      - 'white': Composites onto pure white (#FFFFFF)
      - 'color': Composites onto user-selected HEX color
      - 'image': Composites foreground onto a custom background image
    """
    if rgba_img.mode != "RGBA":
        rgba_img = rgba_img.convert("RGBA")

    width, height = rgba_img.size

    # Optional subtle edge feathering for smooth cutouts
    if edge_feather > 0:
        r, g, b, alpha = rgba_img.split()
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=edge_feather))
        rgba_img = Image.merge("RGBA", (r, g, b, alpha))

    if bg_mode == "transparent":
        return rgba_img

    alpha_channel = rgba_img.split()[3]

    if bg_mode == "image" and custom_bg_img is not None:
        # Resize custom background to match subject dimensions maintaining aspect fill
        bg = custom_bg_img.copy().convert("RGBA")
        bg = ImageOps.fit(bg, (width, height), method=Image.Resampling.LANCZOS)
        bg.paste(rgba_img, (0, 0), mask=alpha_channel)
        return bg.convert("RGB")

    # Solid color mode or pure white
    if bg_mode == "color":
        rgb_color = hex_to_rgb(bg_color_hex)
    else:  # 'white' default
        rgb_color = (255, 255, 255)

    canvas = Image.new("RGB", (width, height), rgb_color)
    canvas.paste(rgba_img, (0, 0), mask=alpha_channel)
    return canvas

def export_image_to_bytes(
    img: Image.Image,
    output_format: str = "jpg",
    quality: int = 95
) -> Tuple[bytes, str]:
    """
    Exports a PIL image into bytes and returns (bytes_data, mime_type).
    """
    fmt = output_format.lower()
    buf = io.BytesIO()

    if fmt in ("jpg", "jpeg"):
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    elif fmt == "webp":
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")
        img.save(buf, format="WEBP", quality=quality, method=6)
        mime = "image/webp"
    else:  # PNG
        if img.mode != "RGBA" and img.mode != "RGB":
            img = img.convert("RGBA")
        img.save(buf, format="PNG", optimize=True)
        mime = "image/png"

    return buf.getvalue(), mime

def create_thumbnail(img: Image.Image, max_size: tuple = (400, 400)) -> Image.Image:
    """
    Generates a high quality thumbnail.
    """
    thumb = img.copy()
    thumb.thumbnail(max_size, Image.Resampling.LANCZOS)
    return thumb
