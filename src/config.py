import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

VERSAO = "1.1.0"
LIMITE_MAXIMO_RESULTADOS = 100


def texto_env(nome: str, padrao: str = "") -> str:
    valor = os.getenv(nome, padrao)
    return valor.strip() if valor else padrao


def webrp_url_padrao() -> str:
    return texto_env("WEBRP_URL", "https://webriopreto.com").rstrip("/")


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
    dados = configuracao_banco()
    return all(str(dados[chave]).strip() for chave in ("host", "user", "password", "database"))
