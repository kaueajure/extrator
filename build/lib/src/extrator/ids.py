from __future__ import annotations

import hashlib


def normalizar_url_maps(url: str) -> str:
    if url.startswith("/"):
        return f"https://www.google.com{url}"
    return url.split("?")[0]


def id_maps(url: str) -> str:
    normalizada = normalizar_url_maps(url)
    digest = hashlib.sha256(normalizada.encode("utf-8")).hexdigest()
    return digest[:16]
