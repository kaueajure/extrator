from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.config import banco_configurado, chave_gemini, credenciais_env, empacotado, webrp_url_padrao
from src.servicos.sessao import CredenciaisSalvas, ler_credenciais, salvar_credenciais
from src.ui.icone import aplicar_icone_janela
from src.ui.tema import criar_botao, criar_campo, criar_logotipo, criar_opcao, folha_estilo
from src.ui.workers import LoginWorker


class JanelaLogin(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cliente = None
        self.email_logado = ""
        self.url_webrp = ""
        self.worker_login: LoginWorker | None = None
        self.setObjectName("dialogLogin")
        self.setWindowTitle("WebRP Extrator — Entrar")
        self.setMinimumSize(900, 650)
        aplicar_icone_janela(self)
        self.resize(1080, 650)
        self.setStyleSheet(folha_estilo())

        painel = QFrame()
        painel.setObjectName("loginPainel")

        contexto = QFrame()
        contexto.setObjectName("loginContexto")
        contexto_layout = QVBoxLayout(contexto)
        contexto_layout.setContentsMargins(42, 42, 42, 42)
        contexto_layout.setSpacing(0)

        logotipo_ctx = criar_logotipo()
        for rotulo in logotipo_ctx.findChildren(QLabel):
            if rotulo.objectName() == "logotipoWeb":
                rotulo.setObjectName("loginContextoWeb")
            elif rotulo.objectName() == "logotipoMarca":
                rotulo.setObjectName("loginContextoMarca")

        mensagem = QVBoxLayout()
        mensagem.setSpacing(19)
        titulo_ctx = QLabel("O centro de operação da Web Rio Preto.")
        titulo_ctx.setObjectName("loginContextoTitulo")
        titulo_ctx.setWordWrap(True)
        texto_ctx = QLabel(
            "Prospecte empresas no Google Maps e importe leads direto para o funil do painel WebRP."
        )
        texto_ctx.setObjectName("loginContextoTexto")
        texto_ctx.setWordWrap(True)
        mensagem.addWidget(titulo_ctx)
        mensagem.addWidget(texto_ctx)

        mapa = QFrame()
        mapa.setMinimumHeight(145)
        mapa.setStyleSheet(
            "QFrame {"
            "  border-top: 1px solid rgba(255,255,255,0.08);"
            "  background-color: #1c2029;"
            "}"
        )
        mapa_layout = QVBoxLayout(mapa)
        mapa_layout.setContentsMargins(42, 14, 28, 14)
        coords = QHBoxLayout()
        lat = QLabel("20°48′ S")
        lat.setStyleSheet("color: #747b87; font-size: 9px; background: transparent;")
        lon = QLabel("49°22′ O")
        lon.setStyleSheet("color: #747b87; font-size: 9px; background: transparent;")
        coords.addWidget(lat)
        coords.addStretch()
        coords.addWidget(lon)
        cidade = QLabel("São José do Rio Preto")
        cidade.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cidade.setStyleSheet("color: #c5c9d1; font-size: 10px; background: transparent;")
        mapa_layout.addLayout(coords)
        mapa_layout.addStretch()
        mapa_layout.addWidget(cidade)

        contexto_layout.addWidget(logotipo_ctx)
        contexto_layout.addStretch()
        contexto_layout.addLayout(mensagem)
        contexto_layout.addSpacing(35)
        contexto_layout.addWidget(mapa)

        acesso = QFrame()
        acesso_layout = QVBoxLayout(acesso)
        acesso_layout.setContentsMargins(0, 0, 0, 0)
        acesso_layout.setSpacing(0)

        cabecalho = QFrame()
        cabecalho.setObjectName("loginAcessoTopo")
        cabecalho.setFixedHeight(66)
        cabecalho_layout = QHBoxLayout(cabecalho)
        cabecalho_layout.setContentsMargins(38, 0, 38, 0)
        etiqueta_acesso = QLabel("ACESSO ADMINISTRATIVO")
        etiqueta_acesso.setObjectName("loginAcessoEtiqueta")
        uso_interno = QLabel("USO INTERNO")
        uso_interno.setObjectName("loginAcessoEtiqueta")
        cabecalho_layout.addWidget(etiqueta_acesso)
        cabecalho_layout.addStretch()
        cabecalho_layout.addWidget(uso_interno)

        conteudo = QWidget()
        conteudo_layout = QVBoxLayout(conteudo)
        conteudo_layout.setContentsMargins(36, 44, 36, 44)
        conteudo_layout.setSpacing(14)

        titulo = QLabel("Entre na sua conta")
        titulo.setObjectName("loginTitulo")
        subtitulo = QLabel("Use as credenciais de desenvolvedor do painel WebRP.")
        subtitulo.setObjectName("loginSubtitulo")
        subtitulo.setWordWrap(True)

        self.campo_url = QLineEdit(webrp_url_padrao())
        self.campo_url.setPlaceholderText("https://webriopreto.com")
        self.campo_email = QLineEdit()
        self.campo_email.setPlaceholderText("seu@email.com")
        self.campo_senha = QLineEdit()
        self.campo_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.campo_senha.setPlaceholderText("Senha do painel admin")

        self.check_lembrar = criar_opcao("Manter conectado neste computador")
        self.check_lembrar.setChecked(True)

        self.botao_entrar = criar_botao("Entrar", "primario")
        self.botao_entrar.setMinimumHeight(46)
        self.botao_entrar.setDefault(True)
        self.botao_entrar.clicked.connect(self._entrar)
        self.campo_senha.returnPressed.connect(self._entrar)

        status_ia = QLabel(
            "Gemini ativo para sugestões"
            if chave_gemini()
            else "Sugestões locais ativas"
        )
        status_ia.setObjectName("loginSubtitulo")

        modo = QLabel(
            "Conectado a webriopreto.com — cruzamento e importação via painel."
            if empacotado()
            else (
                "Banco MySQL configurado — cruzamento e importação diretos."
                if banco_configurado()
                else "Cruzamento e importação via API do WebRP."
            )
        )
        modo.setObjectName("loginSubtitulo")
        modo.setWordWrap(True)

        seguranca = QLabel("A sessão expira após 8 horas e será renovada automaticamente quando possível.")
        seguranca.setObjectName("loginSeguranca")
        seguranca.setWordWrap(True)

        conteudo_layout.addWidget(titulo)
        conteudo_layout.addWidget(subtitulo)
        conteudo_layout.addSpacing(8)
        if not empacotado():
            conteudo_layout.addWidget(criar_campo("URL do WebRP", self.campo_url))
        else:
            self.campo_url.hide()
        conteudo_layout.addWidget(criar_campo("E-mail", self.campo_email))
        conteudo_layout.addWidget(criar_campo("Senha", self.campo_senha))
        conteudo_layout.addWidget(self.check_lembrar)
        conteudo_layout.addWidget(self.botao_entrar)
        conteudo_layout.addWidget(status_ia)
        conteudo_layout.addWidget(modo)
        conteudo_layout.addWidget(seguranca)

        acesso_layout.addWidget(cabecalho)
        acesso_layout.addWidget(conteudo, stretch=1)

        split = QHBoxLayout(painel)
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(0)
        split.addWidget(contexto, stretch=104)
        split.addWidget(acesso, stretch=96)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(painel)

        self._carregar_credenciais()

    def _carregar_credenciais(self) -> None:
        env_email, env_senha = credenciais_env()
        if env_email:
            self.campo_email.setText(env_email)
        if env_senha:
            self.campo_senha.setText(env_senha)

        salvas = ler_credenciais()
        if salvas:
            if salvas.webrp_url and not empacotado():
                self.campo_url.setText(salvas.webrp_url)
            if salvas.email:
                self.campo_email.setText(salvas.email)
            if salvas.senha:
                self.campo_senha.setText(salvas.senha)
            self.check_lembrar.setChecked(salvas.lembrar)

    def _entrar(self) -> None:
        if self.worker_login and self.worker_login.isRunning():
            return

        url = webrp_url_padrao() if empacotado() else self.campo_url.text().strip().rstrip("/")
        email = self.campo_email.text().strip()
        senha = self.campo_senha.text()

        if len(url) < 4 or len(email) < 5 or len(senha) < 8:
            QMessageBox.warning(
                self,
                "Campos inválidos",
                "Preencha e-mail e senha (mín. 8 caracteres).",
            )
            return

        self.botao_entrar.setEnabled(False)
        self.botao_entrar.setText("Entrando…")

        self.worker_login = LoginWorker(url, email, senha, self)
        self.worker_login.concluido.connect(self._login_concluido)
        self.worker_login.erro.connect(self._login_erro)
        self.worker_login.start()

    def _login_concluido(self, cliente, email: str, url: str) -> None:
        try:
            salvar_credenciais(
                CredenciaisSalvas(
                    webrp_url=url,
                    email=email,
                    senha=self.campo_senha.text(),
                    lembrar=self.check_lembrar.isChecked(),
                )
            )
        except Exception as erro:
            QMessageBox.warning(
                self,
                "Credenciais não salvas",
                f"Login OK, mas não foi possível guardar as credenciais: {erro}",
            )

        self.cliente = cliente
        self.email_logado = email
        self.url_webrp = url
        self.accept()

    def _login_erro(self, mensagem: str) -> None:
        self.botao_entrar.setEnabled(True)
        self.botao_entrar.setText("Entrar")
        if "conectar" in mensagem.lower() or "network" in mensagem.lower():
            QMessageBox.critical(
                self,
                "Sem conexão",
                "Não foi possível conectar ao WebRP. Verifique sua internet.",
            )
        else:
            QMessageBox.critical(self, "Falha no login", mensagem)

    def closeEvent(self, event) -> None:
        if self.worker_login and self.worker_login.isRunning():
            event.ignore()
            return
        super().closeEvent(event)
