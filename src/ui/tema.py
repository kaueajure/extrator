from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

ALTURA_BOTAO = 36
ALTURA_CAMPO = 36

FOLHA_ESTILO = """
/* ---- Shell admin (espelha admin.css) ---- */
QMainWindow, QWidget#adminShell {
    background: #f3f4f6;
    color: #1a1d24;
}

QScrollArea#adminScroll {
    background: transparent;
    border: none;
}

QWidget#adminScrollContents {
    background: transparent;
}

QWidget#adminArea {
    background: #f3f4f6;
}

QFrame#painelPrincipal {
    background: #f8f9fa;
    border: 1px solid #dde0e5;
    border-radius: 12px;
}

QWidget#adminPagina {
    background: transparent;
}

/* ---- Cabeçalho ---- */
QFrame#cabecalho {
    background: rgba(255, 255, 255, 0.96);
    border: none;
    border-bottom: 1px solid #dde0e5;
}

QWidget#cabecalhoLinha {
    background: transparent;
}

QLabel {
    background: transparent;
    color: #1a1d24;
}

QLabel#logotipoWeb {
    color: #1a1d24;
    font-size: 16px;
    font-weight: 680;
    letter-spacing: -0.04em;
}

QLabel#logotipoMarca {
    color: #3730e0;
    font-size: 16px;
    font-weight: 680;
    letter-spacing: -0.04em;
}

QLabel#etiquetaAdmin {
    color: #717680;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.04em;
    padding: 3px 7px;
    border: 1px solid #c9cdd4;
    border-radius: 5px;
}

QLabel#tituloPagina {
    color: #626873;
    font-size: 11px;
    font-weight: 600;
}

QFrame#headerDivisor {
    background: #dde0e5;
    max-width: 1px;
    min-width: 1px;
}

QLabel#usuarioAvatar {
    background: #dff7f1;
    color: #075d50;
    font-size: 10px;
    font-weight: 700;
    border-radius: 7px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    qproperty-alignment: AlignCenter;
}

QLabel#usuarioNome {
    color: #1a1d24;
    font-size: 11px;
    font-weight: 620;
}

QLabel#usuarioEmail {
    color: #747a84;
    font-size: 9px;
}

/* ---- Seções ---- */
QFrame#secao {
    background: #ffffff;
    border: 1px solid #dde0e5;
    border-radius: 10px;
}

QFrame#secaoInterna {
    background: transparent;
    border: none;
}

QLabel#tituloSecao {
    color: #1a1d24;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.015em;
}

QLabel#descricaoSecao {
    color: #626873;
    font-size: 11px;
}

QLabel#rotuloCampo {
    color: #4e535c;
    font-size: 11px;
    font-weight: 630;
}

QLabel#resumoSecao {
    color: #626873;
    font-size: 12px;
}

QLabel#feedbackOk {
    color: #0b826e;
    font-size: 12px;
    font-weight: 620;
    padding-top: 6px;
}

QLabel#feedbackErro {
    color: #b42318;
    font-size: 12px;
    font-weight: 620;
    padding-top: 6px;
}

/* ---- Campos ---- */
QLineEdit, QSpinBox, QComboBox {
    background: #ffffff;
    color: #1a1d24;
    border: 1px solid #c9cdd4;
    border-radius: 7px;
    min-height: 34px;
    max-height: 36px;
    padding: 0 10px;
    font-size: 12px;
    selection-background-color: #c8c5ff;
    selection-color: #171246;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #3730e0;
}

QLineEdit::placeholder {
    color: #747a84;
}

QSpinBox::up-button, QSpinBox::down-button {
    width: 18px;
    border: none;
    background: transparent;
}

QTextEdit#logs {
    background: #ffffff;
    color: #1a1d24;
    border: 1px solid #dde0e5;
    border-radius: 7px;
    font-family: "Geist Mono", "SFMono-Regular", "Consolas", "Ubuntu Mono", monospace;
    font-size: 11px;
    padding: 10px 12px;
    selection-background-color: #c8c5ff;
}

/* ---- Botões ---- */
QPushButton {
    min-height: 36px;
    max-height: 36px;
    padding: 0 14px;
    border-radius: 7px;
    font-size: 11px;
    font-weight: 630;
    border: 1px solid transparent;
    outline: none;
}

QWidget#grupoBotoes {
    background: transparent;
}

QWidget#grupoBotoes QPushButton {
    min-width: 0;
}

QPushButton#primario {
    background-color: #3730e0;
    color: #ffffff;
    border: 1px solid #2d27bd;
    min-width: 120px;
}

QPushButton#primario:hover {
    background-color: #2d27bd;
    border-color: #241fb0;
}

QPushButton#primario:pressed {
    background-color: #241fb0;
    border-color: #1c1890;
}

QPushButton#primario:disabled {
    background-color: #b6b3f2;
    color: #f5f4ff;
    border-color: #b6b3f2;
}

QPushButton#secundario {
    background-color: #ffffff;
    color: #242730;
    border: 1px solid #d2d5da;
    min-width: 0;
}

QPushButton#secundario:hover {
    background-color: #f8f9fa;
    border-color: #b8bcc4;
    color: #1a1d24;
}

QPushButton#secundario:pressed {
    background-color: #eef0f3;
    border-color: #a8adb6;
}

QPushButton#secundario:disabled {
    background-color: #f8f9fa;
    color: #a8adb6;
    border-color: #e4e6ea;
}

QPushButton#perigo {
    background-color: #ffffff;
    color: #b42318;
    border: 1px solid #fecdca;
    min-width: 100px;
}

QPushButton#perigo:hover {
    background-color: #fff0ed;
    border-color: #fda29b;
    color: #912018;
}

QPushButton#perigo:pressed {
    background-color: #ffe4e0;
    border-color: #f97066;
}

QPushButton#perigo:disabled {
    background-color: #fff8f7;
    color: #fda29b;
    border-color: #fee4e2;
}

QPushButton#sair {
    min-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0 9px;
    background: transparent;
    color: #737984;
    border: none;
    border-radius: 7px;
    font-weight: 600;
}

QPushButton#sair:hover {
    background: #eef0f3;
    color: #1a1d24;
}

QPushButton#sair:pressed {
    background: #e4e6ea;
}

QPushButton#chipSugestao {
    min-height: 32px;
    padding: 0 12px;
    background-color: #ffffff;
    color: #3730e0;
    border: 1px solid #c8c5ff;
    font-weight: 560;
}

QPushButton#chipSugestao:hover {
    background-color: #eeedff;
    border-color: #aba6ff;
}

QPushButton#chipSugestao:pressed {
    background-color: #e0deff;
}

/* ---- Alternador (Visível / Invisível) ---- */
QWidget#alternador {
    background: #eef0f3;
    border: 1px solid #d2d5da;
    border-radius: 8px;
    min-width: 200px;
    max-width: 240px;
}

QPushButton#alternadorOpcao {
    min-height: 32px;
    max-height: 32px;
    min-width: 0;
    padding: 0 10px;
    margin: 0;
    border: 1px solid transparent;
    border-radius: 6px;
    background: transparent;
    color: #626873;
    font-size: 11px;
    font-weight: 560;
}

QPushButton#alternadorOpcao:hover {
    background: #e4e6ea;
    color: #1a1d24;
}

QPushButton#alternadorOpcao:checked {
    background: #ffffff;
    color: #3730e0;
    border-color: #c8c5ff;
    font-weight: 640;
}

QPushButton#alternadorOpcao:disabled {
    background: transparent;
    color: #b8bcc4;
    border-color: transparent;
}

QPushButton#alternadorOpcao:checked:disabled {
    background: #f3f4f6;
    color: #8b90f5;
    border-color: #dde0e5;
}

/* ---- Sugestões / vazio ---- */
QFrame#painelSugestoes {
    background: #eeedff;
    border: 1px solid #c8c5ff;
    border-radius: 10px;
}

QFrame#popupSugestoes {
    background: #ffffff;
    border: 1px solid #dde0e5;
    border-radius: 10px;
}

QLabel#popupSugestoesTitulo {
    color: #626873;
    font-size: 10px;
    font-weight: 620;
    letter-spacing: 0.02em;
    padding: 2px 4px 4px 4px;
}

QListWidget#popupSugestoesLista {
    background: transparent;
    border: none;
    outline: none;
    color: #1a1d24;
    font-size: 12px;
}

QListWidget#popupSugestoesLista::item {
    padding: 8px 10px;
    border-radius: 6px;
    min-height: 28px;
}

QListWidget#popupSugestoesLista::item:hover,
QListWidget#popupSugestoesLista::item:selected {
    background: #eeedff;
    color: #3730e0;
}

QFrame#estadoVazio {
    background: #f8f9fa;
    border: 1px dashed #c9cdd4;
    border-radius: 10px;
}

QFrame#faixaGoogle {
    background: #f8f9fa;
    border: 1px solid #dde0e5;
    border-radius: 8px;
}

QFrame#barraRodape {
    background: transparent;
    border-top: 1px solid #eef0f3;
}

QFrame#barraResultados {
    background: transparent;
    border-bottom: 1px solid #eef0f3;
    padding-bottom: 8px;
}

QWidget#linhaOpcoes {
    background: transparent;
}

QFrame#faixaOpcoes {
    background: #f8f9fa;
    border: 1px solid #eef0f3;
    border-radius: 8px;
}

/* ---- Checkbox ---- */
QCheckBox#opcaoApp {
    spacing: 10px;
    color: #4e535c;
    font-size: 11px;
    font-weight: 500;
    min-height: 28px;
    padding: 4px 0;
}

QCheckBox#opcaoApp::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid #c9cdd4;
    background: #ffffff;
}

QCheckBox#opcaoApp::indicator:hover {
    border-color: #8b90f5;
}

QCheckBox#opcaoApp::indicator:checked {
    background: #3730e0;
    border-color: #3730e0;
    image: url(__CHECKBOX_CHECK__);
}

QCheckBox#opcaoApp::indicator:disabled {
    background: #f3f4f6;
    border-color: #dde0e5;
}

QCheckBox#opcaoApp::indicator:checked:disabled {
    background: #b6b3f2;
    border-color: #b6b3f2;
}

QCheckBox#opcaoApp:disabled {
    color: #a8adb6;
}

QCheckBox {
    spacing: 10px;
    color: #4e535c;
    font-size: 11px;
    min-height: 28px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid #c9cdd4;
    background: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #8b90f5;
}

QCheckBox::indicator:checked {
    background: #3730e0;
    border-color: #3730e0;
    image: url(__CHECKBOX_CHECK__);
}

QCheckBox::indicator:disabled {
    background: #f3f4f6;
    border-color: #dde0e5;
}

QCheckBox::indicator:checked:disabled {
    background: #b6b3f2;
    border-color: #b6b3f2;
}

QCheckBox:disabled {
    color: #a8adb6;
}

/* ---- Tabela ---- */
QTableWidget {
    background: #ffffff;
    color: #444a54;
    border: 1px solid #dde0e5;
    border-radius: 0;
    gridline-color: transparent;
    outline: none;
    alternate-background-color: #fcfcfd;
}

QTableWidget::item {
    padding: 8px 13px;
    border-top: 1px solid #dde0e5;
    color: #444a54;
    font-size: 11px;
}

QTableWidget::item:selected {
    background: #eeedff;
    color: #1a1d24;
}

QHeaderView::section {
    background: #f8f9fa;
    color: #6e747e;
    border: none;
    border-bottom: 1px solid #dde0e5;
    padding: 0 10px;
    min-height: 34px;
    max-height: 34px;
    font-size: 9px;
    font-weight: 620;
    letter-spacing: 0.04em;
}

QProgressBar {
    background: #eef0f3;
    border: none;
    border-radius: 4px;
    max-height: 8px;
}

QProgressBar::chunk {
    background: #3730e0;
    border-radius: 4px;
}

/* ---- Splitter / scroll ---- */
QSplitter::handle {
    background: #dde0e5;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #a8adb6;
    border-radius: 4px;
    min-height: 24px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ---- Login ---- */
QDialog#dialogLogin {
    background: #eceef1;
}

QFrame#loginPainel {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #dde0e5;
}

QFrame#loginContexto {
    background: #171a22;
    border-top-left-radius: 16px;
    border-bottom-left-radius: 16px;
}

QLabel#loginContextoWeb {
    color: #ffffff;
    font-size: 16px;
    font-weight: 680;
}

QLabel#loginContextoMarca {
    color: #70e1cb;
    font-size: 16px;
    font-weight: 680;
}

QLabel#loginContextoTitulo {
    color: #ffffff;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.025em;
}

QLabel#loginContextoTexto {
    color: #b9bdc7;
    font-size: 13px;
}

QFrame#loginAcessoTopo {
    background: transparent;
    border-bottom: 1px solid #dde0e5;
}

QLabel#loginAcessoEtiqueta {
    color: #777d86;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.04em;
}

QLabel#loginTitulo {
    color: #1a1d24;
    font-size: 26px;
    font-weight: 600;
    letter-spacing: -0.025em;
}

QLabel#loginSubtitulo {
    color: #626873;
    font-size: 12px;
}

QLabel#loginSeguranca {
    color: #737984;
    font-size: 10px;
    padding-top: 18px;
    border-top: 1px solid #dde0e5;
}
"""


_MARCADOR_CHECK: str | None = None


def _caminho_marcador_checkbox() -> str:
    global _MARCADOR_CHECK
    if _MARCADOR_CHECK is not None:
        return _MARCADOR_CHECK

    diretorio_cache = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.CacheLocation
    )
    cache = (
        Path(diretorio_cache)
        if diretorio_cache
        else Path.home() / ".cache" / "WebRP-Extrator"
    )
    cache.mkdir(parents=True, exist_ok=True)
    destino = cache / "checkbox-check.png"

    if not destino.exists():
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(0, 0, 0, 0))
        pintor = QPainter(pixmap)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        caneta = QPen(QColor("#ffffff"))
        caneta.setWidthF(2.2)
        caneta.setCapStyle(Qt.PenCapStyle.RoundCap)
        caneta.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pintor.setPen(caneta)
        pintor.drawLine(2, 7, 5, 10)
        pintor.drawLine(5, 10, 12, 3)
        pintor.end()
        pixmap.save(str(destino), "PNG")

    _MARCADOR_CHECK = destino.as_posix()
    return _MARCADOR_CHECK


def folha_estilo() -> str:
    return FOLHA_ESTILO.replace("__CHECKBOX_CHECK__", _caminho_marcador_checkbox())


def aplicar_fonte(app: QApplication) -> None:
    for familia in ("Geist", "Inter", "Segoe UI", "Ubuntu", "Cantarell", "sans-serif"):
        fonte = QFont(familia, 10)
        if familia in ("Segoe UI", "Ubuntu", "Cantarell", "sans-serif") or fonte.exactMatch():
            app.setFont(fonte)
            break


def configurar_entrada(widget: QLineEdit | QSpinBox) -> None:
    widget.setMinimumHeight(ALTURA_CAMPO)
    widget.setMaximumHeight(ALTURA_CAMPO)


def criar_botao(
    texto: str,
    estilo: str = "secundario",
    largura_minima: int | None = None,
    compacto: bool = False,
) -> QPushButton:
    botao = QPushButton(texto)
    botao.setObjectName(estilo)
    botao.setFixedHeight(32 if compacto else ALTURA_BOTAO)
    botao.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    botao.setCursor(Qt.CursorShape.PointingHandCursor)
    botao.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    if largura_minima:
        botao.setMinimumWidth(largura_minima)
    return botao


def criar_opcao(texto: str, tooltip: str = "") -> QCheckBox:
    opcao = QCheckBox(texto)
    opcao.setObjectName("opcaoApp")
    if tooltip:
        opcao.setToolTip(tooltip)
    return opcao


def criar_linha_opcoes(*opcoes: QCheckBox) -> QWidget:
    container = QFrame()
    container.setObjectName("faixaOpcoes")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(12, 6, 12, 6)
    layout.setSpacing(20)
    layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    for opcao in opcoes:
        layout.addWidget(opcao)
    layout.addStretch()
    return container


def criar_alternador(
    rotulo_esquerda: str,
    rotulo_direita: str,
    *,
    esquerda_ativa: bool = True,
) -> tuple[QWidget, QPushButton, QPushButton, QButtonGroup]:
    container = QWidget()
    container.setObjectName("alternador")
    container.setMinimumWidth(200)
    container.setMaximumWidth(240)
    container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(3, 3, 3, 3)
    layout.setSpacing(2)

    esquerda = QPushButton(rotulo_esquerda)
    direita = QPushButton(rotulo_direita)
    for botao in (esquerda, direita):
        botao.setObjectName("alternadorOpcao")
        botao.setCheckable(True)
        botao.setAutoDefault(False)
        botao.setDefault(False)
        botao.setFixedHeight(32)
        botao.setCursor(Qt.CursorShape.PointingHandCursor)
        botao.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    grupo = QButtonGroup(container)
    grupo.setExclusive(True)
    grupo.addButton(esquerda, 0)
    grupo.addButton(direita, 1)
    esquerda.setChecked(esquerda_ativa)
    direita.setChecked(not esquerda_ativa)

    layout.addWidget(esquerda, 1)
    layout.addWidget(direita, 1)
    return container, esquerda, direita, grupo


def criar_grupo_botoes(*botoes: QPushButton) -> QWidget:
    container = QWidget()
    container.setObjectName("grupoBotoes")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    for botao in botoes:
        layout.addWidget(botao)
    return container


def criar_barra_rodape() -> tuple[QFrame, QHBoxLayout]:
    barra = QFrame()
    barra.setObjectName("barraRodape")
    layout = QHBoxLayout(barra)
    layout.setContentsMargins(0, 8, 0, 0)
    layout.setSpacing(8)
    return barra, layout


def criar_barra_resultados() -> tuple[QFrame, QHBoxLayout]:
    barra = QFrame()
    barra.setObjectName("barraResultados")
    layout = QHBoxLayout(barra)
    layout.setContentsMargins(0, 0, 0, 8)
    layout.setSpacing(8)
    return barra, layout


def criar_logotipo() -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    web = QLabel("Web")
    web.setObjectName("logotipoWeb")
    marca = QLabel("RioPreto")
    marca.setObjectName("logotipoMarca")
    layout.addWidget(web)
    layout.addWidget(marca)
    return container


def criar_etiqueta_admin(texto: str) -> QLabel:
    etiqueta = QLabel(texto.upper())
    etiqueta.setObjectName("etiquetaAdmin")
    return etiqueta


def criar_secao(titulo: str, descricao: str = "", compacto: bool = True) -> tuple[QFrame, QVBoxLayout]:
    secao = QFrame()
    secao.setObjectName("secao")

    layout = QVBoxLayout(secao)
    if compacto:
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)
    else:
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

    cabecalho = QVBoxLayout()
    cabecalho.setSpacing(2 if compacto else 5)
    lbl_titulo = QLabel(titulo)
    lbl_titulo.setObjectName("tituloSecao")
    cabecalho.addWidget(lbl_titulo)
    if descricao:
        lbl_desc = QLabel(descricao)
        lbl_desc.setObjectName("descricaoSecao")
        lbl_desc.setWordWrap(True)
        cabecalho.addWidget(lbl_desc)
    layout.addLayout(cabecalho)
    return secao, layout


def criar_campo(rotulo: str, widget: QWidget) -> QWidget:
    container = QWidget()
    container.setObjectName("secaoInterna")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    label = QLabel(rotulo)
    label.setObjectName("rotuloCampo")
    layout.addWidget(label)
    layout.addWidget(widget)
    if isinstance(widget, (QLineEdit, QSpinBox)):
        configurar_entrada(widget)
    return container


def criar_barra_ferramentas() -> tuple[QWidget, QHBoxLayout]:
    barra = QWidget()
    barra.setObjectName("secaoInterna")
    layout = QHBoxLayout(barra)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    return barra, layout


def criar_pagina_admin() -> tuple[QWidget, QVBoxLayout]:
    pagina = QWidget()
    pagina.setObjectName("adminPagina")
    layout = QVBoxLayout(pagina)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)
    return pagina, layout


criar_painel = criar_secao
