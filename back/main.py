# Copyright (c) 2026 Benjamin Marchand
# Licensed under the PolyForm Noncommercial License 1.0.0
import sys
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH pour permettre l'import du module back
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi.staticfiles import StaticFiles

from back.app import app

# Static files are mounted in back/app.py to ensure correct order with SPA catch-all

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
