from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import urlparse

from src.extrator.ids import id_maps, normalizar_url_maps
from src.extrator.modelos import LugarExtraido

DOMINIOS_GENERICOS = {
    "facebook.com",
    "instagram.com",
    "linktr.ee",
    "wa.me",
    "whatsapp.com",
}


def normalizar_texto(valor: str | None) -> str:
    texto = unicodedata.normalize("NFKD", (valor or "").lower())
    texto = "".join(car for car in texto if not unicodedata.combining(car))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def normalizar_telefone(valor: str | None) -> str:
    digitos = re.sub(r"\D", "", valor or "")
    return digitos[-11:] if len(digitos) >= 8 else ""


def normalizar_dominio(valor: str | None) -> str:
    texto = (valor or "").strip().lower()
    if not texto:
        return ""
    if "://" not in texto:
        texto = f"https://{texto}"
    dominio = (urlparse(texto).hostname or "").removeprefix("www.")
    return "" if dominio in DOMINIOS_GENERICOS else dominio


def maps_id_do_lugar(lugar: LugarExtraido) -> str:
    if lugar.id:
        return lugar.id.strip()
    if lugar.url_referencia:
        return id_maps(normalizar_url_maps(lugar.url_referencia))
    return ""


def chave_empresa(lugar: LugarExtraido) -> str:
    maps_id = maps_id_do_lugar(lugar)
    if maps_id:
        return f"maps:{maps_id}"
    telefone = normalizar_telefone(lugar.telefone)
    if telefone:
        return f"tel:{telefone}"
    dominio = normalizar_dominio(lugar.site)
    if dominio:
        return f"site:{dominio}"
    nome = normalizar_texto(lugar.nome)
    endereco = normalizar_texto(lugar.endereco)
    return f"nome:{nome}|{endereco}"


@dataclass(frozen=True)
class Correspondencia:
    duplicado: bool
    motivo: str = ""
    confianca: float = 0.0
    apenas_alerta: bool = False


@dataclass
class IndiceIdentidades:
    maps_ids: set[str]
    nomes: set[str]
    telefones: set[str]
    dominios: set[str]
    nome_enderecos: set[str]

    def avaliar_url(self, url: str) -> Correspondencia:
        chave = id_maps(normalizar_url_maps(url))
        if chave in self.maps_ids:
            return Correspondencia(True, "mesmo ID/URL do Google Maps", 1.0)
        return Correspondencia(False)

    def avaliar(self, lugar: LugarExtraido) -> Correspondencia:
        maps_id = maps_id_do_lugar(lugar)
        if maps_id and maps_id in self.maps_ids:
            return Correspondencia(True, "mesmo ID do Google Maps", 1.0)

        telefone = normalizar_telefone(lugar.telefone)
        if telefone and telefone in self.telefones:
            return Correspondencia(True, "mesmo telefone", 0.99)

        dominio = normalizar_dominio(lugar.site)
        if dominio and dominio in self.dominios:
            return Correspondencia(True, "mesmo domínio do site", 0.98)

        nome = normalizar_texto(lugar.nome)
        endereco = normalizar_texto(lugar.endereco)
        composto = f"{nome}|{endereco}" if nome and endereco else ""
        if composto and composto in self.nome_enderecos:
            return Correspondencia(True, "mesmo nome e endereço", 0.97)

        if nome and nome in self.nomes:
            return Correspondencia(
                False,
                "nome igual a um lead, mas sem outro identificador",
                0.70,
                apenas_alerta=True,
            )

        if nome and self.nomes:
            melhor = max(
                (SequenceMatcher(None, nome, existente).ratio() for existente in self.nomes),
                default=0.0,
            )
            if melhor >= 0.94:
                return Correspondencia(
                    False,
                    "nome muito parecido com um lead",
                    melhor,
                    apenas_alerta=True,
                )
        return Correspondencia(False)
