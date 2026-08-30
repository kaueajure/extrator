#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.ui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
