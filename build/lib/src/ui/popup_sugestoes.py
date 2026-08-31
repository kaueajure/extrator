from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class PopupSugestoes(QFrame):
    """Lista flutuante posicionada sob o campo de busca."""

    escolhida = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("popupSugestoes")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.rotulo = QLabel("Sugestões")
        self.rotulo.setObjectName("popupSugestoesTitulo")

        self.lista = QListWidget()
        self.lista.setObjectName("popupSugestoesLista")
        self.lista.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lista.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.lista.itemClicked.connect(self._item_clicado)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addWidget(self.rotulo)
        layout.addWidget(self.lista)

        self._ancora: QWidget | None = None

    def definir_ancora(self, widget: QWidget) -> None:
        self._ancora = widget

    def atualizar(self, sugestoes: list[str], origem: str = "") -> None:
        self.lista.clear()
        if not sugestoes:
            self.hide()
            return

        if origem == "gemini":
            self.rotulo.setText("Sugestões da IA — clique para usar")
        elif origem == "regras":
            self.rotulo.setText("Sugestões — clique para usar")
        else:
            self.rotulo.setText("Sugestões")

        for texto in sugestoes:
            item = QListWidgetItem(texto)
            item.setToolTip(texto)
            self.lista.addItem(item)

        altura = min(28 + len(sugestoes) * 32, 220)
        self.setFixedHeight(altura)
        self.mostrar_sob_ancora()

    def mostrar_sob_ancora(self) -> None:
        if not self._ancora or not self.lista.count():
            self.hide()
            return

        ancora = self._ancora
        ponto = ancora.mapToGlobal(ancora.rect().bottomLeft())
        largura = max(ancora.width(), 280)
        self.setFixedWidth(largura)

        tela = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if tela:
            geo = tela.availableGeometry()
            x = min(ponto.x(), geo.right() - largura - 8)
            y = ponto.y() + 2
            if y + self.height() > geo.bottom():
                y = ancora.mapToGlobal(ancora.rect().topLeft()).y() - self.height() - 2
            self.move(max(geo.left() + 8, x), max(geo.top() + 8, y))
        else:
            self.move(ponto.x(), ponto.y() + 2)

        self.show()
        self.raise_()

    def _item_clicado(self, item: QListWidgetItem) -> None:
        texto = item.text().strip()
        if texto:
            self.escolhida.emit(texto)
        self.hide()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
