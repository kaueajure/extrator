from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.ui.login import JanelaLogin
from src.ui.principal import JanelaPrincipal
from src.ui.tema import FOLHA_ESTILO, aplicar_fonte


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("WebRP Extrator")
    app.setOrganizationName("WebRioPreto")
    app.setStyle("Fusion")
    aplicar_fonte(app)
    app.setStyleSheet(FOLHA_ESTILO)

    login = JanelaLogin()
    if login.exec() != JanelaLogin.DialogCode.Accepted or login.cliente is None:
        sys.exit(0)

    janela = JanelaPrincipal(login.cliente, login.email_logado, login.url_webrp)
    janela.show()
    sys.exit(app.exec())
