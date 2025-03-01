# LightWave-Server Development Guide

## Commands
- Run server: `uvicorn main:app --host 0.0.0.0 --port 8080`
- Debug mode: `uvicorn main:app --host 0.0.0.0 --port 8080 --reload`
- Install dependencies: `pip install -r requirements.txt`
- Lint code: `ruff check .`
- Format code: `black .`

## Code Style
- Follow PEP 8 conventions
- Use type hints for function parameters and return values
- Document classes and functions with docstrings
- Max line length: 88 characters
- Imports: standard library first, then third-party, then local
- Thread-based implementation for effects inheriting from EffectBase
- Effect classes should have descriptive docstrings

## Error Handling
- Use HTTPException with appropriate status codes for API errors
- Return consistent JSON error responses
- Validate input parameters with Pydantic models

## API Development
- New endpoints should follow RESTful conventions
- Document API endpoints with docstrings
- Use FastAPI parameter validation and typing