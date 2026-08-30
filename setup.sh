#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> WebRP-Extrator — instalação (rode só uma vez)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Erro: python3 não encontrado."
  echo "Instale com: sudo apt install python3 python3-pip python3-venv"
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  VERSAO=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  echo "Erro: módulo venv indisponível."
  echo "Instale com: sudo apt install python3-venv"
  echo "Ou, se necessário: sudo apt install python${VERSAO}-venv"
  exit 1
fi

if [[ -d .venv ]] && [[ ! -f .venv/bin/activate ]]; then
  echo "==> Removendo ambiente virtual incompleto…"
  rm -rf .venv
fi

if [[ ! -f .venv/bin/activate ]]; then
  echo "==> Criando ambiente virtual…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Instalando dependências Python…"
python -m pip install --upgrade pip
python -m pip install -e .

echo "==> Instalando Chromium do Playwright…"
python -m playwright install chromium

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Arquivo .env criado a partir de .env.example"
fi

echo ""
echo "Instalação concluída."
echo ""
echo "Para usar o extrator, dentro desta pasta digite:"
echo "  ./rodar"
echo ""
echo "Ou, com o ambiente ativo (source .venv/bin/activate):"
echo "  python app.py"
echo ""
echo "Para reinstalar no futuro:"
echo "  ./instalar"
