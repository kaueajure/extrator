from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from src.config import banco_configurado
from src.extrator.ids import id_maps, normalizar_url_maps
from src.extrator.modelos import LugarExtraido
from src.servicos import leads_db


@dataclass
class ResultadoImportacao:
    nome: str
    sucesso: bool
    mensagem: str
    status: int | None = None


class SessaoExpirada(Exception):
    pass


class ClienteWebRP:
    def __init__(self, base_url: str, email: str = "", senha: str = ""):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.senha = senha
        self.usuario_id: int | None = None
        self.cliente = httpx.Client(timeout=30.0, follow_redirects=True)

    def fechar(self) -> None:
        self.cliente.close()

    def definir_credenciais(self, email: str, senha: str) -> None:
        self.email = email
        self.senha = senha

    def login(self, email: str, senha: str) -> None:
        self.definir_credenciais(email, senha)
        resposta = self.cliente.post(
            f"{self.base_url}/api/admin/login",
            json={"email": email, "senha": senha},
        )
        if resposta.status_code != 200:
            dados = resposta.json() if resposta.content else {}
            mensagem = dados.get("mensagem", "Falha ao autenticar no WebRP.")
            raise RuntimeError(mensagem)
        if banco_configurado():
            self.usuario_id = leads_db.buscar_usuario_id(email)

    def renovar_sessao(self) -> bool:
        if not self.email or not self.senha:
            return False
        try:
            self.login(self.email, self.senha)
            return True
        except (RuntimeError, httpx.HTTPError):
            return False

    def listar_leads(self) -> list[dict]:
        resposta = self._requisitar("GET", f"{self.base_url}/api/admin/leads")
        if resposta.status_code == 401:
            raise SessaoExpirada("Sessão WebRP expirada. Faça login novamente.")
        if resposta.status_code != 200:
            dados = resposta.json() if resposta.content else {}
            mensagem = dados.get("mensagem", "Falha ao listar leads do WebRP.")
            raise RuntimeError(mensagem)
        dados = resposta.json() if resposta.content else {}
        leads = dados.get("leads", [])
        return leads if isinstance(leads, list) else []

    def _requisitar(self, metodo: str, url: str, **kwargs) -> httpx.Response:
        ultimo_erro: httpx.HTTPError | None = None
        resposta: httpx.Response | None = None
        for tentativa in range(1, 4):
            try:
                resposta = self.cliente.request(metodo, url, **kwargs)
            except (httpx.TimeoutException, httpx.NetworkError) as erro:
                ultimo_erro = erro
                if tentativa >= 3:
                    raise
                time.sleep(0.6 * tentativa)
                continue

            if resposta.status_code == 401 and self.email and self.senha:
                if self.renovar_sessao():
                    resposta = self.cliente.request(metodo, url, **kwargs)

            if resposta.status_code == 429 or resposta.status_code >= 500:
                if tentativa < 3:
                    espera = resposta.headers.get("Retry-After")
                    try:
                        segundos = min(float(espera), 5.0) if espera else 0.8 * tentativa
                    except ValueError:
                        segundos = 0.8 * tentativa
                    time.sleep(segundos)
                    continue
            return resposta

        if ultimo_erro:
            raise ultimo_erro
        if resposta is None:
            raise RuntimeError("O WebRP não respondeu após três tentativas.")
        return resposta

    def _montar_lead(self, lugar: LugarExtraido) -> dict:
        observacoes_partes = ["Importado via WebRP-Extrator (Google Maps)."]
        if lugar.score is not None:
            observacoes_partes.append(f"Score do lead: {lugar.score}/100")
        if lugar.url_referencia:
            observacoes_partes.append(f"Maps: {lugar.url_referencia}")
        if lugar.nota is not None:
            linha_nota = f"Nota: {lugar.nota}"
            if lugar.avaliacoes is not None:
                linha_nota += f" ({lugar.avaliacoes} avaliações)"
            observacoes_partes.append(linha_nota)

        maps_id = lugar.id or id_maps(lugar.url_referencia or lugar.nome)
        url_maps = normalizar_url_maps(lugar.url_referencia) if lugar.url_referencia else ""

        return {
            "nome": lugar.nome[:160],
            "contato": "",
            "email": "",
            "telefone": (lugar.telefone or "")[:40],
            "categoria": (lugar.categoria or "")[:120],
            "endereco": (lugar.endereco or "")[:300],
            "site": lugar.site or "",
            "responsavel": "",
            "observacoes": "\n".join(observacoes_partes)[:4000],
            "etapa": "novo",
            "valorEstimado": "",
            "proximoContato": "",
            "origem": "extrator",
            "mapsId": maps_id,
            "urlMaps": url_maps,
            "latitude": lugar.latitude if lugar.latitude is not None else "",
            "longitude": lugar.longitude if lugar.longitude is not None else "",
        }

    def importar_lugar(self, lugar: LugarExtraido) -> ResultadoImportacao:
        if banco_configurado() and self.usuario_id:
            return leads_db.inserir_lead(lugar, self.usuario_id)

        resposta = self._requisitar(
            "POST",
            f"{self.base_url}/api/admin/leads",
            json=self._montar_lead(lugar),
        )
        if resposta.status_code == 401:
            raise SessaoExpirada("Sessão WebRP expirada. Faça login novamente.")
        dados = resposta.json() if resposta.content else {}
        mensagem = dados.get("mensagem", "Resposta sem mensagem.")

        if resposta.status_code == 201:
            return ResultadoImportacao(lugar.nome, True, mensagem, resposta.status_code)
        if resposta.status_code == 409:
            return ResultadoImportacao(lugar.nome, False, mensagem, resposta.status_code)
        return ResultadoImportacao(lugar.nome, False, mensagem, resposta.status_code)

    def importar_lugares(
        self,
        lugares: list[LugarExtraido],
        on_progresso: Callable[[int, int, str], None] | None = None,
        on_resultado: Callable[[LugarExtraido, ResultadoImportacao], None] | None = None,
    ) -> list[ResultadoImportacao]:
        resultados: list[ResultadoImportacao] = []
        total = len(lugares)
        for indice, lugar in enumerate(lugares, start=1):
            resultado = self.importar_lugar(lugar)
            resultados.append(resultado)
            if on_resultado:
                on_resultado(lugar, resultado)
            if on_progresso:
                on_progresso(indice, total, lugar.nome)
        return resultados
