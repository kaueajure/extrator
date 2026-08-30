#!/usr/bin/env bash
# Empacota dist/WebRP-Extrator em um AppImage portátil (sem instalação).
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$RAIZ/dist/WebRP-Extrator"
APPDIR="$RAIZ/dist/WebRP-Extrator.AppDir"
SAIDA="$RAIZ/WebRP-Extrator-x86_64.AppImage"
VERSAO="${VERSAO:-1.2.1}"

if [[ ! -d "$DIST" ]]; then
  echo "Pasta dist/WebRP-Extrator não encontrada. Rode o PyInstaller antes."
  exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/share/WebRP-Extrator"
cp -a "$DIST"/. "$APPDIR/usr/share/WebRP-Extrator/"

cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
APP="$HERE/usr/share/WebRP-Extrator"
export PLAYWRIGHT_BROWSERS_PATH="$APP/ms-playwright"
cd "$APP"
exec "$APP/WebRP-Extrator" "$@"
EOF
chmod +x "$APPDIR/AppRun"
chmod +x "$APPDIR/usr/share/WebRP-Extrator/WebRP-Extrator" || true

cat > "$APPDIR/webrp-extrator.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=WebRP Extrator
Exec=WebRP-Extrator
Icon=webrp-extrator
Comment=Prospecte no Google Maps e importe leads no WebRP
Categories=Office;Network;
Terminal=false
EOF

# Ícone mínimo (PNG 1x1 embutido via printf) — AppImage exige um ícone
python3 - <<'PY'
from pathlib import Path
# PNG 48x48 azul simples
import struct, zlib

def chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

w = h = 48
raw = b"".join(b"\x00" + bytes([55, 48, 224, 255]) * w for _ in range(h))
ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
Path("dist/WebRP-Extrator.AppDir/webrp-extrator.png").write_bytes(png)
PY

# appimagetool (sem FUSE na criação)
TOOL="$RAIZ/dist/appimagetool"
if [[ ! -x "$TOOL" ]]; then
  curl -fsSL -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$TOOL"
fi

cd "$RAIZ"
rm -f "$SAIDA"
ARCH=x86_64 VERSION="$VERSAO" APPIMAGE_EXTRACT_AND_RUN=1 \
  "$TOOL" "$APPDIR" "$SAIDA"

chmod +x "$SAIDA"
echo "AppImage gerado: $SAIDA"
ls -lh "$SAIDA"
