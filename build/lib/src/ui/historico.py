from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.servicos.diagnosticos import relatorio_diagnostico
from src.servicos.historico_empresas import (
    estatisticas,
    limpar_historico,
    listar_historico,
)
from src.ui.tema import criar_botao

ROTULOS_STATUS = {
    "": "Todos os estados",
    "extraida": "Extraída",
    "importada": "Importada",
    "duplicada": "Já existente",
    "descartada": "Descartada",
    "falha": "Falha",
    "encontrada": "Encontrada",
}


class DialogoHistorico(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("dialogHistorico")
        self.setWindowTitle("Histórico de empresas")
        self.setMinimumSize(980, 580)
        self.resize(1120, 660)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel("Histórico de empresas")
        titulo.setObjectName("tituloSecao")
        descricao = QLabel(
            "Cada empresa mostra o último estado conhecido e o motivo de descartes ou falhas."
        )
        descricao.setObjectName("descricaoSecao")
        descricao.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(descricao)

        barra = QHBoxLayout()
        self.resumo = QLabel()
        self.resumo.setObjectName("descricaoSecao")
        self.filtro = QComboBox()
        for valor, rotulo in ROTULOS_STATUS.items():
            self.filtro.addItem(rotulo, valor)
        self.filtro.currentIndexChanged.connect(self._carregar)
        atualizar = criar_botao("Atualizar", "secundario", compacto=True)
        atualizar.clicked.connect(self._carregar)
        limpar = criar_botao("Limpar histórico", "perigo", compacto=True)
        limpar.clicked.connect(self._confirmar_limpeza)
        diagnostico = criar_botao("Copiar diagnóstico", "secundario", compacto=True)
        diagnostico.clicked.connect(self._copiar_diagnostico)
        barra.addWidget(self.resumo, stretch=1)
        barra.addWidget(self.filtro)
        barra.addWidget(atualizar)
        barra.addWidget(diagnostico)
        barra.addWidget(limpar)
        layout.addLayout(barra)

        self.tabela = QTableWidget(0, 8)
        self.tabela.setHorizontalHeaderLabels(
            ["Estado", "Empresa", "Telefone", "Site", "Consulta", "Região", "Última vez", "Motivo"]
        )
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.tabela.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.setShowGrid(False)
        self.tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.cellDoubleClicked.connect(self._abrir_maps)
        layout.addWidget(self.tabela, stretch=1)

        rodape = QHBoxLayout()
        dica = QLabel("Dê duplo clique em uma linha para abrir a empresa no Google Maps.")
        dica.setObjectName("descricaoSecao")
        fechar = criar_botao("Fechar", "secundario", compacto=True)
        fechar.clicked.connect(self.accept)
        rodape.addWidget(dica, stretch=1)
        rodape.addWidget(fechar)
        layout.addLayout(rodape)
        self._carregar()

    def _carregar(self) -> None:
        filtro = str(self.filtro.currentData() or "")
        registros = listar_historico(filtro)
        totais = estatisticas()
        self.resumo.setText(
            f"{totais['total']} empresa(s) — {totais['importada']} importada(s), "
            f"{totais['duplicada']} já existente(s), {totais['falha']} falha(s)"
        )
        self.tabela.setRowCount(len(registros))
        for linha, registro in enumerate(registros):
            valores = [
                ROTULOS_STATUS.get(registro.status, registro.status.title()),
                registro.nome or "Empresa ainda não identificada",
                registro.telefone or "—",
                registro.site or "—",
                registro.consulta or "—",
                registro.local or "—",
                registro.ultima_vista.replace("T", " ")[:16],
                registro.motivo or "—",
            ]
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setData(Qt.ItemDataRole.UserRole, registro.url_maps)
                item.setToolTip(valor)
                self.tabela.setItem(linha, coluna, item)

    def _abrir_maps(self, linha: int, _coluna: int) -> None:
        item = self.tabela.item(linha, 0)
        url = str(item.data(Qt.ItemDataRole.UserRole) or "") if item else ""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _confirmar_limpeza(self) -> None:
        resposta = QMessageBox.question(
            self,
            "Limpar histórico",
            "Remover todo o histórico local de empresas? Os leads do WebRP não serão alterados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta == QMessageBox.StandardButton.Yes:
            limpar_historico()
            self._carregar()

    def _copiar_diagnostico(self) -> None:
        QApplication.clipboard().setText(relatorio_diagnostico())
        QMessageBox.information(
            self,
            "Diagnóstico copiado",
            "As informações técnicas foram copiadas. Senhas e credenciais não são incluídas.",
        )
