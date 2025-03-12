import os
import urllib.request
from app.core.logger import get_logger

logger = get_logger(__name__)

FONT_URLS = {
    'Roboto-Regular.ttf': 'https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Regular.ttf',
    'Roboto-Bold.ttf': 'https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf'
}

FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')

def ensure_fonts_exist():
    """Ensure required fonts are available"""
    os.makedirs(FONTS_DIR, exist_ok=True)
    
    for font_name, url in FONT_URLS.items():
        font_path = os.path.join(FONTS_DIR, font_name)
        if not os.path.exists(font_path):
            try:
                logger.info(f"Downloading font: {font_name}")
                urllib.request.urlretrieve(url, font_path)
                logger.info(f"Successfully downloaded: {font_name}")
            except Exception as e:
                logger.error(f"Error downloading font {font_name}: {str(e)}")
                raise
