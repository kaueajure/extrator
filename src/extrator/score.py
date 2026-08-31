from __future__ import annotations

import math
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from src.extrator.modelos import LugarExtraido

CATEGORIAS_PME_ALTA = (
    "clínica",
    "consultório",
    "odontol",
    "dentista",
    "estética",
    "fisioterapia",
    "nutricion",
    "psicólog",
    "veterinári",
    "pet shop",
    "advocacia",
    "contabilidade",
)

CATEGORIAS_PME_MEDIA = (
    "salão",
    "barbearia",
    "oficina",
    "imobiliária",
    "academia",
    "escola",
    "laboratório",
    "padaria",
    "restaurante",
    "lanchonete",
    "marmita",
)

DOMINIOS_DE_PERFIL = (
    # Redes sociais
    "facebook.com",
    "fb.com",
    "instagram.com",
    "kwai.com",
    "linkedin.com",
    "pinterest.com",
    "snapchat.com",
    "threads.net",
    "tiktok.com",
    "tumblr.com",
    "twitch.tv",
    "twitter.com",
    "x.com",
    "youtube.com",
    "youtu.be",
    # Mensageiros
    "discord.com",
    "discord.gg",
    "t.me",
    "telegram.me",
    "wa.me",
    "whatsapp.com",
    # Páginas que apenas agrupam links e perfis
    "beacons.ai",
    "bio.link",
    "bio.site",
    "campsite.bio",
    "linkbio.co",
    "linktr.ee",
    "milkshake.app",
    "solo.to",
    "taplink.cc",
)


def eh_perfil_social(site: str | None) -> bool:
    """Indica links de perfil ou bio que não representam um site oficial."""
    valor = (site or "").strip().lower()
    if not valor:
        return False

    endereco = valor if "://" in valor else f"//{valor}"
    dominio = (urlsplit(endereco).hostname or "").rstrip(".")
    if dominio.startswith("www."):
        dominio = dominio[4:]

    return any(
        dominio == dominio_perfil or dominio.endswith(f".{dominio_perfil}")
        for dominio_perfil in DOMINIOS_DE_PERFIL
    )


def _pontos_site(lugar: LugarExtraido) -> float:
    site = (lugar.site or "").strip().lower()
    if not site:
        return 24.0
    if eh_perfil_social(site):
        return 16.5
    if site.startswith("http"):
        return 4.0
    return 8.0


def _pontos_telefone(telefone: str | None) -> float:
    digitos = re.sub(r"\D", "", telefone or "")
    if len(digitos) < 8:
        return 0.0
    if len(digitos) >= 11:
        return 14.0
    if len(digitos) >= 10:
        return 11.5
    return 8.0


def _pontos_avaliacoes(avaliacoes: int | None) -> float:
    if avaliacoes is None:
        return 6.0
    if avaliacoes <= 0:
        return 10.0
    if avaliacoes < 15:
        return 18.0
    if avaliacoes < 40:
        return 15.0 - math.log10(avaliacoes + 1) * 2.2
    if avaliacoes < 120:
        return 11.0 - math.log10(avaliacoes) * 1.8
    if avaliacoes < 350:
        return 6.0 - math.log10(avaliacoes / 120) * 2.5
    if avaliacoes < 800:
        return 2.0
    return -4.0 - min(8.0, math.log10(avaliacoes / 800) * 3.0)


def _pontos_nota(nota: float | None) -> float:
    if nota is None:
        return 2.0
    if nota >= 4.85:
        return 8.0
    if nota >= 4.6:
        return 6.5
    if nota >= 4.3:
        return 4.0
    if nota >= 4.0:
        return 1.5
    if nota >= 3.5:
        return -2.0
    return -6.0


def _pontos_categoria(categoria: str | None) -> float:
    texto = (categoria or "").lower()
    if not texto:
        return 3.0
    if any(termo in texto for termo in CATEGORIAS_PME_ALTA):
        return 14.0 + min(4.0, len(texto) / 40)
    if any(termo in texto for termo in CATEGORIAS_PME_MEDIA):
        return 9.0 + min(3.0, len(texto) / 50)
    return 4.0 + min(2.0, len(texto) / 60)


def _pontos_completude(lugar: LugarExtraido) -> float:
    pts = 0.0
    if lugar.endereco and len(lugar.endereco.strip()) > 12:
        pts += 4.0
    if lugar.categoria:
        pts += 2.0
    if lugar.latitude is not None and lugar.longitude is not None:
        pts += 2.5
    nome = lugar.nome.strip()
    if 4 <= len(nome) <= 80:
        pts += 2.0
    return pts


def _pontos_nome(nome: str) -> float:
    texto = nome.lower()
    if any(marca in texto for marca in ("franquia", " rede ", "filial", "matriz")):
        return -5.0
    palavras = len(nome.split())
    if palavras >= 5:
        return -1.5
    if palavras <= 2:
        return 1.5
    return 0.0


def calcular_score(lugar: LugarExtraido) -> int:
    total = (
        12.0
        + _pontos_site(lugar)
        + _pontos_telefone(lugar.telefone)
        + _pontos_avaliacoes(lugar.avaliacoes)
        + _pontos_nota(lugar.nota)
        + _pontos_categoria(lugar.categoria)
        + _pontos_completude(lugar)
        + _pontos_nome(lugar.nome)
    )
    return max(5, min(99, round(total)))


@dataclass
class FiltrosLead:
    sem_site: bool = False
    max_avaliacoes: int | None = None
    nota_minima: float | None = None
    score_minimo: int | None = None

    def passa(self, lugar: LugarExtraido, score: int) -> bool:
        tem_site_oficial = bool((lugar.site or "").strip()) and not eh_perfil_social(lugar.site)
        if self.sem_site and tem_site_oficial:
            return False

        if self.max_avaliacoes is not None:
            total = lugar.avaliacoes if lugar.avaliacoes is not None else 0
            if total >= self.max_avaliacoes:
                return False

        if self.nota_minima is not None:
            if lugar.nota is None or lugar.nota < self.nota_minima:
                return False

        if self.score_minimo is not None and score < self.score_minimo:
            return False

        return True
