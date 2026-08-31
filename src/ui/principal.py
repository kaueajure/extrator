from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import LIMITE_MAXIMO_RESULTADOS, VERSAO
from src.extrator.maps import desconectar_google
from src.extrator.modelos import LugarExtraido, ResultadoExtracao
from src.extrator.score import FiltrosLead, calcular_score
from src.servicos.buscas_variadas import (
    contagem_progresso,
    limpar_progresso_busca,
    proxima_busca_variada,
    registrar_busca_usada,
    salvar_urls_processadas,
)
from src.servicos.perfil_google import sessao_marcada, texto_status
from src.servicos.sessao import FiltrosSalvos, ler_filtros, salvar_filtros
from src.servicos.sugestoes import sugestoes_locais_rapidas
from src.servicos.webrp import ClienteWebRP, SessaoExpirada
from src.ui.popup_sugestoes import PopupSugestoes
from src.ui.tema import (
    FOLHA_ESTILO,
    criar_alternador,
    criar_barra_resultados,
    criar_barra_rodape,
    criar_botao,
    criar_campo,
    criar_etiqueta_admin,
    criar_grupo_botoes,
    criar_logotipo,
    criar_pagina_admin,
    criar_painel,
)
from src.ui.workers import ExtracaoWorker, GoogleLoginWorker, ImportacaoWorker, SugestaoWorker


class JanelaPrincipal(QMainWindow):
    def __init__(self, cliente: ClienteWebRP, email: str, webrp_url: str) -> None:
        super().__init__()
        self.cliente = cliente
        self.email = email
        self.webrp_url = webrp_url
        self.lugares: list[LugarExtraido] = []
        self.worker_extracao: ExtracaoWorker | None = None
        self.worker_importacao: ImportacaoWorker | None = None
        self.worker_sugestao: SugestaoWorker | None = None
        self.worker_google: GoogleLoginWorker | None = None
        self._ultimo_resultado: ResultadoExtracao | None = None
        self._pendente_fechar = False
        self._consulta_sugestao_pendente = ""
        self.timer_sugestao = QTimer(self)
        self.timer_sugestao.setSingleShot(True)
        self.timer_sugestao.timeout.connect(self._mostrar_sugestoes_apos_pausa)
        self.timer_status = QTimer(self)
        self.timer_status.setSingleShot(True)
        self.timer_status.timeout.connect(self._atualizar_status_busca)

        self.setWindowTitle("WebRP Extrator")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 780)
        self.setStyleSheet(FOLHA_ESTILO)

        pagina, layout_pagina = criar_pagina_admin()
        pagina.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout_pagina.addWidget(self._montar_busca(), 0)
        layout_pagina.addWidget(self._montar_area_principal(), 1)

        self.popup_sugestoes = PopupSugestoes(self)
        self.popup_sugestoes.definir_ancora(self.campo_consulta)
        self.popup_sugestoes.escolhida.connect(self._aplicar_sugestao)

        painel = QFrame()
        painel.setObjectName("painelPrincipal")
        painel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout_painel = QVBoxLayout(painel)
        layout_painel.setContentsMargins(0, 0, 0, 0)
        layout_painel.setSpacing(0)
        layout_painel.addWidget(pagina)

        self._area_conteudo = QWidget()
        self._area_conteudo.setObjectName("adminArea")
        self._layout_area = QHBoxLayout(self._area_conteudo)
        self._layout_area.setContentsMargins(32, 10, 32, 10)
        self._layout_area.setSpacing(0)
        self._layout_area.addWidget(painel)

        central = QWidget()
        central.setObjectName("adminShell")
        layout_central = QVBoxLayout(central)
        layout_central.setContentsMargins(0, 0, 0, 0)
        layout_central.setSpacing(0)
        layout_central.addWidget(self._montar_cabecalho())
        layout_central.addWidget(self._area_conteudo, stretch=1)
        self.setCentralWidget(central)

        filtros_salvos = ler_filtros()
        if filtros_salvos.consulta:
            self.campo_consulta.setText(filtros_salvos.consulta)
        self.campo_local.setText(filtros_salvos.local)
        self.spin_limite.setValue(max(1, min(LIMITE_MAXIMO_RESULTADOS, filtros_salvos.limite)))
        self._definir_navegador_visivel(filtros_salvos.navegador_visivel)
        self.check_sem_site.setChecked(filtros_salvos.sem_site)
        self.campo_max_avaliacoes.setText(filtros_salvos.max_avaliacoes)
        self.campo_nota_minima.setText(filtros_salvos.nota_minima)
        self.campo_score_minimo.setText(filtros_salvos.score_minimo)
        self.check_continuar.setChecked(filtros_salvos.continuar_busca)
        self.check_cruzar.setChecked(filtros_salvos.cruzar_webrp)
        self.check_variada_auto.setChecked(filtros_salvos.busca_variada_auto)
        self.check_perfil_google.setChecked(filtros_salvos.usar_perfil_google)
        self.spin_limite.valueChanged.connect(lambda _: self._preferencias_alteradas())
        self.campo_local.textChanged.connect(self._preferencias_alteradas)
        self.campo_consulta.textChanged.connect(self._preferencias_alteradas)
        self._atualizar_status_google()
        self._atualizar_status_busca()

    def _iniciais_usuario(self) -> str:
        parte = self.email.split("@", 1)[0].strip()
        if not parte:
            return "WR"
        if len(parte) >= 2:
            return parte[:2].upper()
        return parte[0].upper()

    def _nome_usuario(self) -> str:
        parte = self.email.split("@", 1)[0].strip()
        return parte.replace(".", " ").replace("_", " ").title() or "Usuário"

    def _margem_lateral(self) -> int:
        return max(20, int(self.width() * 0.05))

    def _montar_cabecalho(self) -> QFrame:
        cabecalho = QFrame()
        cabecalho.setObjectName("cabecalho")
        cabecalho.setFixedHeight(60)

        linha = QWidget()
        linha.setObjectName("cabecalhoLinha")
        self._layout_cabecalho_linha = QHBoxLayout(linha)
        self._layout_cabecalho_linha.setContentsMargins(32, 0, 32, 0)
        self._layout_cabecalho_linha.setSpacing(14)

        esquerda = QHBoxLayout()
        esquerda.setSpacing(9)
        esquerda.addWidget(criar_logotipo())
        esquerda.addWidget(criar_etiqueta_admin("Extrator"))

        centro = QHBoxLayout()
        centro.addStretch()
        titulo = QLabel("Prospectar no Google Maps")
        titulo.setObjectName("tituloPagina")
        centro.addWidget(titulo)
        centro.addStretch()

        avatar = QLabel(self._iniciais_usuario())
        avatar.setObjectName("usuarioAvatar")

        dados = QVBoxLayout()
        dados.setSpacing(1)
        nome = QLabel(self._nome_usuario())
        nome.setObjectName("usuarioNome")
        email = QLabel(self.email)
        email.setObjectName("usuarioEmail")
        dados.addWidget(nome)
        dados.addWidget(email)

        usuario = QHBoxLayout()
        usuario.setSpacing(8)
        usuario.addWidget(avatar)
        usuario.addLayout(dados)

        divisor = QFrame()
        divisor.setObjectName("headerDivisor")
        divisor.setFixedHeight(20)

        botao_sair = QPushButton("Sair")
        botao_sair.setObjectName("sair")
        botao_sair.clicked.connect(self._sair)

        versao = QLabel(f"v{VERSAO}")
        versao.setObjectName("descricaoSecao")

        direita = QHBoxLayout()
        direita.setSpacing(10)
        direita.addWidget(versao)
        direita.addLayout(usuario)
        direita.addWidget(divisor)
        direita.addWidget(botao_sair)

        self._layout_cabecalho_linha.addLayout(esquerda)
        self._layout_cabecalho_linha.addLayout(centro, stretch=1)
        self._layout_cabecalho_linha.addLayout(direita)

        layout_cabecalho = QVBoxLayout(cabecalho)
        layout_cabecalho.setContentsMargins(0, 0, 0, 0)
        layout_cabecalho.addWidget(linha)
        return cabecalho

    def _montar_busca(self) -> QFrame:
        painel, layout = criar_painel("Busca e filtros")
        painel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        self.campo_consulta = QLineEdit()
        self.campo_consulta.setPlaceholderText("Ex.: clínicas odontológicas")
        self.campo_consulta.textChanged.connect(self._ao_digitar_consulta)
        self.campo_consulta.editingFinished.connect(self._esconder_popup_se_vazio)

        self.campo_local = QLineEdit("São José do Rio Preto, SP, Brasil")
        self.campo_local.textChanged.connect(self._agendar_status_busca)

        self.spin_limite = QSpinBox()
        self.spin_limite.setRange(1, LIMITE_MAXIMO_RESULTADOS)
        self.spin_limite.setValue(10)
        self.spin_limite.setFixedWidth(84)

        (
            self.alternador_navegador,
            self.btn_nav_visivel,
            self.btn_nav_invisivel,
            self.grupo_navegador,
        ) = criar_alternador("Visível", "Invisível", esquerda_ativa=True)
        self.btn_nav_visivel.clicked.connect(self._navegador_alterado)
        self.btn_nav_invisivel.clicked.connect(self._navegador_alterado)

        self.botao_extrair = criar_botao("Extrair dados", "primario", 120)
        self.botao_extrair.clicked.connect(self._iniciar_extracao)

        self.botao_cancelar = criar_botao("Cancelar", "perigo", 92)
        self.botao_cancelar.setEnabled(False)
        self.botao_cancelar.clicked.connect(self._cancelar_extracao)

        linha_campos = QHBoxLayout()
        linha_campos.setSpacing(10)
        linha_campos.setAlignment(Qt.AlignmentFlag.AlignBottom)
        linha_campos.addWidget(criar_campo("Nome ou categoria", self.campo_consulta), stretch=2)
        linha_campos.addWidget(criar_campo("Cidade ou região", self.campo_local), stretch=3)
        layout.addLayout(linha_campos)

        linha_acoes = QHBoxLayout()
        linha_acoes.setSpacing(10)
        linha_acoes.setAlignment(Qt.AlignmentFlag.AlignBottom)
        col_limite = criar_campo("Resultados", self.spin_limite)
        col_limite.setFixedWidth(92)
        linha_acoes.addWidget(col_limite)
        linha_acoes.addWidget(criar_campo("Navegador", self.alternador_navegador))
        linha_acoes.addStretch()
        linha_acoes.addWidget(criar_grupo_botoes(self.botao_extrair, self.botao_cancelar))
        layout.addLayout(linha_acoes)

        faixa_google = QFrame()
        faixa_google.setObjectName("faixaGoogle")
        google = QHBoxLayout(faixa_google)
        google.setContentsMargins(10, 8, 10, 8)
        google.setSpacing(8)

        self.check_perfil_google = QCheckBox("Sessão Google")
        self.check_perfil_google.setObjectName("opcaoCompacta")
        self.check_perfil_google.setToolTip(
            "Mantém cookies e login do Google neste computador para reduzir bloqueios no Maps."
        )
        self.check_perfil_google.stateChanged.connect(self._preferencias_alteradas)
        self.check_perfil_google.stateChanged.connect(self._atualizar_status_google)

        self.label_google = QLabel()
        self.label_google.setObjectName("descricaoSecao")
        self.label_google.setWordWrap(True)

        self.btn_google_login = criar_botao("Entrar no Google", "secundario", compacto=True)
        self.btn_google_login.clicked.connect(self._iniciar_login_google)
        self.btn_google_sair = criar_botao("Desconectar", "secundario", compacto=True)
        self.btn_google_sair.clicked.connect(self._desconectar_google)

        google.addWidget(self.check_perfil_google)
        google.addWidget(self.label_google, stretch=1)
        google.addWidget(self.btn_google_login)
        google.addWidget(self.btn_google_sair)
        layout.addWidget(faixa_google)

        opcoes = QWidget()
        opcoes.setObjectName("linhaOpcoes")
        opcoes_layout = QHBoxLayout(opcoes)
        opcoes_layout.setContentsMargins(0, 0, 0, 0)
        opcoes_layout.setSpacing(16)

        self.check_continuar = QCheckBox("Continuar busca")
        self.check_continuar.setObjectName("opcaoCompacta")
        self.check_continuar.setToolTip("Na mesma consulta, pula lugares já extraídos e pega os próximos.")
        self.check_cruzar = QCheckBox("Ignorar leads no WebRP")
        self.check_cruzar.setObjectName("opcaoCompacta")
        self.check_cruzar.setToolTip("Cruza com o funil antes de exibir resultados.")
        self.check_variada_auto = QCheckBox("Busca variada após importar")
        self.check_variada_auto.setObjectName("opcaoCompacta")
        self.check_variada_auto.setToolTip("Após importar, sugere automaticamente outro termo de busca.")
        for item in (self.check_continuar, self.check_cruzar, self.check_variada_auto):
            item.stateChanged.connect(self._preferencias_alteradas)
        opcoes_layout.addWidget(self.check_continuar)
        opcoes_layout.addWidget(self.check_cruzar)
        opcoes_layout.addWidget(self.check_variada_auto)
        opcoes_layout.addStretch()
        layout.addWidget(opcoes)

        self.check_sem_site = QCheckBox("Apenas sem site")
        self.check_sem_site.setObjectName("opcaoCompacta")
        self.campo_max_avaliacoes = QLineEdit()
        self.campo_max_avaliacoes.setPlaceholderText("200")
        self.campo_max_avaliacoes.setFixedWidth(84)
        self.campo_nota_minima = QLineEdit()
        self.campo_nota_minima.setPlaceholderText("4.0")
        self.campo_nota_minima.setFixedWidth(72)
        self.campo_score_minimo = QLineEdit()
        self.campo_score_minimo.setPlaceholderText("60")
        self.campo_score_minimo.setFixedWidth(72)

        for campo in (
            self.check_sem_site,
            self.campo_max_avaliacoes,
            self.campo_nota_minima,
            self.campo_score_minimo,
        ):
            if isinstance(campo, QCheckBox):
                campo.stateChanged.connect(self._filtros_alterados)
            else:
                campo.textChanged.connect(self._filtros_alterados)

        linha_filtros = QHBoxLayout()
        linha_filtros.setSpacing(12)
        linha_filtros.setAlignment(Qt.AlignmentFlag.AlignBottom)
        linha_filtros.addWidget(self.check_sem_site)
        linha_filtros.addWidget(criar_campo("Máx. aval. (<)", self.campo_max_avaliacoes))
        linha_filtros.addWidget(criar_campo("Nota mín. (≥)", self.campo_nota_minima))
        linha_filtros.addWidget(criar_campo("Score mín. (≥)", self.campo_score_minimo))
        linha_filtros.addStretch()
        layout.addLayout(linha_filtros)

        barra_rodape, acoes_busca = criar_barra_rodape()
        self.label_progresso = QLabel()
        self.label_progresso.setObjectName("descricaoSecao")
        self.label_progresso.setWordWrap(True)
        self.btn_proxima_busca = criar_botao("Próxima variada", "secundario", compacto=True)
        self.btn_proxima_busca.clicked.connect(self._aplicar_proxima_busca_variada)
        self.btn_reiniciar_busca = criar_botao("Reiniciar", "secundario", compacto=True)
        self.btn_reiniciar_busca.clicked.connect(self._reiniciar_progresso_busca)
        acoes_busca.addWidget(self.label_progresso, stretch=1)
        acoes_busca.addWidget(self.btn_proxima_busca)
        acoes_busca.addWidget(self.btn_reiniciar_busca)
        layout.addWidget(barra_rodape)

        self.barra_progresso_extracao = QProgressBar()
        self.barra_progresso_extracao.setVisible(False)
        self.barra_progresso_extracao.setFixedHeight(8)
        self.barra_progresso_extracao.setTextVisible(False)
        layout.addWidget(self.barra_progresso_extracao)
        return painel

    def _ao_digitar_consulta(self) -> None:
        # Esconde enquanto digita; só abre o popup após 1,5s parado
        self.popup_sugestoes.hide()
        self.timer_sugestao.start(1500)
        self._agendar_status_busca()

    def _agendar_status_busca(self) -> None:
        self.timer_status.start(350)

    def _esconder_popup_se_vazio(self) -> None:
        if not self.campo_consulta.text().strip():
            self.popup_sugestoes.hide()

    def _mostrar_sugestoes_apos_pausa(self) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        if len(consulta) < 2:
            self.popup_sugestoes.hide()
            return

        locais = sugestoes_locais_rapidas(consulta, local)
        if locais:
            self.popup_sugestoes.atualizar(locais, origem="regras")
        else:
            self.popup_sugestoes.hide()

        if len(consulta) >= 3:
            self._buscar_sugestoes_ia()

    def _montar_area_principal(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.addWidget(self._montar_logs())
        splitter.addWidget(self._montar_resultados())
        splitter.setSizes([300, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        return splitter

    def _montar_logs(self) -> QFrame:
        painel, layout = criar_painel("Atividade")
        painel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        botao_limpar = criar_botao("Limpar", "secundario", compacto=True)
        botao_limpar.clicked.connect(lambda: self.area_logs.clear())
        barra = QHBoxLayout()
        barra.addStretch()
        barra.addWidget(botao_limpar)

        self.area_logs = QTextEdit()
        self.area_logs.setObjectName("logs")
        self.area_logs.setReadOnly(True)
        self.area_logs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout.addLayout(barra)
        layout.addWidget(self.area_logs, stretch=1)
        painel.setMinimumWidth(260)
        painel.setMaximumWidth(380)
        return painel

    def _montar_resultados(self) -> QFrame:
        painel, layout = criar_painel("Resultados")
        painel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        barra, barra_layout = criar_barra_resultados()
        self.label_resumo = QLabel("Nenhuma extração iniciada.")
        self.label_resumo.setObjectName("descricaoSecao")

        self.botao_selecionar = criar_botao("Selecionar visíveis", "secundario", compacto=True)
        self.botao_selecionar.setEnabled(False)
        self.botao_selecionar.clicked.connect(self._selecionar_visiveis)

        self.botao_desmarcar = criar_botao("Desmarcar", "secundario", compacto=True)
        self.botao_desmarcar.setEnabled(False)
        self.botao_desmarcar.clicked.connect(self._desmarcar_visiveis)

        self.botao_importar = criar_botao("Importar ao WebRP", "primario", 140)
        self.botao_importar.setEnabled(False)
        self.botao_importar.clicked.connect(self._importar)

        barra_layout.addWidget(self.label_resumo, stretch=1)
        barra_layout.addWidget(
            criar_grupo_botoes(self.botao_selecionar, self.botao_desmarcar, self.botao_importar)
        )

        self.frame_vazio = QFrame()
        self.frame_vazio.setObjectName("estadoVazio")
        vazio_layout = QVBoxLayout(self.frame_vazio)
        vazio_layout.setContentsMargins(16, 20, 16, 20)
        vazio_layout.setSpacing(4)
        self.label_vazio_titulo = QLabel("Pronto para prospectar")
        self.label_vazio_titulo.setObjectName("tituloSecao")
        self.label_vazio_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_vazio_texto = QLabel(
            "Os lugares extraídos aparecerão aqui com score e filtros aplicáveis."
        )
        self.label_vazio_texto.setObjectName("descricaoSecao")
        self.label_vazio_texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_vazio_texto.setWordWrap(True)
        vazio_layout.addWidget(self.label_vazio_titulo)
        vazio_layout.addWidget(self.label_vazio_texto)

        self.tabela = QTableWidget(0, 9)
        self.tabela.setHorizontalHeaderLabels(
            ["", "Score", "Empresa", "Endereço", "Categoria", "Aval.", "Nota", "Contato", "Maps"]
        )
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.tabela.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.tabela.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.tabela.setColumnWidth(0, 36)
        self.tabela.setColumnWidth(1, 56)
        self.tabela.setColumnWidth(5, 52)
        self.tabela.setColumnWidth(6, 52)
        self.tabela.setColumnWidth(8, 52)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setShowGrid(False)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabela.hide()

        self.label_feedback = QLabel("")
        self.label_feedback.setWordWrap(True)

        layout.addWidget(barra)
        layout.addWidget(self.frame_vazio)
        layout.addWidget(self.tabela, stretch=1)

        self.barra_progresso_importacao = QProgressBar()
        self.barra_progresso_importacao.setVisible(False)
        self.barra_progresso_importacao.setFixedHeight(8)
        layout.addWidget(self.barra_progresso_importacao)
        layout.addWidget(self.label_feedback)
        return painel

    def _preferencias_alteradas(self) -> None:
        salvar_filtros(
            FiltrosSalvos(
                sem_site=self.check_sem_site.isChecked(),
                max_avaliacoes=self.campo_max_avaliacoes.text(),
                nota_minima=self.campo_nota_minima.text(),
                score_minimo=self.campo_score_minimo.text(),
                continuar_busca=self.check_continuar.isChecked(),
                cruzar_webrp=self.check_cruzar.isChecked(),
                busca_variada_auto=self.check_variada_auto.isChecked(),
                usar_perfil_google=self.check_perfil_google.isChecked(),
                consulta=self.campo_consulta.text().strip(),
                local=self.campo_local.text().strip(),
                limite=self.spin_limite.value(),
                navegador_visivel=self._navegador_visivel(),
            )
        )
        self._atualizar_status_busca()
        self._atualizar_status_google()

    def _navegador_visivel(self) -> bool:
        return self.btn_nav_visivel.isChecked()

    def _definir_navegador_visivel(self, visivel: bool) -> None:
        self.btn_nav_visivel.setChecked(visivel)
        self.btn_nav_invisivel.setChecked(not visivel)

    def _navegador_alterado(self) -> None:
        if not self.btn_nav_visivel.isChecked() and not self.btn_nav_invisivel.isChecked():
            self._definir_navegador_visivel(True)
        self._preferencias_alteradas()

    def _atualizar_status_google(self) -> None:
        self.label_google.setText(texto_status())
        self.btn_google_sair.setEnabled(sessao_marcada())
        if self.check_perfil_google.isChecked():
            self._definir_navegador_visivel(True)
            self.btn_nav_invisivel.setEnabled(False)
            self.btn_nav_visivel.setEnabled(True)
            self.alternador_navegador.setToolTip(
                "Com «Sessão Google» ativa o navegador precisa ficar visível para manter o login."
            )
        else:
            self.btn_nav_visivel.setEnabled(True)
            self.btn_nav_invisivel.setEnabled(True)
            self.alternador_navegador.setToolTip(
                "Visível: abre o Chrome na tela. Invisível: roda em segundo plano (mais rápido, "
                "mas captchas exigem modo visível)."
            )

    def _iniciar_login_google(self) -> None:
        if self.worker_google and self.worker_google.isRunning():
            return
        if self.worker_extracao and self.worker_extracao.isRunning():
            QMessageBox.warning(
                self,
                "Extração em andamento",
                "Aguarde a extração terminar antes de abrir o login do Google.",
            )
            return

        self.btn_google_login.setEnabled(False)
        self.btn_google_login.setText("Aguardando login…")
        self._registrar_log("Abrindo navegador para login no Google…")

        self.worker_google = GoogleLoginWorker(self)
        self.worker_google.log.connect(self._registrar_log)
        self.worker_google.concluido.connect(self._login_google_concluido)
        self.worker_google.erro.connect(self._login_google_erro)
        self.worker_google.start()

    def _login_google_concluido(self, logado: bool) -> None:
        self.btn_google_login.setEnabled(True)
        self.btn_google_login.setText("Entrar no Google")
        self._atualizar_status_google()
        if logado:
            QMessageBox.information(
                self,
                "Google conectado",
                "Sessão salva. As próximas extrações usarão sua conta Google no Maps.",
            )
        else:
            QMessageBox.warning(
                self,
                "Login não confirmado",
                "O app não detectou login concluído.\n\n"
                "1. Clique em «Entrar no Google» de novo\n"
                "2. No Chrome, clique em «Fazer login» no Maps\n"
                "3. Conclua e-mail e senha (e 2FA se pedir)\n"
                "4. Aguarde o Maps carregar — não feche o Chrome antes disso",
            )

    def _login_google_erro(self, mensagem: str) -> None:
        self.btn_google_login.setEnabled(True)
        self.btn_google_login.setText("Entrar no Google")
        self._registrar_log(f"Erro no login Google: {mensagem}")
        QMessageBox.critical(self, "Erro no login Google", mensagem)

    def _desconectar_google(self) -> None:
        if self.worker_google and self.worker_google.isRunning():
            return
        confirmar = QMessageBox.question(
            self,
            "Desconectar Google",
            "Remover a sessão Google salva neste computador?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return
        desconectar_google()
        self._atualizar_status_google()
        self._registrar_log("Sessão Google removida deste computador.")

    def _atualizar_status_busca(self) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        if len(consulta) < 2 or len(local) < 2:
            self.label_progresso.setText("")
            return

        partes: list[str] = []
        total = contagem_progresso(consulta, local)
        if total:
            partes.append(f"{total} lugar(es) já processado(s) nesta busca.")
        proxima = proxima_busca_variada(consulta, local)
        if proxima:
            partes.append(f"Próxima variada: «{proxima}».")
        self.label_progresso.setText(" ".join(partes))

    def _aplicar_proxima_busca_variada(self) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        proxima = proxima_busca_variada(consulta, local)
        if not proxima:
            QMessageBox.information(
                self,
                "Sem variações",
                "Não há mais buscas variadas para este termo e região. Tente outra categoria.",
            )
            return
        registrar_busca_usada(consulta, local)
        self.campo_consulta.setText(proxima)
        self.popup_sugestoes.hide()
        self._registrar_log(f"Busca variada aplicada: {proxima}")
        self._atualizar_status_busca()

    def _reiniciar_progresso_busca(self) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        if len(consulta) < 2 or len(local) < 2:
            return
        confirmar = QMessageBox.question(
            self,
            "Reiniciar busca",
            "Limpar o progresso desta consulta e voltar a extrair do início?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return
        limpar_progresso_busca(consulta, local)
        self._registrar_log("Progresso da busca reiniciado.")
        self._atualizar_status_busca()

    def _pos_extracao(self, resultado: ResultadoExtracao) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        registrar_busca_usada(consulta, local)
        if self.check_continuar.isChecked() and resultado.urls_processadas:
            salvar_urls_processadas(consulta, local, set(resultado.urls_processadas))
        self._atualizar_status_busca()

        if (
            resultado.ignorados_continuacao
            and not resultado.lugares
            and self.check_variada_auto.isChecked()
        ):
            proxima = proxima_busca_variada(consulta, local)
            if proxima:
                self._registrar_log(f"Sugestão: tente a busca variada «{proxima}».")
                self.campo_consulta.setText(proxima)

    def _pos_importacao_variada(self) -> None:
        if not self.check_variada_auto.isChecked():
            return
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        proxima = proxima_busca_variada(consulta, local)
        if proxima:
            registrar_busca_usada(consulta, local)
            self.campo_consulta.setText(proxima)
            self._registrar_log(f"Próxima busca variada: {proxima}")
            self._atualizar_status_busca()
            self._buscar_sugestoes_ia()

    def _buscar_sugestoes_ia(self) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        if len(consulta) < 3:
            return

        if self.worker_sugestao and self.worker_sugestao.isRunning():
            # Reagenda se já houver worker — evita fila acumulada
            self._consulta_sugestao_pendente = consulta
            return

        self._consulta_sugestao_pendente = consulta
        self.worker_sugestao = SugestaoWorker(consulta, local, self)
        self.worker_sugestao.concluido.connect(self._exibir_sugestoes)
        self.worker_sugestao.erro.connect(self._sugestao_erro)
        self.worker_sugestao.start()

    def _sugestao_erro(self, mensagem: str) -> None:
        self._registrar_log(f"Sugestões IA indisponíveis: {mensagem}")

    def _exibir_sugestoes(self, dados: dict) -> None:
        consulta_atual = self.campo_consulta.text().strip()
        # Descarta resposta atrasada se o usuário já digitou outra coisa
        if self._consulta_sugestao_pendente and consulta_atual.lower() != self._consulta_sugestao_pendente.lower():
            if len(consulta_atual) >= 3:
                self.timer_sugestao.start(1500)
            return

        sugestoes = [str(item) for item in (dados.get("sugestoes") or []) if str(item).strip()]
        if not sugestoes or len(consulta_atual) < 2:
            return

        origem = str(dados.get("origem") or "regras")
        if origem == "gemini" or not self.popup_sugestoes.isVisible():
            self.popup_sugestoes.atualizar(sugestoes, origem=origem)

        pendente = self._consulta_sugestao_pendente
        if pendente and pendente.lower() != consulta_atual.lower() and len(consulta_atual) >= 3:
            self.timer_sugestao.start(1500)

    def _aplicar_sugestao(self, sugestao: str) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        if consulta:
            registrar_busca_usada(consulta, local)
        self.campo_consulta.blockSignals(True)
        self.campo_consulta.setText(sugestao)
        self.campo_consulta.blockSignals(False)
        self.popup_sugestoes.hide()
        self._registrar_log(f"Consulta atualizada: {sugestao}")
        self._atualizar_status_busca()

    def _filtros(self) -> FiltrosLead:
        def parse_int(texto: str) -> int | None:
            texto = texto.strip()
            if not texto:
                return None
            try:
                return int(texto)
            except ValueError:
                return None

        def parse_float(texto: str) -> float | None:
            texto = texto.strip().replace(",", ".")
            if not texto:
                return None
            try:
                return float(texto)
            except ValueError:
                return None

        return FiltrosLead(
            sem_site=self.check_sem_site.isChecked(),
            max_avaliacoes=parse_int(self.campo_max_avaliacoes.text()),
            nota_minima=parse_float(self.campo_nota_minima.text()),
            score_minimo=parse_int(self.campo_score_minimo.text()),
        )

    def _validar_campo_numerico(self, campo: QLineEdit, inteiro: bool = False) -> bool:
        texto = campo.text().strip().replace(",", ".")
        if not texto:
            campo.setStyleSheet("")
            return True
        try:
            if inteiro:
                int(texto)
            else:
                float(texto)
            campo.setStyleSheet("")
            return True
        except ValueError:
            campo.setStyleSheet("border-color: #b42318;")
            return False

    def _filtros_alterados(self) -> None:
        valido = (
            self._validar_campo_numerico(self.campo_max_avaliacoes, inteiro=True)
            and self._validar_campo_numerico(self.campo_nota_minima, inteiro=False)
            and self._validar_campo_numerico(self.campo_score_minimo, inteiro=True)
        )
        self._preferencias_alteradas()
        if valido:
            self._atualizar_tabela()

    def _registrar_log(self, mensagem: str) -> None:
        hora = datetime.now().strftime("%H:%M:%S")
        self.area_logs.append(f"[{hora}] {mensagem}")

    def _extracao_ativa(self) -> bool:
        return self.worker_extracao is not None and self.worker_extracao.isRunning()

    def _iniciar_extracao(self) -> None:
        consulta = self.campo_consulta.text().strip()
        local = self.campo_local.text().strip()
        if len(consulta) < 2 or len(local) < 2:
            QMessageBox.warning(self, "Busca inválida", "Informe consulta e local com ao menos 2 caracteres.")
            return

        if self.worker_extracao and self.worker_extracao.isRunning():
            return

        self.popup_sugestoes.hide()
        self.lugares.clear()
        self.label_feedback.setText("")
        self.label_feedback.setObjectName("")
        self._atualizar_tabela()
        self.label_resumo.setText("Extração em andamento…")

        self.botao_extrair.setEnabled(False)
        self.botao_cancelar.setEnabled(True)
        self.barra_progresso_extracao.setVisible(True)
        self.barra_progresso_extracao.setRange(0, 0)
        self._registrar_log("Iniciando extração…")

        self.worker_extracao = ExtracaoWorker(
            consulta,
            local,
            self.spin_limite.value(),
            self._navegador_visivel(),
            self.check_continuar.isChecked(),
            self.check_cruzar.isChecked(),
            self.check_perfil_google.isChecked(),
            self.cliente,
            self,
        )
        self.worker_extracao.log.connect(self._registrar_log)
        self.worker_extracao.lugar.connect(self._adicionar_lugar)
        self.worker_extracao.progresso.connect(self._atualizar_progresso_extracao)
        self.worker_extracao.concluido.connect(self._extracao_concluida)
        self.worker_extracao.cancelado.connect(self._extracao_cancelada)
        self.worker_extracao.erro.connect(self._extracao_erro)
        self.worker_extracao.start()

    def _cancelar_extracao(self, fechar_depois: bool = False) -> None:
        if not self.worker_extracao or not self.worker_extracao.isRunning():
            return
        self._pendente_fechar = fechar_depois
        self.botao_cancelar.setEnabled(False)
        self.botao_cancelar.setText("Cancelando…")
        self.worker_extracao.cancelar()
        self._registrar_log("Cancelamento solicitado…")

    def _adicionar_lugar(self, lugar: LugarExtraido) -> None:
        lugar.score = calcular_score(lugar)
        self.lugares.append(lugar)
        self._atualizar_tabela()

    def _atualizar_progresso_extracao(self, atual: int, total: int) -> None:
        self.barra_progresso_extracao.setRange(0, total)
        self.barra_progresso_extracao.setValue(atual)
        self.label_resumo.setText(f"Extraindo {atual}/{total}…")

    def _formatar_resumo(self, resultado: ResultadoExtracao) -> str:
        partes = [f"{len(resultado.lugares)} extraído(s)"]
        if resultado.ignorados_webrp:
            partes.append(f"{resultado.ignorados_webrp} ignorado(s) no WebRP")
        if resultado.ignorados_continuacao:
            partes.append(f"{resultado.ignorados_continuacao} pulado(s) na continuação")
        return " — ".join(partes)

    def _extracao_concluida(self, resultado: ResultadoExtracao) -> None:
        self._ultimo_resultado = resultado
        self._registrar_log(
            f"Concluído em {resultado.duracao_segundos}s — {self._formatar_resumo(resultado)}."
        )
        self._pos_extracao(resultado)
        self._finalizar_extracao()

    def _extracao_cancelada(self, resultado: ResultadoExtracao) -> None:
        self._ultimo_resultado = resultado
        total = len(resultado.lugares)
        if total:
            self._registrar_log(
                f"Extração cancelada — {total} lugar(es) mantido(s) em {resultado.duracao_segundos}s."
            )
            self._pos_extracao(resultado)
        else:
            self._registrar_log("Extração cancelada pelo usuário.")
            self.label_resumo.setText("Extração cancelada.")
        self._finalizar_extracao()
        if self._pendente_fechar:
            self._pendente_fechar = False
            self.cliente.fechar()
            self.close()

    def _extracao_erro(self, mensagem: str) -> None:
        self._registrar_log(f"Erro: {mensagem}")
        captcha = "captcha" in mensagem.lower() or "verificação de segurança" in mensagem.lower()
        if captcha:
            self.label_feedback.setObjectName("feedbackErro")
            self.label_feedback.setText(mensagem)
            self.label_feedback.style().unpolish(self.label_feedback)
            self.label_feedback.style().polish(self.label_feedback)
            if not self._navegador_visivel():
                self._definir_navegador_visivel(True)
                self._preferencias_alteradas()
            QMessageBox.warning(
                self,
                "Captcha detectado",
                mensagem + "\n\nO modo «Visível» foi ativado para a próxima tentativa.",
            )
        else:
            QMessageBox.critical(self, "Extração interrompida", mensagem)
        self._finalizar_extracao()

    def _finalizar_extracao(self) -> None:
        self.barra_progresso_extracao.setVisible(False)
        self.botao_extrair.setEnabled(True)
        self.botao_extrair.setText("Extrair dados")
        self.botao_cancelar.setEnabled(False)
        self.botao_cancelar.setText("Cancelar")
        self._atualizar_status_google()
        self._atualizar_tabela()

    def _visiveis(self) -> list[tuple[LugarExtraido, int]]:
        filtros = self._filtros()
        pares: list[tuple[LugarExtraido, int]] = []
        for lugar in self.lugares:
            score = calcular_score(lugar)
            lugar.score = score
            if filtros.passa(lugar, score):
                pares.append((lugar, score))
        pares.sort(key=lambda item: item[1], reverse=True)
        return pares

    def _atualizar_tabela(self) -> None:
        visiveis = self._visiveis()
        self.tabela.setRowCount(len(visiveis))

        for linha, (lugar, score) in enumerate(visiveis):
            self.tabela.setRowHeight(linha, 52)

            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            check.setCheckState(Qt.CheckState.Checked)
            self.tabela.setItem(linha, 0, check)

            item_score = QTableWidgetItem(str(score))
            item_score.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if score >= 75:
                item_score.setForeground(QColor("#0b826e"))
            elif score >= 55:
                item_score.setForeground(QColor("#3730e0"))
            else:
                item_score.setForeground(QColor("#b42318"))
            font = item_score.font()
            font.setBold(True)
            item_score.setFont(font)
            self.tabela.setItem(linha, 1, item_score)

            item_nome = QTableWidgetItem(lugar.nome)
            font_nome = item_nome.font()
            font_nome.setBold(True)
            item_nome.setFont(font_nome)
            item_nome.setToolTip(lugar.url_referencia or lugar.nome)
            self.tabela.setItem(linha, 2, item_nome)
            self.tabela.setItem(linha, 3, QTableWidgetItem(lugar.endereco or "—"))
            self.tabela.setItem(linha, 4, QTableWidgetItem(lugar.categoria or "—"))
            self.tabela.setItem(
                linha,
                5,
                QTableWidgetItem(str(lugar.avaliacoes) if lugar.avaliacoes is not None else "—"),
            )
            self.tabela.setItem(
                linha,
                6,
                QTableWidgetItem(f"{lugar.nota:.1f}" if lugar.nota is not None else "—"),
            )
            self.tabela.setItem(linha, 7, QTableWidgetItem(lugar.telefone or "—"))
            item_maps = QTableWidgetItem("Abrir" if lugar.url_referencia else "—")
            if lugar.url_referencia:
                item_maps.setToolTip(lugar.url_referencia)
                item_maps.setForeground(QColor("#3730e0"))
            self.tabela.setItem(linha, 8, item_maps)

        total = len(self.lugares)
        if self._extracao_ativa():
            if total == 0:
                self.label_resumo.setText("Extração em andamento…")
                self.frame_vazio.show()
                self.tabela.hide()
                self.label_vazio_titulo.setText("Extraindo dados")
                self.label_vazio_texto.setText(
                    "Os resultados aparecem aqui conforme cada lugar é processado."
                )
            else:
                self.label_resumo.setText(f"Extraindo… {total} lugar(es) até agora.")
                if len(visiveis) == 0:
                    self.frame_vazio.show()
                    self.tabela.hide()
                    self.label_vazio_titulo.setText("Aguardando resultados visíveis")
                    self.label_vazio_texto.setText(
                        "Lugares já extraídos não passaram nos filtros atuais."
                    )
                else:
                    self.frame_vazio.hide()
                    self.tabela.show()
            self.botao_importar.setEnabled(False)
            self.botao_selecionar.setEnabled(False)
            self.botao_desmarcar.setEnabled(False)
            return

        if total == 0:
            self.label_resumo.setText("Nenhuma extração iniciada.")
            self.frame_vazio.show()
            self.tabela.hide()
            self.label_vazio_titulo.setText("Pronto para prospectar")
            self.label_vazio_texto.setText(
                "Os lugares extraídos aparecerão aqui com score e filtros aplicáveis."
            )
        elif len(visiveis) == 0:
            self.label_resumo.setText(f"{total} extraído(s) → nenhum visível após filtros.")
            self.frame_vazio.show()
            self.tabela.hide()
            self.label_vazio_titulo.setText("Nenhum resultado visível")
            self.label_vazio_texto.setText(
                "Ajuste os filtros ou extraia mais lugares com termos mais específicos."
            )
        else:
            self.frame_vazio.hide()
            self.tabela.show()
            resumo = f"{len(visiveis)} visível(is)"
            if self._ultimo_resultado and (
                self._ultimo_resultado.ignorados_webrp or self._ultimo_resultado.ignorados_continuacao
            ):
                resumo = f"{self._formatar_resumo(self._ultimo_resultado)} → {len(visiveis)} visível(is)"
            elif len(visiveis) == total:
                self.label_resumo.setText(f"{total} lugar(es) extraído(s).")
            else:
                self.label_resumo.setText(f"{total} extraído(s) → {len(visiveis)} visível(is) após filtros.")
                habilitar = len(visiveis) > 0
                self.botao_importar.setEnabled(habilitar)
                self.botao_selecionar.setEnabled(habilitar)
                self.botao_desmarcar.setEnabled(habilitar)
                return
            self.label_resumo.setText(resumo)

        habilitar = len(visiveis) > 0
        self.botao_importar.setEnabled(habilitar)
        self.botao_selecionar.setEnabled(habilitar)
        self.botao_desmarcar.setEnabled(habilitar)

    def _selecionar_visiveis(self) -> None:
        for linha in range(self.tabela.rowCount()):
            item = self.tabela.item(linha, 0)
            if item:
                item.setCheckState(Qt.CheckState.Checked)

    def _desmarcar_visiveis(self) -> None:
        for linha in range(self.tabela.rowCount()):
            item = self.tabela.item(linha, 0)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)

    def _lugares_selecionados(self) -> list[LugarExtraido]:
        visiveis = self._visiveis()
        selecionados: list[LugarExtraido] = []
        for linha, (lugar, score) in enumerate(visiveis):
            item = self.tabela.item(linha, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                lugar.score = score
                selecionados.append(lugar)
        return selecionados

    def _importar(self) -> None:
        selecionados = self._lugares_selecionados()
        if not selecionados:
            self.label_feedback.setObjectName("feedbackErro")
            self.label_feedback.setText("Selecione ao menos um lugar visível.")
            self.label_feedback.style().unpolish(self.label_feedback)
            self.label_feedback.style().polish(self.label_feedback)
            return

        if self.worker_importacao and self.worker_importacao.isRunning():
            return

        self.botao_importar.setEnabled(False)
        self.botao_importar.setText("Importando…")
        self.barra_progresso_importacao.setVisible(True)
        self.barra_progresso_importacao.setRange(0, len(selecionados))
        self.barra_progresso_importacao.setValue(0)
        self.label_feedback.setObjectName("")
        self.label_feedback.setText(f"Enviando {len(selecionados)} lead(s) ao WebRP…")

        self.worker_importacao = ImportacaoWorker(self.cliente, selecionados, self)
        self.worker_importacao.progresso.connect(self._atualizar_progresso_importacao)
        self.worker_importacao.concluido.connect(self._importacao_concluida)
        self.worker_importacao.erro.connect(self._importacao_erro)
        self.worker_importacao.start()

    def _atualizar_progresso_importacao(self, atual: int, total: int, nome: str) -> None:
        self.barra_progresso_importacao.setValue(atual)
        self.label_feedback.setText(f"Importando {atual}/{total}: {nome}")

    def _importacao_concluida(self, mensagem: str, resultados: list) -> None:
        self.barra_progresso_importacao.setVisible(False)
        self.label_feedback.setObjectName("feedbackOk")
        self.label_feedback.setText(mensagem)
        self.label_feedback.style().unpolish(self.label_feedback)
        self.label_feedback.style().polish(self.label_feedback)
        self._registrar_log(mensagem)
        for item in resultados:
            if item.sucesso:
                prefixo = "✓"
            elif item.status == 409:
                prefixo = "↷"
            else:
                prefixo = "✗"
            self._registrar_log(f"{prefixo} {item.nome}: {item.mensagem}")
        self.botao_importar.setEnabled(len(self._visiveis()) > 0)
        self.botao_importar.setText("Importar ao WebRP")
        self._pos_importacao_variada()

    def _importacao_erro(self, mensagem: str) -> None:
        self.barra_progresso_importacao.setVisible(False)
        if isinstance(mensagem, str) and "expirada" in mensagem.lower():
            if self.cliente.renovar_sessao():
                self._registrar_log("Sessão WebRP renovada. Tente importar novamente.")
                QMessageBox.information(
                    self,
                    "Sessão renovada",
                    "A sessão foi renovada automaticamente. Clique em Importar novamente.",
                )
            else:
                QMessageBox.warning(
                    self,
                    "Sessão expirada",
                    "Faça login novamente para continuar importando leads.",
                )
        self.label_feedback.setObjectName("feedbackErro")
        self.label_feedback.setText(mensagem)
        self.label_feedback.style().unpolish(self.label_feedback)
        self.label_feedback.style().polish(self.label_feedback)
        self._registrar_log(f"Erro na importação: {mensagem}")
        self.botao_importar.setEnabled(len(self._visiveis()) > 0)
        self.botao_importar.setText("Importar ao WebRP")

    def _sair(self) -> None:
        if self.worker_extracao and self.worker_extracao.isRunning():
            confirmar = QMessageBox.question(
                self,
                "Extração em andamento",
                "Deseja cancelar a extração e sair?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirmar != QMessageBox.StandardButton.Yes:
                return
            self._cancelar_extracao(fechar_depois=True)
            return
        if self.worker_google and self.worker_google.isRunning():
            QMessageBox.warning(
                self,
                "Login Google em andamento",
                "Aguarde concluir ou feche a janela do navegador antes de sair.",
            )
            return

        confirmar = QMessageBox.question(
            self,
            "Sair",
            "Deseja encerrar o WebRP Extrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmar != QMessageBox.StandardButton.Yes:
            return

        self.cliente.fechar()
        self.close()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        margem = max(24, self._margem_lateral())
        self._layout_area.setContentsMargins(margem, 10, margem, 10)
        self._layout_cabecalho_linha.setContentsMargins(margem, 0, margem, 0)
        if self.popup_sugestoes.isVisible():
            self.popup_sugestoes.mostrar_sob_ancora()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        if hasattr(self, "popup_sugestoes") and self.popup_sugestoes.isVisible():
            self.popup_sugestoes.mostrar_sob_ancora()

    def closeEvent(self, event) -> None:
        if self.worker_extracao and self.worker_extracao.isRunning():
            event.ignore()
            confirmar = QMessageBox.question(
                self,
                "Extração em andamento",
                "Deseja cancelar a extração antes de fechar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if confirmar == QMessageBox.StandardButton.Yes:
                self._cancelar_extracao(fechar_depois=True)
            return

        self.cliente.fechar()
        event.accept()
