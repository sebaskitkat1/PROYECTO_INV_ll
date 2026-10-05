"""
Cosecha — sistema visual fresco y minimalista.

Papel verdoso, tinta bosque y un solo acento menta.
Sin azules corporativos, sin sombras duras, sin mayusculas gritadas.
"""

# --- base fresca -------------------------------------------------------

PAPER = "#F3F6EF"          # fondo app
SURFACE = "#FFFFFF"        # tarjetas / inputs
SURFACE_WARM = "#FAFCF6"   # tarjeta secundaria
INK = "#1D2A1F"            # texto principal
MUTED = "#5D7060"          # texto secundario
FAINT = "#A9BCA9"          # terciario / decoracion
LINE = "#DCE5D6"           # bordes suaves
LINE_SOFT = "#E8EEE3"

VERDE = "#2C5233"          # primario (botones, texto fuerte)
VERDE_HOVER = "#3B6340"

MENTA = "#4C9A5F"          # unico acento
MENTA_SOFT = "#DDEBD9"     # fondo activo
MENTA_LINE = "#B7D4B4"

SAGE = "#5B7A5A"
SAGE_BG = "#EAF0E8"
CLAY = "#A83E2A"
CLAY_BG = "#F8E8E2"
HONEY = "#8A6A1B"
HONEY_BG = "#F7F0D9"

# --- aliases compat (codigo viejo que aun usa los nombres anteriores) ---

PRIMARY = VERDE
PRIMARY_HOVER = VERDE_HOVER
LIGHT_BLUE = MENTA_SOFT
LIGHT_BLUE_BORDER = MENTA_LINE

TEXT_DARK = INK
TEXT_GRAY = MUTED
TEXT_LIGHT_GRAY = FAINT

BORDER = LINE
BG_WHITE = SURFACE
BG_LIGHT = LINE_SOFT
BG_LIGHTER = SURFACE_WARM

SUCCESS = SAGE
SUCCESS_BG = SAGE_BG
DANGER = CLAY
DANGER_BG = CLAY_BG
WARNING = HONEY
WARNING_BG = HONEY_BG

FONT_FAMILY = "Segoe UI Variable, Segoe UI, Inter, system-ui, sans-serif"

# paleta para matplotlib (verdes, sin azul)
CHART_COLORS = [VERDE, MENTA, SAGE, "#7C8B7A", HONEY, CLAY]
CHART_GRID = "#E4EADB"

GLOBAL_STYLESHEET = f"""
QWidget {{
    font-family: {FONT_FAMILY};
    color: {INK};
    background-color: {PAPER};
    font-size: 13px;
}}

QLabel {{
    background-color: transparent;
}}

QMainWindow {{
    background-color: {PAPER};
}}

/* Titulos: tinta, no azul, peso 600 */
QLabel[role="pageTitle"] {{
    font-size: 14px;
    font-weight: 600;
    color: {INK};
}}
QLabel[role="pageSubtitle"] {{
    font-size: 12px;
    color: {MUTED};
}}
QLabel[role="sectionTitle"] {{
    font-size: 20px;
    font-weight: 600;
    color: {INK};
}}
QLabel[role="cardLabel"] {{
    font-size: 12px;
    font-weight: 500;
    color: {MUTED};
}}
QLabel[role="cardValue"] {{
    font-size: 28px;
    font-weight: 600;
    color: {INK};
}}
QLabel[role="micro"] {{
    font-size: 11px;
    color: {FAINT};
}}

/* Inputs: frescos, foco menta */
QLineEdit {{
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0 12px;
    font-size: 13px;
    background-color: {SURFACE};
    min-height: 34px;
}}
QLineEdit:focus {{
    border: 1px solid {MENTA};
    background-color: {SURFACE};
}}

QComboBox {{
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0 10px;
    font-size: 12.5px;
    background-color: {SURFACE};
    min-height: 32px;
}}
QComboBox:hover {{
    border: 1px solid {MENTA_LINE};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    selection-background-color: {MENTA_SOFT};
    selection-color: {INK};
    outline: none;
}}

/* Botones: 34px, sentence case, sin gritar */
QPushButton {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 10px;
    font-size: 12.5px;
    font-weight: 600;
    padding: 0 14px;
    min-height: 34px;
}}
QPushButton[role="primary"] {{
    background-color: {VERDE};
    color: #F2F8F0;
    border: none;
}}
QPushButton[role="primary"]:hover {{
    background-color: {VERDE_HOVER};
}}
QPushButton[role="primary"]:disabled {{
    background-color: #B7C6B2;
    color: #F2F8F0;
}}
QPushButton[role="secondary"] {{
    background-color: #E3EBDC;
    color: {INK};
    border: none;
}}
QPushButton[role="secondary"]:hover {{
    background-color: #D5E2CC;
}}
QPushButton[role="outline"] {{
    background-color: {SURFACE};
    color: {INK};
    border: 1px solid {LINE};
}}
QPushButton[role="outline"]:hover {{
    border: 1px solid {MENTA};
    color: {VERDE};
    background-color: {SURFACE_WARM};
}}
QPushButton[role="ghost"] {{
    background-color: transparent;
    color: {MUTED};
    border: none;
    min-height: 30px;
}}
QPushButton[role="ghost"]:hover {{
    color: {INK};
    background-color: #E3EBDC;
}}

/* Navegacion segmentada */
QFrame[role="segNav"] {{
    background-color: #E3EBDC;
    border: none;
    border-radius: 999px;
}}
QPushButton[role="nav"] {{
    background-color: transparent;
    color: {MUTED};
    border: none;
    padding: 0 13px;
    border-radius: 999px;
    min-height: 30px;
    font-weight: 500;
}}
QPushButton[role="nav"]:hover {{
    color: {INK};
}}
QPushButton[role="navActive"] {{
    background-color: {SURFACE};
    color: {INK};
    border: none;
    padding: 0 13px;
    border-radius: 999px;
    min-height: 30px;
    font-weight: 600;
}}
QPushButton[role="link"] {{
    background-color: transparent;
    color: {MUTED};
    border: none;
    font-weight: 500;
}}
QPushButton[role="link"]:hover {{
    color: {INK};
    background-color: transparent;
}}

/* Tarjetas: radio amplio, borde suave fino, sin sombra */
QFrame[role="card"] {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 14px;
}}
QFrame[role="filterBar"] {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 14px;
}}
QFrame[role="infoBanner"] {{
    background-color: {SURFACE_WARM};
    border: 1px solid {LINE};
    border-radius: 12px;
}}
QFrame[role="alertDanger"] {{
    background-color: {CLAY_BG};
    border: 1px solid #E5BEB2;
    border-radius: 12px;
}}
QFrame[role="topbar"] {{
    background-color: {SURFACE};
    border-bottom: 1px solid {LINE};
}}

/* Login card */
QFrame[role="loginCard"] {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 18px;
}}

/* Tablas: encabezado invisible, filas con hairline */
QTableWidget {{
    border: 1px solid {LINE};
    border-radius: 12px;
    background-color: {SURFACE};
    gridline-color: {LINE_SOFT};
    font-size: 12.5px;
    selection-background-color: {MENTA_SOFT};
    selection-color: {INK};
    alternate-background-color: {SURFACE};
    outline: none;
}}
QHeaderView::section {{
    background-color: {SURFACE};
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
    padding: 10px;
    border: none;
    border-bottom: 1px solid {LINE};
}}
QTableWidget::item {{
    padding: 0 10px;
    border-bottom: 1px solid {LINE_SOFT};
}}
QTableWidget::item:selected {{
    background-color: {MENTA_SOFT};
}}

QScrollArea {{
    border: none;
    background-color: {PAPER};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: #BFD0B6;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
