# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

raiz = Path(SPECPATH)
projeto = raiz.parent
icones = projeto / "src" / "recursos" / "icons"
ico = raiz / "webrp-extrator.ico"

datas = []
if icones.is_dir():
    for png in sorted(icones.glob("*.png")):
        datas.append((str(png), "recursos/icons"))

icon_exe = str(ico) if sys.platform == "win32" and ico.is_file() else None

a = Analysis(
    [str(projeto / "app.py")],
    pathex=[str(projeto)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "src.ui.app",
        "src.ui.login",
        "src.ui.principal",
        "src.ui.workers",
        "src.ui.tema",
        "src.ui.icone",
        "src.ui.popup_sugestoes",
        "src.servicos.webrp",
        "src.servicos.sugestoes",
        "src.servicos.sessao",
        "src.servicos.banco",
        "src.servicos.leads_db",
        "src.servicos.indice_leads",
        "src.servicos.buscas_variadas",
        "src.servicos.perfil_google",
        "src.extrator.maps",
        "src.extrator.modelos",
        "src.extrator.score",
        "src.extrator.ids",
        "src.config",
        "playwright",
        "pymysql",
        "keyring.backends",
        "keyring.backends.SecretService",
        "keyring.backends.Windows",
        "keyring.backends.chainer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["fastapi", "uvicorn"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WebRP-Extrator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_exe,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WebRP-Extrator",
)
