# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

raiz = Path(SPECPATH).parent

a = Analysis(
    [str(raiz / "app.py")],
    pathex=[str(raiz)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "src.ui.app",
        "src.ui.login",
        "src.ui.principal",
        "src.ui.workers",
        "src.ui.tema",
        "src.servicos.webrp",
        "src.servicos.sugestoes",
        "src.servicos.sessao",
        "src.extrator.maps",
        "src.extrator.modelos",
        "src.extrator.score",
        "src.config",
        "playwright",
        "keyring.backends",
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
