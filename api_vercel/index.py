import sys
from pathlib import Path

# Add parent directory to path so we can import api module
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app

# Export for Vercel
handler = app
