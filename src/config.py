from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

VERSAO = "1.2.0"
LIMITE_MAXIMO_RESULTADOS = 100
URL_PRODUCAO = "https://webriopreto.com"


def empacotado() -> bool:
    """True quando roda pelo PyInstaller (instalador / build)."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def diretorio_app() -> Path:
    if empacotado():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def preparar_ambiente() -> None:
    """Ajusta caminhos do Chromium e carrega .env só em desenvolvimento."""
    raiz = diretorio_app()
    browsers = raiz / "ms-playwright"
    if browsers.is_dir():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers))

    if not empacotado():
        load_dotenv(raiz / ".env")


preparar_ambiente()


def texto_env(nome: str, padrao: str = "") -> str:
    valor = os.getenv(nome, padrao)
    return valor.strip() if valor else padrao


def webrp_url_padrao() -> str:
    if empacotado():
        return URL_PRODUCAO
    return texto_env("WEBRP_URL", URL_PRODUCAO).rstrip("/")


def credenciais_env() -> tuple[str, str]:
    return texto_env("WEBRP_EMAIL"), texto_env("WEBRP_SENHA")


def chave_gemini() -> str | None:
    valor = texto_env("GEMINI_API_KEY")
    return valor or None


def modelo_gemini() -> str:
    return texto_env("GEMINI_MODEL", "gemini-2.0-flash")


def configuracao_banco() -> dict[str, str | int]:
    return {
        "host": texto_env("DB_HOST"),
        "port": int(texto_env("DB_PORT", "3306") or "3306"),
        "user": texto_env("DB_USER"),
        "password": texto_env("DB_PASSWORD"),
        "database": texto_env("DB_NAME"),
    }


def banco_configurado() -> bool:
    """Banco direto só em desenvolvimento com .env — o app empacotado usa a API."""
    if empacotado():
        return False
    dados = configuracao_banco()
    return all(str(dados[chave]).strip() for chave in ("host", "user", "password", "database"))
