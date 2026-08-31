from __future__ import annotations

from dataclasses import dataclass, field

from src.extrator.ids import id_maps, normalizar_url_maps
from src.extrator.modelos import LugarExtraido
from src.servicos.banco import conexao, obter_config_banco
from src.servicos.identidade import (
    Correspondencia,
    IndiceIdentidades,
    normalizar_dominio,
)
from src.servicos.identidade import (
    normalizar_telefone as _normalizar_telefone,
)
from src.servicos.identidade import (
    normalizar_texto as _normalizar_texto,
)


@dataclass
class IndiceLeadsDB:
    maps_ids: set[str]
    nomes: set[str]
    telefones: set[str]
    dominios: set[str] = field(default_factory=set)
    nome_enderecos: set[str] = field(default_factory=set)
    total: int = 0

    def _identidades(self) -> IndiceIdentidades:
        return IndiceIdentidades(
            maps_ids=self.maps_ids,
            nomes=self.nomes,
            telefones=self.telefones,
            dominios=self.dominios,
            nome_enderecos=self.nome_enderecos,
        )

    def diagnosticar_url(self, url: str) -> Correspondencia:
        return self._identidades().avaliar_url(url)

    def diagnosticar(self, lugar: LugarExtraido) -> Correspondencia:
        return self._identidades().avaliar(lugar)

    def contem_url(self, url: str) -> bool:
        return self.diagnosticar_url(url).duplicado

    def contem(self, lugar: LugarExtraido) -> bool:
        return self.diagnosticar(lugar).duplicado

    def __len__(self) -> int:
        return self.total


def carregar_indice() -> IndiceLeadsDB:
    if obter_config_banco() is None:
        raise RuntimeError("Banco não configurado.")
    maps_ids: set[str] = set()
    nomes: set[str] = set()
    telefones: set[str] = set()
    dominios: set[str] = set()
    nome_enderecos: set[str] = set()
    total = 0
    with conexao() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT maps_id, nome, telefone, endereco, site
                FROM Leads
                WHERE maps_id IS NOT NULL OR nome IS NOT NULL OR telefone IS NOT NULL
                   OR endereco IS NOT NULL OR site IS NOT NULL
                """
            )
            for linha in cur.fetchall():
                total += 1
                maps_id = linha.get("maps_id")
                if isinstance(maps_id, str) and maps_id.strip():
                    maps_ids.add(maps_id.strip())
                nome = linha.get("nome")
                if isinstance(nome, str) and nome.strip():
                    nomes.add(_normalizar_texto(nome))
                telefone = linha.get("telefone")
                if isinstance(telefone, str):
                    normalizado = _normalizar_telefone(telefone)
                    if len(normalizado) >= 8:
                        telefones.add(normalizado)
                dominio = normalizar_dominio(linha.get("site"))
                if dominio:
                    dominios.add(dominio)
                endereco = _normalizar_texto(linha.get("endereco"))
                nome_normalizado = _normalizar_texto(linha.get("nome"))
                if nome_normalizado and endereco:
                    nome_enderecos.add(f"{nome_normalizado}|{endereco}")
    return IndiceLeadsDB(
        maps_ids=maps_ids,
        nomes=nomes,
        telefones=telefones,
        dominios=dominios,
        nome_enderecos=nome_enderecos,
        total=total,
    )


def buscar_usuario_id(email: str) -> int | None:
    with conexao() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM Usuarios WHERE email = %s AND desenvolvedor = 1 LIMIT 1",
                (email.strip().lower(),),
            )
            linha = cur.fetchone()
            if not linha:
                return None
            return int(linha["id"])


def _montar_observacoes(lugar: LugarExtraido) -> str:
    partes = ["Importado via WebRP-Extrator (Google Maps)."]
    if lugar.score is not None:
        partes.append(f"Score do lead: {lugar.score}/100")
    if lugar.url_referencia:
        partes.append(f"Maps: {lugar.url_referencia}")
    if lugar.nota is not None:
        linha = f"Nota: {lugar.nota}"
        if lugar.avaliacoes is not None:
            linha += f" ({lugar.avaliacoes} avaliações)"
        partes.append(linha)
    return "\n".join(partes)[:4000]


def inserir_lead(lugar: LugarExtraido, usuario_id: int):
    from src.servicos.webrp import ResultadoImportacao

    maps_id = lugar.id or id_maps(lugar.url_referencia or lugar.nome)
    url_maps = normalizar_url_maps(lugar.url_referencia) if lugar.url_referencia else None
    try:
        with conexao() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO Leads (
                        nome, contato, email, telefone, categoria, endereco, site, responsavel,
                        observacoes, etapa, valor_estimado, proximo_contato, origem,
                        maps_id, url_maps, latitude, longitude, criado_por
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        lugar.nome[:160],
                        None,
                        None,
                        (lugar.telefone or "")[:40] or None,
                        (lugar.categoria or "")[:120] or None,
                        (lugar.endereco or "")[:300] or None,
                        lugar.site or None,
                        None,
                        _montar_observacoes(lugar),
                        "novo",
                        None,
                        None,
                        "extrator",
                        maps_id,
                        url_maps[:500] if url_maps else None,
                        lugar.latitude,
                        lugar.longitude,
                        usuario_id,
                    ),
                )
                lead_id = cur.lastrowid
                cur.execute(
                    """
                    INSERT INTO Historico (lead_id, etapa_anterior, etapa_nova, usuario_id)
                    VALUES (%s, NULL, %s, %s)
                    """,
                    (lead_id, "novo", usuario_id),
                )
        return ResultadoImportacao(lugar.nome, True, "Lead adicionado ao funil.", 201)
    except Exception as erro:
        codigo = getattr(erro, "args", (None,))[0]
        if codigo == 1062:
            return ResultadoImportacao(lugar.nome, False, "Esta empresa já está no funil.", 409)
        return ResultadoImportacao(lugar.nome, False, str(erro), None)
