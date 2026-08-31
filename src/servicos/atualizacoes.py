from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlsplit

import httpx

from src.config import VERSAO

URL_RELEASES = "https://api.github.com/repos/kaueajure/extrator/releases/latest"


@dataclass(frozen=True)
class AtualizacaoDisponivel:
    versao_atual: str
    versao_nova: str
    url: str
    disponivel: bool
    download_direto: bool = False
    nome_arquivo: str = ""


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


def _selecionar_asset(dados: dict, plataforma: str | None = None) -> tuple[str, str]:
    plataforma = plataforma or sys.platform
    if plataforma.startswith("win"):
        extensoes = (".exe",)
    elif plataforma.startswith("linux"):
        extensoes = (".deb", ".appimage")
    elif plataforma == "darwin":
        extensoes = (".dmg", ".pkg")
    else:
        extensoes = ()

    assets = dados.get("assets")
    if not isinstance(assets, list):
        return "", ""

    for extensao in extensoes:
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            nome = str(asset.get("name") or "").strip()
            url = str(asset.get("browser_download_url") or "").strip()
            if nome.lower().endswith(extensao) and url:
                return url, nome
    return "", ""


def _nome_download(url: str, nome_sugerido: str = "") -> str:
    nome = nome_sugerido.strip() or Path(unquote(urlsplit(url).path)).name
    nome = re.sub(r"[^A-Za-z0-9._() -]", "_", nome).strip(" .")
    return nome or "WebRP-Extrator-atualizacao"


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
                url_asset, nome_asset = _selecionar_asset(dados)
                url_direta = str(
                    dados.get("url_download") or dados.get("download_url") or ""
                ).strip()
                url_final = url_asset or url_direta or url
                return AtualizacaoDisponivel(
                    versao_atual=VERSAO,
                    versao_nova=versao,
                    url=url_final,
                    disponivel=_partes_versao(versao) > _partes_versao(VERSAO),
                    download_direto=bool(url_asset or url_direta),
                    nome_arquivo=_nome_download(url_final, nome_asset) if url_final else "",
                )
            except (httpx.HTTPError, ValueError) as erro:
                erros.append(str(erro))
    detalhe = "; ".join(erros[-2:])
    raise RuntimeError(f"Não foi possível consultar atualizações. {detalhe}".strip())


def baixar_atualizacao(
    url: str,
    pasta_destino: Path,
    nome_arquivo: str = "",
    callback: Callable[[int, int], None] | None = None,
) -> Path:
    esquema = urlsplit(url).scheme.lower()
    if esquema not in {"http", "https"}:
        raise RuntimeError("O endereço de download da atualização é inválido.")

    pasta_destino.mkdir(parents=True, exist_ok=True)
    nome = _nome_download(url, nome_arquivo)
    destino = pasta_destino / nome
    contador = 2
    while destino.exists():
        destino = pasta_destino / f"{Path(nome).stem} ({contador}){Path(nome).suffix}"
        contador += 1
    temporario = destino.with_name(f"{destino.name}.part")

    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as cliente:
            with cliente.stream("GET", url) as resposta:
                resposta.raise_for_status()
                total = int(resposta.headers.get("content-length") or 0)
                recebido = 0
                with temporario.open("wb") as arquivo:
                    for bloco in resposta.iter_bytes(chunk_size=256 * 1024):
                        arquivo.write(bloco)
                        recebido += len(bloco)
                        if callback:
                            callback(recebido, total)
        temporario.replace(destino)
        if destino.suffix.lower() == ".appimage":
            destino.chmod(destino.stat().st_mode | 0o111)
        return destino
    except Exception:
        temporario.unlink(missing_ok=True)
        raise
