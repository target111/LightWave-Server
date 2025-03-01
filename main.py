"""
Main entry point for LightWave-Server.

This module provides a simple entry point for running the LightWave-Server application
without having to import the package directly.
"""

import sys
from lightwave.api.server import create_app

# Create the FastAPI application
app = create_app()

if __name__ == "__main__":
    # If run directly, delegate to the package's main entry point
    from lightwave.__main__ import main
    main()