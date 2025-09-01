"""Main application entry point."""

import sys
from pathlib import Path

from app.config.settings import SettingsFactory
from app.factory import create_app

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Verify Python version
if sys.version_info < (3, 11):
    print(f"Error: Python 3.11+ required, got {sys.version}")
    sys.exit(1)

# Create application instance
settings = SettingsFactory.create()
app = create_app(settings)

# For development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # nosec B104 - Development server binding is intentional
        port=8000,
        reload=True if settings.environment == "development" else False,
        log_level=settings.log_level.lower(),
    )
