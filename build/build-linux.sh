#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> WebRP-Extrator — build Linux"

if [[ ! -f .venv/bin/activate ]]; then
  echo "Execute ./instalar antes do build."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install pyinstaller

pyinstaller build/webrp-extrator.spec --noconfirm

echo ""
echo "Build concluído: dist/WebRP-Extrator/"
echo "Distribua a pasta dist/WebRP-Extrator (modo onedir)."
echo "Na primeira execução, o Chromium do Playwright deve estar instalado:"
echo "  python -m playwright install chromium"
