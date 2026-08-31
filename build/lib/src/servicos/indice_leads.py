from __future__ import annotations

from src.config import banco_configurado
from src.extrator.ids import id_maps, normalizar_url_maps
from src.extrator.modelos import LugarExtraido
from src.servicos.identidade import Correspondencia, normalizar_dominio
from src.servicos.leads_db import (
    IndiceLeadsDB,
    _normalizar_telefone,
    _normalizar_texto,
)
from src.servicos.leads_db import (
    carregar_indice as carregar_indice_db,
)


class IndiceLeadsWebRP:
    """Índice de leads do funil WebRP (API autenticada ou banco em dev)."""

    def __init__(self, indice: IndiceLeadsDB) -> None:
        self._indice = indice

    @classmethod
    def carregar(cls, cliente=None) -> IndiceLeadsWebRP:
        if banco_configurado():
            return cls(carregar_indice_db())
        if cliente is None:
            raise RuntimeError("Cliente WebRP necessário para carregar leads pela API.")
        return cls(_indice_pela_api(cliente))

    def contem_url(self, url: str) -> bool:
        return self._indice.contem_url(url)

    def diagnosticar_url(self, url: str) -> Correspondencia:
        return self._indice.diagnosticar_url(url)

    def contem(self, lugar: LugarExtraido) -> bool:
        return self._indice.contem(lugar)

    def diagnosticar(self, lugar: LugarExtraido) -> Correspondencia:
        return self._indice.diagnosticar(lugar)

    def __len__(self) -> int:
        return len(self._indice)


def _indice_pela_api(cliente) -> IndiceLeadsDB:
    leads = cliente.listar_leads()
    maps_ids: set[str] = set()
    nomes: set[str] = set()
    telefones: set[str] = set()
    dominios: set[str] = set()
    nome_enderecos: set[str] = set()

    for lead in leads:
        maps_id = lead.get("mapsId") or lead.get("maps_id")
        if isinstance(maps_id, str) and maps_id.strip():
            maps_ids.add(maps_id.strip())

        url_maps = lead.get("urlMaps") or lead.get("url_maps")
        if isinstance(url_maps, str) and url_maps.strip():
            maps_ids.add(id_maps(normalizar_url_maps(url_maps)))

        nome = lead.get("nome")
        if isinstance(nome, str) and nome.strip():
            nomes.add(_normalizar_texto(nome))

        telefone = lead.get("telefone")
        if isinstance(telefone, str):
            normalizado = _normalizar_telefone(telefone)
            if len(normalizado) >= 8:
                telefones.add(normalizado)

        site = lead.get("site")
        dominio = normalizar_dominio(site if isinstance(site, str) else "")
        if dominio:
            dominios.add(dominio)

        endereco = lead.get("endereco")
        nome_normalizado = _normalizar_texto(nome if isinstance(nome, str) else "")
        endereco_normalizado = _normalizar_texto(endereco if isinstance(endereco, str) else "")
        if nome_normalizado and endereco_normalizado:
            nome_enderecos.add(f"{nome_normalizado}|{endereco_normalizado}")

    return IndiceLeadsDB(
        maps_ids=maps_ids,
        nomes=nomes,
        telefones=telefones,
        dominios=dominios,
        nome_enderecos=nome_enderecos,
        total=len(leads),
    )
