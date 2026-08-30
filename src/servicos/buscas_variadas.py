from __future__ import annotations

import hashlib

from src.servicos.sessao import _armazenar, _ler

CHAVE_PROGRESSO = "progresso_buscas"
CHAVE_HISTORICO_BUSCAS = "historico_buscas_variadas"

VARIANTES_LOCAIS = (
    "centro",
    "zona norte",
    "zona sul",
    "bairros",
)


def chave_busca(consulta: str, local: str) -> str:
    base = f"{consulta.strip().lower()}|{local.strip().lower()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]


def _ler_mapa(chave: str) -> dict:
    dados = _ler(chave)
    return dados if isinstance(dados, dict) else {}


def ler_urls_processadas(consulta: str, local: str) -> set[str]:
    mapa = _ler_mapa(CHAVE_PROGRESSO)
    entrada = mapa.get(chave_busca(consulta, local), {})
    urls = entrada.get("urls", [])
    if not isinstance(urls, list):
        return set()
    return {str(item) for item in urls if item}


def salvar_urls_processadas(consulta: str, local: str, urls: set[str]) -> None:
    if not urls:
        return
    mapa = _ler_mapa(CHAVE_PROGRESSO)
    chave = chave_busca(consulta, local)
    existentes = set(ler_urls_processadas(consulta, local))
    existentes.update(urls)
    mapa[chave] = {
        "consulta": consulta.strip(),
        "local": local.strip(),
        "urls": sorted(existentes),
        "total": len(existentes),
    }
    _armazenar(CHAVE_PROGRESSO, mapa)


def limpar_progresso_busca(consulta: str, local: str) -> None:
    mapa = _ler_mapa(CHAVE_PROGRESSO)
    mapa.pop(chave_busca(consulta, local), None)
    _armazenar(CHAVE_PROGRESSO, mapa)


def contagem_progresso(consulta: str, local: str) -> int:
    return len(ler_urls_processadas(consulta, local))


def ler_historico_buscas(local: str) -> list[str]:
    mapa = _ler_mapa(CHAVE_HISTORICO_BUSCAS)
    chave = local.strip().lower()
    historico = mapa.get(chave, [])
    if not isinstance(historico, list):
        return []
    return [str(item) for item in historico if item]


def registrar_busca_usada(consulta: str, local: str) -> None:
    termo = consulta.strip()
    if len(termo) < 2:
        return
    mapa = _ler_mapa(CHAVE_HISTORICO_BUSCAS)
    chave = local.strip().lower()
    historico = ler_historico_buscas(local)
    if termo.lower() not in {item.lower() for item in historico}:
        historico.append(termo)
    mapa[chave] = historico[-40:]
    _armazenar(CHAVE_HISTORICO_BUSCAS, mapa)


def _variantes_locais(consulta: str, local: str) -> list[str]:
    cidade = local.split(",")[0].strip()
    if len(cidade) < 3:
        return []
    opcoes: list[str] = []
    for sufixo in VARIANTES_LOCAIS:
        opcoes.append(f"{consulta} {sufixo} {cidade}")
    return opcoes


def listar_opcoes_variadas(consulta: str, local: str) -> list[str]:
    """Variantes locais — sem chamar Gemini (não bloqueia a UI)."""
    from src.servicos.sugestoes import sugestoes_locais_rapidas

    opcoes: list[str] = []
    vistos: set[str] = set()

    def adicionar(termo: str) -> None:
        limpo = termo.strip()
        chave = limpo.lower()
        if len(limpo) < 2 or chave in vistos:
            return
        vistos.add(chave)
        opcoes.append(limpo)

    for item in sugestoes_locais_rapidas(consulta, local):
        adicionar(item)

    for item in _variantes_locais(consulta, local):
        adicionar(item)

    return opcoes

def proxima_busca_variada(consulta: str, local: str) -> str | None:
    historico = {item.lower() for item in ler_historico_buscas(local)}
    historico.add(consulta.strip().lower())
    for opcao in listar_opcoes_variadas(consulta, local):
        if opcao.lower() not in historico:
            return opcao
    return None


def limpar_historico_buscas(local: str) -> None:
    mapa = _ler_mapa(CHAVE_HISTORICO_BUSCAS)
    mapa.pop(local.strip().lower(), None)
    _armazenar(CHAVE_HISTORICO_BUSCAS, mapa)
