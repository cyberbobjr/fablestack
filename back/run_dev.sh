#!/bin/bash

# Script to launch the FastAPI server with live reloading
cd "$(dirname "$0")"
. venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8001