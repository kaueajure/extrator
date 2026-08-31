from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from src.config import diretorio_app, empacotado

TAMANHOS = (16, 32, 48, 64, 128, 256, 512)


def _pastas_icones() -> list[Path]:
    if empacotado():
        base = Path(getattr(sys, "_MEIPASS", diretorio_app()))
        interno = base / "_internal" if (base / "_internal").is_dir() else base
        return [
            interno / "recursos" / "icons",
            interno / "assets",
            base / "recursos" / "icons",
            diretorio_app() / "recursos" / "icons",
            diretorio_app() / "icons",
        ]

    raiz = Path(__file__).resolve().parents[2]
    return [
        raiz / "src" / "recursos" / "icons",
        raiz / "build" / "_icones",
        raiz / "build" / "assets",
    ]


def _montar_icone() -> QIcon | None:
    icone = QIcon()

    for pasta in _pastas_icones():
        if not pasta.is_dir():
            continue

        adicionou = False
        for tamanho in TAMANHOS:
            arquivo = pasta / f"icone-{tamanho}.png"
            if not arquivo.is_file():
                continue
            icone.addFile(
                str(arquivo),
                QSize(tamanho, tamanho),
                QIcon.Mode.Normal,
                QIcon.State.Off,
            )
            adicionou = True

        if adicionou:
            return icone if not icone.isNull() else None

        unico = pasta / "icone.png"
        if unico.is_file():
            for tamanho in (32, 48, 256):
                icone.addFile(str(unico), QSize(tamanho, tamanho))
            return icone if not icone.isNull() else None

    return None


_ICONE_CACHE: QIcon | None | bool = False


def icone_app() -> QIcon | None:
    global _ICONE_CACHE
    if _ICONE_CACHE is False:
        _ICONE_CACHE = _montar_icone()
    return _ICONE_CACHE  # type: ignore[return-value]


def aplicar_icone_janela(janela) -> None:
    icone = icone_app()
    if icone is not None:
        janela.setWindowIcon(icone)
