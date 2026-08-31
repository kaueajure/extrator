from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import QApplication, QWidget

from src.ui.historico import DialogoHistorico
from src.ui.principal import JanelaPrincipal
from src.ui.tema import folha_estilo


class _ClienteFalso:
    def fechar(self) -> None:
        pass


class UiSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["WEBRP_HISTORICO_PATH"] = str(Path(self.tmp.name) / "historico.sqlite3")
        os.environ["XDG_CONFIG_HOME"] = str(Path(self.tmp.name) / "config")

    def tearDown(self) -> None:
        os.environ.pop("WEBRP_HISTORICO_PATH", None)
        os.environ.pop("XDG_CONFIG_HOME", None)
        self.tmp.cleanup()

    def test_janela_principal_e_historico_sao_construidos(self) -> None:
        janela = JanelaPrincipal(_ClienteFalso(), "teste@webriopreto.com", "https://webriopreto.com")
        dialogo = DialogoHistorico(janela)
        self.assertEqual(dialogo.tabela.columnCount(), 8)
        self.assertEqual(janela.combo_continuacao.count(), 3)
        dialogo.close()
        janela.close()

    def test_folha_de_estilo_nao_emite_erro_de_parse(self) -> None:
        mensagens: list[str] = []

        def capturar(_tipo, _contexto, mensagem: str) -> None:
            mensagens.append(mensagem)

        manipulador_anterior = qInstallMessageHandler(capturar)
        try:
            widget = QWidget()
            widget.setStyleSheet(folha_estilo())
            widget.show()
            self.app.processEvents()
            widget.close()
        finally:
            qInstallMessageHandler(manipulador_anterior)

        erros = [mensagem for mensagem in mensagens if "parse stylesheet" in mensagem]
        self.assertEqual(erros, [])


if __name__ == "__main__":
    unittest.main()
