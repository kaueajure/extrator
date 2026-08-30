#!/usr/bin/env bash
# Empacota dist/WebRP-Extrator em um instalador .run auto-extraível.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$RAIZ/dist/WebRP-Extrator"
SAIDA="$RAIZ/WebRP-Extrator-Setup.run"
STAGING="$RAIZ/dist/linux-installer"
VERSAO="${VERSAO:-1.2.0}"

if [[ ! -d "$DIST" ]]; then
  echo "Pasta dist/WebRP-Extrator não encontrada. Rode o PyInstaller antes."
  exit 1
fi

rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -a "$DIST" "$STAGING/WebRP-Extrator"

cat > "$STAGING/install.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

DEST="${XDG_DATA_HOME:-$HOME/.local/share}/WebRP-Extrator"
BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

echo "Instalando WebRP Extrator em $DEST …"
mkdir -p "$DEST" "$BIN" "$APPS"
rm -rf "$DEST"
cp -a "$(dirname "$0")/WebRP-Extrator" "$DEST"

# Chromium embutido
export PLAYWRIGHT_BROWSERS_PATH="$DEST/ms-playwright"

cat > "$BIN/webrp-extrator" <<LAUNCHER
#!/usr/bin/env bash
export PLAYWRIGHT_BROWSERS_PATH="$DEST/ms-playwright"
exec "$DEST/WebRP-Extrator" "\$@"
LAUNCHER
chmod +x "$BIN/webrp-extrator" "$DEST/WebRP-Extrator" || true
if [[ -f "$DEST/webrp-extrator.sh" ]]; then
  chmod +x "$DEST/webrp-extrator.sh"
fi

cat > "$APPS/webrp-extrator.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=WebRP Extrator
Comment=Prospecte no Google Maps e importe leads no WebRP
Exec=$BIN/webrp-extrator
Icon=applications-internet
Terminal=false
Categories=Office;Network;
DESKTOP

echo
echo "Instalação concluída (v${VERSAO:-1.2.0})."
echo "  • Menu de aplicativos: WebRP Extrator"
echo "  • Terminal: webrp-extrator"
echo
if command -v gtk-launch >/dev/null 2>&1 || [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  read -r -p "Abrir agora? [S/n] " resp || true
  if [[ "${resp:-S}" =~ ^[SsYy]?$ ]]; then
    nohup "$BIN/webrp-extrator" >/dev/null 2>&1 &
  fi
fi
EOF

# Injeta versão no script
sed -i "s/\${VERSAO:-1.2.0}/$VERSAO/g" "$STAGING/install.sh"
chmod +x "$STAGING/install.sh"

# Arquivo .run: cabeçalho + tar.gz
PAYLOAD="$STAGING/payload.tar.gz"
tar -C "$STAGING" -czf "$PAYLOAD" WebRP-Extrator install.sh

{
  cat <<HEADER
#!/usr/bin/env bash
# WebRP Extrator Setup $VERSAO
set -euo pipefail
TMP="\$(mktemp -d)"
trap 'rm -rf "\$TMP"' EXIT
ARCHIVE_LINE=\$(awk '/^__ARCHIVE_BELOW__$/ { print NR + 1; exit 0; }' "\$0")
tail -n +"\$ARCHIVE_LINE" "\$0" | tar -xz -C "\$TMP"
bash "\$TMP/install.sh"
exit 0
__ARCHIVE_BELOW__
HEADER
  cat "$PAYLOAD"
} > "$SAIDA"

chmod +x "$SAIDA"
echo "Instalador gerado: $SAIDA"
ls -lh "$SAIDA"
