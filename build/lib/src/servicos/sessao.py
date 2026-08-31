from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import keyring
import keyring.errors

SERVICO = "webrp-extrator"
CHAVE_CREDENCIAIS = "credenciais"
CHAVE_FILTROS = "filtros"


@dataclass
class CredenciaisSalvas:
    webrp_url: str
    email: str
    senha: str
    lembrar: bool = True


@dataclass
class FiltrosSalvos:
    sem_site: bool = False
    max_avaliacoes: str = ""
    nota_minima: str = ""
    score_minimo: str = ""
    continuar_busca: bool = True
    politica_continuacao: str = "todas"
    cruzar_webrp: bool = True
    busca_variada_auto: bool = True
    usar_perfil_google: bool = True
    consulta: str = ""
    local: str = "São José do Rio Preto, SP, Brasil"
    limite: int = 10
    navegador_visivel: bool = False


def _pasta_local() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    raiz = Path(base) if base else Path.home() / ".config"
    pasta = raiz / "webrp-extrator"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def _arquivo_local(chave: str) -> Path:
    return _pasta_local() / f"{chave}.json"


def _armazenar_local(chave: str, dados: dict) -> None:
    caminho = _arquivo_local(chave)
    caminho.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    caminho.chmod(0o600)


def _ler_local(chave: str) -> dict | None:
    caminho = _arquivo_local(chave)
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _remover_local(chave: str) -> None:
    caminho = _arquivo_local(chave)
    if caminho.exists():
        caminho.unlink()


def _armazenar(chave: str, dados: dict) -> None:
    bruto = json.dumps(dados, ensure_ascii=False)
    try:
        keyring.set_password(SERVICO, chave, bruto)
        _remover_local(chave)
        return
    except (keyring.errors.KeyringError, Exception):
        pass
    _armazenar_local(chave, dados)


def _ler(chave: str) -> dict | None:
    try:
        bruto = keyring.get_password(SERVICO, chave)
        if bruto:
            try:
                return json.loads(bruto)
            except json.JSONDecodeError:
                pass
    except (keyring.errors.KeyringError, Exception):
        pass
    return _ler_local(chave)


def salvar_credenciais(credenciais: CredenciaisSalvas) -> None:
    if credenciais.lembrar:
        _armazenar(CHAVE_CREDENCIAIS, asdict(credenciais))
    else:
        limpar_credenciais()


def ler_credenciais() -> CredenciaisSalvas | None:
    dados = _ler(CHAVE_CREDENCIAIS)
    if not dados:
        return None
    return CredenciaisSalvas(
        webrp_url=str(dados.get("webrp_url", "")),
        email=str(dados.get("email", "")),
        senha=str(dados.get("senha", "")),
        lembrar=bool(dados.get("lembrar", True)),
    )


def limpar_credenciais() -> None:
    try:
        keyring.delete_password(SERVICO, CHAVE_CREDENCIAIS)
    except keyring.errors.PasswordDeleteError:
        pass
    except Exception:
        pass
    _remover_local(CHAVE_CREDENCIAIS)


def salvar_filtros(filtros: FiltrosSalvos) -> None:
    _armazenar(CHAVE_FILTROS, asdict(filtros))


def ler_filtros() -> FiltrosSalvos:
    dados = _ler(CHAVE_FILTROS)
    if not dados:
        return FiltrosSalvos()
    return FiltrosSalvos(
        sem_site=bool(dados.get("sem_site", False)),
        max_avaliacoes=str(dados.get("max_avaliacoes", "")),
        nota_minima=str(dados.get("nota_minima", "")),
        score_minimo=str(dados.get("score_minimo", "")),
        continuar_busca=bool(dados.get("continuar_busca", True)),
        politica_continuacao=str(dados.get("politica_continuacao", "todas")),
        cruzar_webrp=bool(dados.get("cruzar_webrp", True)),
        busca_variada_auto=bool(dados.get("busca_variada_auto", True)),
        usar_perfil_google=bool(dados.get("usar_perfil_google", True)),
        consulta=str(dados.get("consulta", "")),
        local=str(dados.get("local", "São José do Rio Preto, SP, Brasil")),
        limite=int(dados.get("limite", 10) or 10),
        navegador_visivel=bool(dados.get("navegador_visivel", False)),
    )
