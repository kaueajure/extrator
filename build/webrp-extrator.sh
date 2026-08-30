#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
export PLAYWRIGHT_BROWSERS_PATH="${DIR}/ms-playwright"
exec "${DIR}/WebRP-Extrator"
