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

echo "==> Chromium do Playwright (pasta ms-playwright)…"
mkdir -p dist/WebRP-Extrator/ms-playwright
PLAYWRIGHT_BROWSERS_PATH="$PWD/dist/WebRP-Extrator/ms-playwright" \
  python -m playwright install chromium --no-shell

cp build/webrp-extrator.sh dist/WebRP-Extrator/
chmod +x dist/WebRP-Extrator/webrp-extrator.sh
cp build/LEIA-ME-LINUX.txt dist/WebRP-Extrator/
cp .env.example dist/WebRP-Extrator/ 2>/dev/null || true

echo ""
echo "Build concluído: dist/WebRP-Extrator/"
echo "Execute: dist/WebRP-Extrator/webrp-extrator.sh"
