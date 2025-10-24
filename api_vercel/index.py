import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("VERCEL API HANDLER LOADING")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current file: {__file__}")
logger.info("=" * 50)

# Add parent directory to path so we can import api module
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)
logger.info(f"Added to path: {parent_dir}")

try:
    from api.main import app
    logger.info("Successfully imported FastAPI app")
    logger.info(f"App routes: {[route.path for route in app.routes]}")
except Exception as e:
    logger.error(f"Failed to import app: {e}", exc_info=True)
    raise

# Export for Vercel
handler = app

# Add a test function to verify it's loaded
def hello():
    return {"message": "Vercel API handler loaded successfully"}

logger.info("Handler exported successfully")
