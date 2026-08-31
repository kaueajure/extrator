#!/usr/bin/env python3
"""Gera PNGs em vários tamanhos e .ico a partir de build/assets/icone.png.

Fonte oficial: logo azul WRP do site (public/icone-app.png no repositório WebRP).
"""
from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit("Instale Pillow: pip install pillow") from exc

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "build" / "assets" / "icone.png"
SAIDA_BUILD = RAIZ / "build" / "_icones"
SAIDA_RECURSOS = RAIZ / "src" / "recursos" / "icons"
TAMANHOS = (16, 32, 48, 64, 128, 256, 512)


def redimensionar(imagem: Image.Image, tamanho: int) -> Image.Image:
    rgba = imagem.convert("RGBA")
    if rgba.width == tamanho and rgba.height == tamanho:
        return rgba
    return rgba.resize((tamanho, tamanho), Image.Resampling.LANCZOS)


def main() -> None:
    if not ORIGEM.is_file():
        raise SystemExit(f"Ícone não encontrado: {ORIGEM}")

    SAIDA_BUILD.mkdir(parents=True, exist_ok=True)
    SAIDA_RECURSOS.mkdir(parents=True, exist_ok=True)
    origem = Image.open(ORIGEM)

    for tamanho in TAMANHOS:
        imagem = redimensionar(origem, tamanho)
        for pasta in (SAIDA_BUILD, SAIDA_RECURSOS):
            destino = pasta / f"icone-{tamanho}.png"
            imagem.save(destino, format="PNG")
            print(destino)

    ico_caminho = RAIZ / "build" / "webrp-extrator.ico"
    redimensionar(origem, 256).save(
        ico_caminho,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(ico_caminho)

    # Cópias usadas por .deb / AppImage
    redimensionar(origem, 256).save(SAIDA_BUILD / "webrp-extrator.png", format="PNG")
    redimensionar(origem, 48).save(SAIDA_BUILD / "webrp-extrator-48.png", format="PNG")
    redimensionar(origem, 256).save(SAIDA_RECURSOS / "webrp-extrator.png", format="PNG")


if __name__ == "__main__":
    main()
