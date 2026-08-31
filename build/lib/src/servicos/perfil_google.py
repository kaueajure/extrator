from __future__ import annotations

import os
import shutil
from pathlib import Path

MARCADOR_SESSAO = ".sessao-google"


def diretorio_perfil() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    raiz = Path(base) if base else Path.home() / ".config"
    return raiz / "webrp-extrator" / "perfil-google"


def perfil_existe() -> bool:
    return diretorio_perfil().exists()


def sessao_marcada() -> bool:
    return (diretorio_perfil() / MARCADOR_SESSAO).exists()


def marcar_sessao_ativa() -> None:
    diretorio = diretorio_perfil()
    diretorio.mkdir(parents=True, exist_ok=True)
    (diretorio / MARCADOR_SESSAO).touch()


def limpar_marcador_sessao() -> None:
    marcador = diretorio_perfil() / MARCADOR_SESSAO
    if marcador.exists():
        marcador.unlink(missing_ok=True)


def limpar_sessao() -> None:
    diretorio = diretorio_perfil()
    if diretorio.exists():
        shutil.rmtree(diretorio, ignore_errors=True)


def texto_status() -> str:
    if sessao_marcada():
        return "Google: sessão salva neste computador"
    if perfil_existe():
        return "Google: perfil criado — faça login de novo (sessão não confirmada)"
    return "Google: não conectado — buscas anônimas têm limite menor"
