#!/usr/bin/env bash
# Empacota dist/WebRP-Extrator em .deb (Ubuntu/Debian — duplo clique ou apt install).
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$RAIZ/dist/WebRP-Extrator"
STAGING="$RAIZ/dist/deb-root"
VERSAO="${VERSAO:-1.2.6}"
SAIDA="$RAIZ/WebRP-Extrator_amd64.deb"

if [[ ! -d "$DIST" ]]; then
  echo "Pasta dist/WebRP-Extrator não encontrada. Rode o PyInstaller antes."
  exit 1
fi

ICONES="$RAIZ/src/recursos/icons"

if [[ ! -d "$ICONES" ]]; then
  echo "Ícones não encontrados. Rode: python build/preparar-icones.py"
  exit 1
fi

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb não encontrado. Instale: sudo apt install dpkg"
  exit 1
fi

rm -rf "$STAGING"
mkdir -p "$STAGING/DEBIAN"
mkdir -p "$STAGING/opt/WebRP-Extrator"
mkdir -p "$STAGING/usr/bin"
mkdir -p "$STAGING/usr/share/applications"
mkdir -p "$STAGING/usr/share/icons/hicolor"

cp -a "$DIST"/. "$STAGING/opt/WebRP-Extrator/"
chmod +x "$STAGING/opt/WebRP-Extrator/WebRP-Extrator" 2>/dev/null || true
mkdir -p "$STAGING/opt/WebRP-Extrator/recursos/icons"
cp "$ICONES"/*.png "$STAGING/opt/WebRP-Extrator/recursos/icons/"

cat > "$STAGING/usr/bin/WebRP-Extrator" <<'EOF'
#!/bin/bash
APP=/opt/WebRP-Extrator
export PLAYWRIGHT_BROWSERS_PATH="$APP/ms-playwright"
exec "$APP/WebRP-Extrator" "$@"
EOF
chmod 755 "$STAGING/usr/bin/WebRP-Extrator"

cat > "$STAGING/usr/share/applications/webrp-extrator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=WebRP Extrator
Comment=Prospecte no Google Maps e importe leads no WebRP
Exec=WebRP-Extrator
Icon=webrp-extrator
Categories=Office;Network;
Terminal=false
StartupWMClass=WebRP-Extrator
EOF

for tamanho in 16 32 48 64 128 256; do
  mkdir -p "$STAGING/usr/share/icons/hicolor/${tamanho}x${tamanho}/apps"
  cp "$ICONES/icone-${tamanho}.png" \
    "$STAGING/usr/share/icons/hicolor/${tamanho}x${tamanho}/apps/webrp-extrator.png"
done

INSTALLED_KB="$(du -sk "$STAGING/opt/WebRP-Extrator" | awk '{print int($1)}')"

cat > "$STAGING/DEBIAN/control" <<EOF
Package: webrp-extrator
Version: ${VERSAO}
Section: utils
Priority: optional
Architecture: amd64
Installed-Size: ${INSTALLED_KB}
Depends: libxcb-cursor0, libxkbcommon-x11-0, libegl1, libglib2.0-0, libnss3, libnspr4, libatk1.0-0, libatk-bridge2.0-0, libdrm2, libxcomposite1, libxdamage1, libxfixes3, libxrandr2, libgbm1, libasound2
Maintainer: Web Rio Preto <contato@webriopreto.com>
Homepage: https://extrator.webriopreto.com
Description: Extrator de leads do Google Maps para o WebRP
 Prospecta empresas no Google Maps e importa leads no painel WebRP.
 Não requer configuração de .env — basta login de desenvolvedor.
EOF

cat > "$STAGING/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
fi
exit 0
EOF
chmod 755 "$STAGING/DEBIAN/postinst"

cat > "$STAGING/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
fi
exit 0
EOF
chmod 755 "$STAGING/DEBIAN/postrm"

rm -f "$SAIDA"
dpkg-deb --build --root-owner-group "$STAGING" "$SAIDA"
echo "Pacote .deb gerado: $SAIDA"
ls -lh "$SAIDA"
