from __future__ import annotations

import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.extrator.ids import id_maps, normalizar_url_maps
from src.extrator.modelos import LugarExtraido
from src.servicos.identidade import (
    chave_empresa,
    maps_id_do_lugar,
    normalizar_dominio,
    normalizar_telefone,
    normalizar_texto,
)

STATUS_VALIDOS = {"encontrada", "extraida", "importada", "duplicada", "descartada", "falha"}
POLITICAS_CONTINUACAO = {"todas", "importadas", "recentes30"}


@dataclass(frozen=True)
class RegistroHistorico:
    chave: str
    maps_id: str
    url_maps: str
    nome: str
    telefone: str
    site: str
    endereco: str
    consulta: str
    local: str
    status: str
    motivo: str
    primeira_vista: str
    ultima_vista: str
    importado_em: str
    ocorrencias: int


def _pasta_dados() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        raiz = Path(base) if base else Path.home() / "AppData" / "Local"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        raiz = Path(base) if base else Path.home() / ".local" / "share"
    pasta = raiz / "webrp-extrator"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def caminho_banco() -> Path:
    sobrescrito = os.environ.get("WEBRP_HISTORICO_PATH")
    return Path(sobrescrito) if sobrescrito else _pasta_dados() / "historico.sqlite3"


def _conexao() -> sqlite3.Connection:
    caminho = caminho_banco()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA journal_mode=WAL")
    conexao.execute("PRAGMA busy_timeout=10000")
    _criar_schema(conexao)
    return conexao


def _criar_schema(conexao: sqlite3.Connection) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS empresas (
            chave TEXT PRIMARY KEY,
            maps_id TEXT NOT NULL DEFAULT '',
            url_maps TEXT NOT NULL DEFAULT '',
            nome TEXT NOT NULL DEFAULT '',
            nome_normalizado TEXT NOT NULL DEFAULT '',
            telefone TEXT NOT NULL DEFAULT '',
            dominio TEXT NOT NULL DEFAULT '',
            endereco TEXT NOT NULL DEFAULT '',
            endereco_normalizado TEXT NOT NULL DEFAULT '',
            consulta TEXT NOT NULL DEFAULT '',
            local TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            motivo TEXT NOT NULL DEFAULT '',
            primeira_vista TEXT NOT NULL,
            ultima_vista TEXT NOT NULL,
            importado_em TEXT NOT NULL DEFAULT '',
            ocorrencias INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_empresas_maps_id ON empresas(maps_id);
        CREATE INDEX IF NOT EXISTS idx_empresas_telefone ON empresas(telefone);
        CREATE INDEX IF NOT EXISTS idx_empresas_dominio ON empresas(dominio);
        CREATE INDEX IF NOT EXISTS idx_empresas_busca ON empresas(consulta, local);
        CREATE INDEX IF NOT EXISTS idx_empresas_status ON empresas(status);
        CREATE TABLE IF NOT EXISTS buscas_empresas (
            chave TEXT NOT NULL,
            consulta TEXT NOT NULL,
            local TEXT NOT NULL,
            url_maps TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            primeira_vista TEXT NOT NULL,
            ultima_vista TEXT NOT NULL,
            PRIMARY KEY (chave, consulta, local)
        );
        CREATE INDEX IF NOT EXISTS idx_buscas_empresas_busca
            ON buscas_empresas(consulta, local, status, ultima_vista);
        """
    )


def _agora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def registrar_lugar(
    lugar: LugarExtraido,
    consulta: str,
    local: str,
    status: str = "extraida",
    motivo: str = "",
) -> str:
    if status not in STATUS_VALIDOS:
        raise ValueError(f"Status de histórico inválido: {status}")
    agora = _agora()
    chave = chave_empresa(lugar)
    maps_id = maps_id_do_lugar(lugar)
    url = normalizar_url_maps(lugar.url_referencia) if lugar.url_referencia else ""
    importado_em = agora if status == "importada" else ""
    valores = {
        "chave": chave,
        "maps_id": maps_id,
        "url_maps": url,
        "nome": lugar.nome.strip(),
        "nome_normalizado": normalizar_texto(lugar.nome),
        "telefone": normalizar_telefone(lugar.telefone),
        "dominio": normalizar_dominio(lugar.site),
        "endereco": (lugar.endereco or "").strip(),
        "endereco_normalizado": normalizar_texto(lugar.endereco),
        "consulta": consulta.strip(),
        "local": local.strip(),
        "status": status,
        "motivo": motivo.strip(),
        "agora": agora,
        "importado_em": importado_em,
    }
    with _conexao() as conexao:
        conexao.execute(
            """
            INSERT INTO empresas (
                chave, maps_id, url_maps, nome, nome_normalizado, telefone, dominio,
                endereco, endereco_normalizado, consulta, local, status, motivo,
                primeira_vista, ultima_vista, importado_em, ocorrencias
            ) VALUES (
                :chave, :maps_id, :url_maps, :nome, :nome_normalizado, :telefone, :dominio,
                :endereco, :endereco_normalizado, :consulta, :local, :status, :motivo,
                :agora, :agora, :importado_em, 1
            )
            ON CONFLICT(chave) DO UPDATE SET
                maps_id = CASE WHEN excluded.maps_id <> '' THEN excluded.maps_id ELSE empresas.maps_id END,
                url_maps = CASE WHEN excluded.url_maps <> '' THEN excluded.url_maps ELSE empresas.url_maps END,
                nome = CASE WHEN excluded.nome <> '' THEN excluded.nome ELSE empresas.nome END,
                nome_normalizado = CASE WHEN excluded.nome_normalizado <> '' THEN excluded.nome_normalizado ELSE empresas.nome_normalizado END,
                telefone = CASE WHEN excluded.telefone <> '' THEN excluded.telefone ELSE empresas.telefone END,
                dominio = CASE WHEN excluded.dominio <> '' THEN excluded.dominio ELSE empresas.dominio END,
                endereco = CASE WHEN excluded.endereco <> '' THEN excluded.endereco ELSE empresas.endereco END,
                endereco_normalizado = CASE WHEN excluded.endereco_normalizado <> '' THEN excluded.endereco_normalizado ELSE empresas.endereco_normalizado END,
                consulta = excluded.consulta,
                local = excluded.local,
                status = excluded.status,
                motivo = excluded.motivo,
                ultima_vista = excluded.ultima_vista,
                importado_em = CASE WHEN excluded.importado_em <> '' THEN excluded.importado_em ELSE empresas.importado_em END,
                ocorrencias = empresas.ocorrencias + 1
            """,
            valores,
        )
        conexao.execute(
            """
            INSERT INTO buscas_empresas (
                chave, consulta, local, url_maps, status, primeira_vista, ultima_vista
            ) VALUES (:chave, :consulta, :local, :url_maps, :status, :agora, :agora)
            ON CONFLICT(chave, consulta, local) DO UPDATE SET
                url_maps = CASE WHEN excluded.url_maps <> '' THEN excluded.url_maps ELSE buscas_empresas.url_maps END,
                status = excluded.status,
                ultima_vista = excluded.ultima_vista
            """,
            valores,
        )
    return chave


def registrar_url(
    url: str,
    consulta: str,
    local: str,
    status: str = "encontrada",
    motivo: str = "",
) -> str:
    normalizada = normalizar_url_maps(url)
    lugar = LugarExtraido(
        id=id_maps(normalizada),
        nome="",
        url_referencia=normalizada,
    )
    return registrar_lugar(lugar, consulta, local, status, motivo)


def urls_para_ignorar(consulta: str, local: str, politica: str = "todas") -> set[str]:
    if politica not in POLITICAS_CONTINUACAO:
        politica = "todas"
    clausulas = ["consulta = ?", "local = ?", "url_maps <> ''"]
    parametros: list[str] = [consulta.strip(), local.strip()]
    if politica == "importadas":
        clausulas.append("status IN ('importada', 'duplicada')")
    elif politica == "recentes30":
        limite = (datetime.now(UTC) - timedelta(days=30)).isoformat(timespec="seconds")
        clausulas.append("ultima_vista >= ?")
        parametros.append(limite)
    with _conexao() as conexao:
        linhas = conexao.execute(
            f"SELECT url_maps FROM buscas_empresas WHERE {' AND '.join(clausulas)}",
            parametros,
        ).fetchall()
    return {str(linha["url_maps"]) for linha in linhas if linha["url_maps"]}


def listar_historico(status: str = "", limite: int = 300) -> list[RegistroHistorico]:
    limite = max(1, min(limite, 2000))
    consulta = "SELECT * FROM empresas"
    parametros: list[object] = []
    if status in STATUS_VALIDOS:
        consulta += " WHERE status = ?"
        parametros.append(status)
    consulta += " ORDER BY ultima_vista DESC LIMIT ?"
    parametros.append(limite)
    with _conexao() as conexao:
        linhas = conexao.execute(consulta, parametros).fetchall()
    return [
        RegistroHistorico(
            chave=linha["chave"],
            maps_id=linha["maps_id"],
            url_maps=linha["url_maps"],
            nome=linha["nome"],
            telefone=linha["telefone"],
            site=linha["dominio"],
            endereco=linha["endereco"],
            consulta=linha["consulta"],
            local=linha["local"],
            status=linha["status"],
            motivo=linha["motivo"],
            primeira_vista=linha["primeira_vista"],
            ultima_vista=linha["ultima_vista"],
            importado_em=linha["importado_em"],
            ocorrencias=int(linha["ocorrencias"]),
        )
        for linha in linhas
    ]


def estatisticas() -> dict[str, int]:
    totais = {status: 0 for status in STATUS_VALIDOS}
    with _conexao() as conexao:
        linhas = conexao.execute(
            "SELECT status, COUNT(*) AS total FROM empresas GROUP BY status"
        ).fetchall()
        total = conexao.execute("SELECT COUNT(*) FROM empresas").fetchone()[0]
    for linha in linhas:
        totais[str(linha["status"])] = int(linha["total"])
    totais["total"] = int(total)
    return totais


def contagem_busca(consulta: str, local: str) -> int:
    with _conexao() as conexao:
        linha = conexao.execute(
            "SELECT COUNT(*) FROM buscas_empresas WHERE consulta = ? AND local = ?",
            (consulta.strip(), local.strip()),
        ).fetchone()
    return int(linha[0])


def limpar_historico_busca(consulta: str, local: str) -> None:
    with _conexao() as conexao:
        conexao.execute(
            "DELETE FROM buscas_empresas WHERE consulta = ? AND local = ?",
            (consulta.strip(), local.strip()),
        )


def limpar_historico() -> None:
    with _conexao() as conexao:
        conexao.execute("DELETE FROM buscas_empresas")
        conexao.execute("DELETE FROM empresas")


def registro_para_dict(registro: RegistroHistorico) -> dict:
    return asdict(registro)
