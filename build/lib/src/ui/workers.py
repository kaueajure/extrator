from __future__ import annotations

import httpx
from PySide6.QtCore import QThread, Signal

from src.config import banco_configurado
from src.extrator.maps import abrir_login_google, extrair_lugares
from src.extrator.modelos import (
    CaptchaDetectado,
    EventoProcessamento,
    ExtracaoCancelada,
    LugarExtraido,
    ResultadoExtracao,
)
from src.servicos.atualizacoes import verificar_atualizacao
from src.servicos.buscas_variadas import ler_urls_processadas
from src.servicos.historico_empresas import (
    registrar_lugar,
    registrar_url,
    urls_para_ignorar,
)
from src.servicos.indice_leads import IndiceLeadsWebRP
from src.servicos.sugestoes import sugerir_consulta_sync
from src.servicos.webrp import ClienteWebRP, SessaoExpirada


class ExtracaoWorker(QThread):
    log = Signal(str)
    lugar = Signal(object)
    progresso = Signal(int, int)
    concluido = Signal(object)
    cancelado = Signal(object)
    erro = Signal(str)
    evento = Signal(object)

    def __init__(
        self,
        consulta: str,
        local: str,
        limite: int,
        visivel: bool,
        continuar_busca: bool,
        cruzar_webrp: bool,
        usar_perfil_google: bool,
        politica_continuacao: str,
        cliente: ClienteWebRP | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.consulta = consulta
        self.local = local
        self.limite = limite
        self.visivel = visivel
        self.continuar_busca = continuar_busca
        self.cruzar_webrp = cruzar_webrp
        self.usar_perfil_google = usar_perfil_google
        self.politica_continuacao = politica_continuacao
        self.cliente = cliente
        self._cancelar = False
        self._total_links = 0

    def cancelar(self) -> None:
        self._cancelar = True

    def run(self) -> None:
        try:
            def on_log(mensagem: str) -> None:
                self.log.emit(mensagem)
                if mensagem.startswith("Extraindo ") and "/" in mensagem:
                    parte = mensagem.replace("Extraindo ", "").replace("…", "")
                    try:
                        atual, total = parte.split("/", 1)
                        self.progresso.emit(int(atual), int(total))
                    except ValueError:
                        pass

            def on_lugar(lugar: LugarExtraido) -> None:
                self.lugar.emit(lugar)

            def deve_cancelar() -> bool:
                return self._cancelar

            indice: IndiceLeadsWebRP | None = None
            if self.cruzar_webrp:
                if self.cliente is None and not banco_configurado():
                    raise RuntimeError("Faça login no WebRP para cruzar leads com o funil.")
                on_log("Carregando leads do WebRP…")
                indice = IndiceLeadsWebRP.carregar(self.cliente)
                on_log(f"{len(indice)} lead(s) no funil — duplicatas serão ignoradas.")
                if deve_cancelar():
                    on_log("Extração cancelada.")
                    self.cancelado.emit(ResultadoExtracao())
                    return

            ignorar = (
                urls_para_ignorar(self.consulta, self.local, self.politica_continuacao)
                if self.continuar_busca
                else set()
            )
            if self.continuar_busca and self.politica_continuacao == "todas":
                urls_legadas = ler_urls_processadas(self.consulta, self.local)
                for url_legada in urls_legadas - ignorar:
                    registrar_url(
                        url_legada,
                        self.consulta,
                        self.local,
                        "extraida",
                        "Migrada do histórico de versões anteriores",
                    )
                ignorar.update(urls_legadas)

            def ja_existe(lugar: LugarExtraido):
                return indice.diagnosticar(lugar) if indice else None

            def ja_existe_url(url: str):
                return indice.diagnosticar_url(url) if indice else None

            def on_evento(evento: EventoProcessamento) -> None:
                if evento.lugar is not None:
                    registrar_lugar(
                        evento.lugar,
                        self.consulta,
                        self.local,
                        evento.status,
                        evento.motivo,
                    )
                else:
                    registrar_url(
                        evento.url,
                        self.consulta,
                        self.local,
                        evento.status,
                        evento.motivo,
                    )
                self.evento.emit(evento)

            resultado = extrair_lugares(
                self.consulta,
                self.local,
                self.limite,
                self.visivel,
                on_log,
                on_lugar,
                ignorar,
                ja_existe if indice else None,
                ja_existe_url if indice else None,
                self.usar_perfil_google,
                deve_cancelar,
                on_evento,
            )
            if self._cancelar:
                self.cancelado.emit(resultado)
            else:
                self.concluido.emit(resultado)
        except ExtracaoCancelada as erro:
            self.cancelado.emit(erro.resultado)
        except CaptchaDetectado as erro:
            self.erro.emit(
                "Google pediu captcha ou verificação de segurança. "
                "Selecione «Visível» no navegador, resolva o desafio na janela do Chrome "
                "e use «Entrar no Google» se ainda não estiver logado. "
                f"Detalhe: {erro.motivo}"
            )
        except Exception as erro:
            self.erro.emit(str(erro))


class GoogleLoginWorker(QThread):
    log = Signal(str)
    concluido = Signal(bool)
    erro = Signal(str)

    def run(self) -> None:
        try:
            def on_log(mensagem: str) -> None:
                self.log.emit(mensagem)

            logado = abrir_login_google(on_log)
            self.concluido.emit(logado)
        except Exception as erro:
            self.erro.emit(str(erro))


class LoginWorker(QThread):
    concluido = Signal(object, str, str)
    erro = Signal(str)

    def __init__(self, url: str, email: str, senha: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url
        self.email = email
        self.senha = senha

    def run(self) -> None:
        try:
            cliente = ClienteWebRP(self.url, self.email, self.senha)
            cliente.login(self.email, self.senha)
            self.concluido.emit(cliente, self.email, self.url)
        except RuntimeError as erro:
            self.erro.emit(str(erro))
        except httpx.HTTPError:
            self.erro.emit("Não foi possível conectar ao WebRP.")
        except Exception as erro:
            self.erro.emit(str(erro))


class ImportacaoWorker(QThread):
    log = Signal(str)
    progresso = Signal(int, int, str)
    concluido = Signal(str, list)
    erro = Signal(str)

    def __init__(
        self,
        cliente: ClienteWebRP,
        lugares: list[LugarExtraido],
        consulta: str,
        local: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cliente = cliente
        self.lugares = lugares
        self.consulta = consulta
        self.local = local

    def run(self) -> None:
        try:
            def on_progresso(atual: int, total: int, nome: str) -> None:
                self.progresso.emit(atual, total, nome)
                self.log.emit(f"Importando {atual}/{total}: {nome}")

            def on_resultado(lugar: LugarExtraido, resultado) -> None:
                if resultado.sucesso:
                    status = "importada"
                elif resultado.status == 409:
                    status = "duplicada"
                else:
                    status = "falha"
                registrar_lugar(
                    lugar,
                    self.consulta,
                    self.local,
                    status,
                    resultado.mensagem,
                )

            resultados = self.cliente.importar_lugares(
                self.lugares,
                on_progresso,
                on_resultado,
            )
            sucesso = sum(1 for item in resultados if item.sucesso)
            duplicados = sum(1 for item in resultados if item.status == 409)
            falhas = len(resultados) - sucesso - duplicados
            mensagem = (
                f"{sucesso} lead(s) importado(s), "
                f"{duplicados} duplicado(s), {falhas} falha(s)."
            )
            self.concluido.emit(mensagem, resultados)
        except SessaoExpirada as erro:
            self.erro.emit(str(erro))
        except Exception as erro:
            self.erro.emit(str(erro))


class SugestaoWorker(QThread):
    concluido = Signal(dict)
    erro = Signal(str)

    def __init__(self, consulta: str, local: str, parent=None) -> None:
        super().__init__(parent)
        self.consulta = consulta
        self.local = local

    def run(self) -> None:
        try:
            dados = sugerir_consulta_sync(self.consulta, self.local)
            self.concluido.emit(dados)
        except Exception as erro:
            self.erro.emit(str(erro))


class AtualizacaoWorker(QThread):
    concluido = Signal(object)
    erro = Signal(str)

    def __init__(self, webrp_url: str, parent=None) -> None:
        super().__init__(parent)
        self.webrp_url = webrp_url

    def run(self) -> None:
        try:
            self.concluido.emit(verificar_atualizacao(self.webrp_url))
        except Exception as erro:
            self.erro.emit(str(erro))
