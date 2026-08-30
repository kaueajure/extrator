#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Garante import do pacote em desenvolvimento
RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Configura Chromium embutido e .env (dev) antes de qualquer UI
from src import config as _config  # noqa: F401, E402
from src.ui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
