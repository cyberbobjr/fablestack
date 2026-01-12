# Copyright (c) 2026 Benjamin Marchand
# Licensed under the PolyForm Noncommercial License 1.0.0
# back/app.py
import logfire
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from pathlib import Path
from back.di import configure_injector
from back.routers import (auth, characters, creation, gamesession, scenarios,
                          translation, user, users)
from back.utils.exceptions import InternalServerError

app = FastAPI(title="FableStack - AI-Assisted RPG")

def scrubbing_callback(m: logfire.ScrubMatch):
    return m.value

logfire.configure(scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback),environment='dev')
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()

configure_injector(app)

@app.exception_handler(InternalServerError)
async def internal_server_error_handler(request: Request, exc: InternalServerError):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

# CORS configuration (kept for potential future frontend/dev tools)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"],  # Common dev ports
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Routers REST
app.include_router(characters.router, prefix="/api/characters")
app.include_router(scenarios.router,  prefix="/api/scenarios")
app.include_router(creation.router,   prefix="/api/creation")
app.include_router(gamesession.router, prefix="/api/gamesession")
app.include_router(user.router, prefix="/api/user")
app.include_router(users.router, prefix="/api/users")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(translation.router, prefix="/api/translation")

# Add Swagger documentation
@app.get("/openapi.json", include_in_schema=False)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="FableStack - AI-Assisted RPG",
        version="1.0.0",
        description="API for an AI-assisted RPG game.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

import os

from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Mount static files (Backend)
# Must be done BEFORE the SPA catch-all
# project_root is defined later for frontend, but we need it here for backend static
project_root_back = Path(__file__).resolve().parent
static_dir = project_root_back / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Serve Static Files (Frontend) if available
# This assumes the frontend is built to ../front/dist relative to back/app.py
project_root = project_root_back.parent
frontend_dist = project_root / "front" / "dist"

if os.path.exists(frontend_dist):
    # Mount assets
    assets_path = frontend_dist / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

    # Catch-all for SPA
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # API routes are already handled above by precedence
        
        # Check if a file exists in the dist folder (e.g. favicon.ico, manifest.json)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
             return FileResponse(str(file_path))
             
        # Otherwise serve index.html
        return FileResponse(str(frontend_dist / "index.html"))
