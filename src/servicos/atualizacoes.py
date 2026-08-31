from __future__ import annotations

from dataclasses import dataclass

import httpx

from src.config import VERSAO

URL_RELEASES = "https://api.github.com/repos/kaueajure/extrator/releases/latest"


@dataclass(frozen=True)
class AtualizacaoDisponivel:
    versao_atual: str
    versao_nova: str
    url: str
    disponivel: bool


def _partes_versao(valor: str) -> tuple[int, ...]:
    texto = valor.strip().lower().removeprefix("v")
    partes: list[int] = []
    for parte in texto.split("."):
        numero = "".join(car for car in parte if car.isdigit())
        partes.append(int(numero or 0))
    return tuple(partes)


def _interpretar(dados: dict) -> tuple[str, str]:
    versao = str(
        dados.get("versao")
        or dados.get("version")
        or dados.get("tag_name")
        or ""
    ).strip()
    url = str(
        dados.get("url_download")
        or dados.get("download_url")
        or dados.get("html_url")
        or ""
    ).strip()
    return versao.removeprefix("v"), url


def verificar_atualizacao(base_url: str) -> AtualizacaoDisponivel:
    endpoints = [f"{base_url.rstrip('/')}/api/extrator/versao", URL_RELEASES]
    erros: list[str] = []
    with httpx.Client(timeout=8.0, follow_redirects=True) as cliente:
        for endpoint in endpoints:
            try:
                resposta = cliente.get(endpoint, headers={"Accept": "application/json"})
                if resposta.status_code != 200:
                    erros.append(f"{resposta.status_code} em {endpoint}")
                    continue
                dados = resposta.json()
                if not isinstance(dados, dict):
                    continue
                versao, url = _interpretar(dados)
                if not versao:
                    continue
                return AtualizacaoDisponivel(
                    versao_atual=VERSAO,
                    versao_nova=versao,
                    url=url,
                    disponivel=_partes_versao(versao) > _partes_versao(VERSAO),
                )
            except (httpx.HTTPError, ValueError) as erro:
                erros.append(str(erro))
    detalhe = "; ".join(erros[-2:])
    raise RuntimeError(f"Não foi possível consultar atualizações. {detalhe}".strip())
