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
python -m playwright install chromium --no-shell

echo "==> Gerando ícones do app…"
python -m pip install pillow -q
python build/preparar-icones.py

if [[ "$(uname -s)" == "Linux" ]]; then
  echo "==> Registrando ícone no sistema (barra de tarefas / dock)…"
  RAIZ="$(pwd)"
  ICONES="$RAIZ/src/recursos/icons"
  for tamanho in 16 32 48 64 128 256; do
    mkdir -p "$HOME/.local/share/icons/hicolor/${tamanho}x${tamanho}/apps"
    cp "$ICONES/icone-${tamanho}.png" \
      "$HOME/.local/share/icons/hicolor/${tamanho}x${tamanho}/apps/webrp-extrator.png"
  done
  mkdir -p "$HOME/.local/share/applications"
  cat > "$HOME/.local/share/applications/webrp-extrator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=WebRP Extrator
Comment=Prospecte no Google Maps e importe leads no WebRP
Exec=bash -c "cd '$RAIZ' && exec -a WebRP-Extrator '$RAIZ/.venv/bin/python' '$RAIZ/app.py'"
Path=$RAIZ
Icon=webrp-extrator
Categories=Office;Network;
Terminal=false
StartupWMClass=WebRP-Extrator
EOF
  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
  fi
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  fi
fi

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
