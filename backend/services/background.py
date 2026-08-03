"""
Background Removal Service using rembg.
"""
import io
import logging
from PIL import Image
from rembg import remove, new_session

logger = logging.getLogger("bg_remover.services.background")

# Global session instance for faster execution after initial model load
_REMBG_SESSION = None

def get_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        try:
            logger.info("Initializing rembg session (u2net model)...")
            _REMBG_SESSION = new_session("u2net")
        except Exception as e:
            logger.warning(f"Could not pre-initialize rembg session: {e}. Will use default remove call.")
            _REMBG_SESSION = None
    return _REMBG_SESSION

def remove_background(image: Image.Image) -> Image.Image:
    """
    Removes background from a PIL Image and returns an RGBA PIL Image with transparent background.
    """
    try:
        # Convert image to bytes buffer for rembg
        buf = io.BytesIO()
        # Save as PNG to preserve alpha/colors accurately before processing
        image.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        
        session = get_session()
        if session:
            output_bytes = remove(image_bytes, session=session)
        else:
            output_bytes = remove(image_bytes)
            
        result_img = Image.open(io.BytesIO(output_bytes)).convert("RGBA")
        return result_img
    except Exception as e:
        logger.error(f"Error during background removal: {e}", exc_info=True)
        raise RuntimeError(f"Background removal failed: {str(e)}")
