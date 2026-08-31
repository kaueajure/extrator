from __future__ import annotations

import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from src.ui.icone import aplicar_icone_janela, icone_app
from src.ui.login import JanelaLogin
from src.ui.principal import JanelaPrincipal
from src.ui.tema import aplicar_fonte, folha_estilo


def main() -> None:
    if sys.platform.startswith("linux"):
        QGuiApplication.setDesktopFileName("webrp-extrator")

    app = QApplication(sys.argv)
    app.setApplicationName("WebRP Extrator")
    app.setOrganizationName("WebRioPreto")
    app.setStyle("Fusion")
    icone = icone_app()
    if icone is not None:
        app.setWindowIcon(icone)
    aplicar_fonte(app)
    app.setStyleSheet(folha_estilo())

    login = JanelaLogin()
    aplicar_icone_janela(login)
    if login.exec() != JanelaLogin.DialogCode.Accepted or login.cliente is None:
        sys.exit(0)

    janela = JanelaPrincipal(login.cliente, login.email_logado, login.url_webrp)
    aplicar_icone_janela(janela)
    janela.show()
    sys.exit(app.exec())
