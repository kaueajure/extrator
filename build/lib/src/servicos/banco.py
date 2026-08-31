from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import pymysql
import pymysql.cursors

from src.config import configuracao_banco, banco_configurado


@dataclass(frozen=True)
class ConfigBanco:
    host: str
    port: int
    user: str
    password: str
    database: str


def obter_config_banco() -> ConfigBanco | None:
    if not banco_configurado():
        return None
    dados = configuracao_banco()
    return ConfigBanco(
        host=dados["host"],
        port=dados["port"],
        user=dados["user"],
        password=dados["password"],
        database=dados["database"],
    )


@contextmanager
def conexao() -> Iterator[pymysql.connections.Connection]:
    config = obter_config_banco()
    if config is None:
        raise RuntimeError("Banco de dados não configurado. Defina DB_HOST, DB_USER, DB_PASSWORD e DB_NAME no .env.")
    conn = pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
