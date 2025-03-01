"""
Main entry point for LightWave-Server.

This module provides the main entry point for running the LightWave-Server application.
"""

import logging
import sys
import uvicorn

from lightwave.config import settings
from lightwave.utils import setup_logging
from lightwave.api.server import create_app


def main():
    """Run the LightWave-Server application."""
    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Log startup information
    logger.info(f"Starting LightWave-Server v2.0.0")
    logger.info(f"Server settings: host={settings.server.host}, port={settings.server.port}")
    logger.info(f"LED settings: count={settings.led.count}, mode={settings.led.mode}")
    
    try:
        # Run the server
        uvicorn.run(
            "lightwave.api.server:create_app",
            host=settings.server.host,
            port=settings.server.port,
            log_level=settings.server.log_level.value.lower(),
            factory=True,
            reload=settings.server.debug,
        )
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()