from __future__ import annotations

import os
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path

from src.config import VERSAO
from src.servicos.historico_empresas import caminho_banco, estatisticas

LIMITE_LOG = 2 * 1024 * 1024


def pasta_diagnosticos() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        raiz = Path(base) if base else Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        raiz = Path(base) if base else Path.home() / ".local" / "state"
    pasta = raiz / "webrp-extrator"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def caminho_log() -> Path:
    return pasta_diagnosticos() / "extrator.log"


def _rotacionar(caminho: Path) -> None:
    if caminho.exists() and caminho.stat().st_size >= LIMITE_LOG:
        anterior = caminho.with_suffix(".anterior.log")
        anterior.unlink(missing_ok=True)
        caminho.replace(anterior)


def registrar_log(mensagem: str, nivel: str = "INFO") -> None:
    try:
        caminho = caminho_log()
        _rotacionar(caminho)
        momento = datetime.now().astimezone().isoformat(timespec="seconds")
        with caminho.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"{momento} [{nivel}] {mensagem.strip()}\n")
    except OSError:
        pass


def registrar_excecao(tipo, valor, rastreio) -> None:
    detalhe = "".join(traceback.format_exception(tipo, valor, rastreio))
    registrar_log(detalhe, "ERRO")
    sys.__excepthook__(tipo, valor, rastreio)


def relatorio_diagnostico() -> str:
    totais = estatisticas()
    return "\n".join(
        [
            f"WebRP Extrator: {VERSAO}",
            f"Sistema: {platform.platform()}",
            f"Python: {platform.python_version()}",
            f"Empacotado: {'sim' if getattr(sys, 'frozen', False) else 'não'}",
            f"Histórico: {totais['total']} empresa(s)",
            f"Banco local: {caminho_banco()}",
            f"Log: {caminho_log()}",
        ]
    )
