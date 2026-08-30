from __future__ import annotations

from src.extrator.modelos import LugarExtraido
from src.servicos.leads_db import IndiceLeadsDB, carregar_indice as carregar_indice_db


class IndiceLeadsWebRP:
    """Índice de leads carregado diretamente do banco MySQL do WebRP."""

    def __init__(self, indice: IndiceLeadsDB) -> None:
        self._indice = indice

    @classmethod
    def carregar(cls, _cliente=None) -> IndiceLeadsWebRP:
        return cls(carregar_indice_db())

    def contem_url(self, url: str) -> bool:
        return self._indice.contem_url(url)

    def contem(self, lugar: LugarExtraido) -> bool:
        return self._indice.contem(lugar)

    def __len__(self) -> int:
        return len(self._indice)
