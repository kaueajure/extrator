#!/usr/bin/env python3
"""Gera ícone PNG 48x48 do WebRP Extrator (fundo azul + W simplificado)."""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def gerar_png(caminho: Path, tamanho: int = 48) -> None:
    # Fundo azul #3730e0; W branco simplificado (pixels)
    azul = (55, 48, 224, 255)
    branco = (255, 255, 255, 255)
    px = [[azul for _ in range(tamanho)] for _ in range(tamanho)]

    def pintar(x: int, y: int, cor: tuple[int, int, int, int]) -> None:
        if 0 <= x < tamanho and 0 <= y < tamanho:
            px[y][x] = cor

    # W grosso — coordenadas relativas ao centro
    s = tamanho / 48.0
    pontos_w = [
        (8, 38), (14, 12), (20, 28), (24, 18), (28, 28), (34, 12), (40, 38),
        (36, 38), (30, 22), (24, 32), (18, 22), (12, 38),
    ]
    for x, y in pontos_w:
        for dx in range(int(3 * s)):
            for dy in range(int(3 * s)):
                pintar(int(x * s) + dx, int(y * s) + dy, branco)

    raw = b"".join(b"\x00" + bytes(c for c in linha) for linha in px)
    ihdr = struct.pack(">IIBBBBB", tamanho, tamanho, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(png)


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("webrp-extrator.png")
    gerar_png(destino)
    print(destino)
