"""
Background Removal Service using rembg with model caching and session management.
"""
import io
import logging
from typing import Optional
from PIL import Image
from rembg import remove, new_session

logger = logging.getLogger("bg_remover.services.background")

# Global session cache dictionary for fast multi-model inference
_SESSIONS = {}

AVAILABLE_MODELS = {
    "u2net": "U2Net (Default - High Quality General)",
    "u2netp": "U2NetP (Lightweight & Fast)",
    "isnet-general-use": "IS-Net (High Precision Edge Detection)",
    "silueta": "Silueta (Fast & Compact for Humans/Objects)",
}

def get_session(model_name: str = "u2net"):
    """
    Returns a cached rembg session for the requested model name.
    """
    global _SESSIONS
    if model_name not in AVAILABLE_MODELS:
        model_name = "u2net"
        
    if model_name not in _SESSIONS:
        try:
            logger.info(f"Initializing rembg session with model '{model_name}'...")
            _SESSIONS[model_name] = new_session(model_name)
        except Exception as e:
            logger.warning(f"Could not pre-initialize rembg session for '{model_name}': {e}. Falling back to default remove.")
            return None
            
    return _SESSIONS.get(model_name)

def remove_background(
    image: Image.Image,
    model_name: str = "u2net",
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10
) -> Image.Image:
    """
    Removes background from a PIL Image and returns an RGBA PIL Image with transparent background.
    """
    try:
        # Convert image to bytes buffer
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        
        session = get_session(model_name)
        
        kwargs = {}
        if session:
            kwargs["session"] = session
            
        if alpha_matting:
            kwargs["alpha_matting"] = True
            kwargs["alpha_matting_foreground_threshold"] = alpha_matting_foreground_threshold
            kwargs["alpha_matting_background_threshold"] = alpha_matting_background_threshold
            kwargs["alpha_matting_erode_size"] = alpha_matting_erode_size
            
        output_bytes = remove(image_bytes, **kwargs)
        result_img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        return result_img
    except Exception as e:
        logger.error(f"Error during background removal: {e}", exc_info=True)
        raise RuntimeError(f"Background removal failed: {str(e)}")
