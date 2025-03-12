import os
import urllib.request
from app.core.logger import get_logger

logger = get_logger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(__file__))
LOGO_PATH = os.path.join(ASSETS_DIR, 'opal_logo.png')

def ensure_logo_exists():
    """Ensure company logo is available"""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    if not os.path.exists(LOGO_PATH):
        logger.warning(f"Company logo not found at {LOGO_PATH}")
        logger.info("Please place your company logo at this location")
        # Create a placeholder if needed
        create_placeholder_logo()

def create_placeholder_logo():
    """Create a simple placeholder logo if actual logo is not available"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a 200x200 white image
    img = Image.new('RGB', (200, 200), color='white')
    d = ImageDraw.Draw(img)
    
    # Add a simple placeholder text
    d.text((50, 90), 'OPAL', fill=(0, 67, 127))
    
    # Save the placeholder
    img.save(LOGO_PATH)
    logger.info(f"Created placeholder logo at {LOGO_PATH}")
