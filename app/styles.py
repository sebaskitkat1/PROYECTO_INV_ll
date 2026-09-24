"""
CaféData — sistema visual cálido y minimalista.

Papel cálido, tinta espresso y un solo acento caramelo.
Sin azules corporativos, sin sombras duras, sin mayúsculas gritadas.
"""

# --- Base cálida -------------------------------------------------------

PAPER = "#F7F3ED"          # fondo app
SURFACE = "#FFFFFF"        # tarjetas / inputs
SURFACE_WARM = "#FDFBF7"   # tarjeta secundaria
INK = "#201914"            # texto principal
MUTED = "#8C7E71"          # texto secundario
FAINT = "#B8ABA0"          # terciario / placeholders
LINE = "#E9E0D5"           # bordes cálidos
LINE_SOFT = "#F1EAE0"

ESPRESSO = "#2A1E17"       # primario (botones, texto fuerte)
ESPRESSO_HOVER = "#3E2E23"

CARAMEL = "#C27A3A"        # único acento
CARAMEL_SOFT = "#F5E7D3"   # fondo activo
CARAMEL_LINE = "#E3C9A8"

SAGE = "#5B7A5A"
SAGE_BG = "#EAF0E8"
CLAY = "#A83E2A"
CLAY_BG = "#F8E8E2"
HONEY = "#8A6A1B"
HONEY_BG = "#F7F0D9"

# --- Aliases compat (el código viejo sigue funcionando, ahora cálido) ---

PRIMARY = ESPRESSO
PRIMARY_HOVER = ESPRESSO_HOVER
LIGHT_BLUE = CARAMEL_SOFT
LIGHT_BLUE_BORDER = CARAMEL_LINE

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

# Paleta para matplotlib (tierra, sin azul)
CHART_COLORS = [ESPRESSO, CARAMEL, SAGE, "#7A6A5A", HONEY, CLAY]
CHART_GRID = "#EFE7DA"

GLOBAL_STYLESHEET = f"""
QWidget {{
    font-family: {FONT_FAMILY};
    color: {INK};
    background-color: {PAPER};
    font-size: 13px;
}}

QMainWindow {{
    background-color: {PAPER};
}}

/* Títulos: tinta, no azul, peso 600 */
QLabel[role="pageTitle"] {{
    font-size: 14px;
    font-weight: 600;
    color: {INK};
    letter-spacing: 0px;
}}
QLabel[role="pageSubtitle"] {{
    font-size: 12px;
    color: {MUTED};
}}
QLabel[role="sectionTitle"] {{
    font-size: 20px;
    font-weight: 600;
    color: {INK};
    letter-spacing: -0.2px;
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
    letter-spacing: -0.5px;
}}
QLabel[role="micro"] {{
    font-size: 11px;
    color: {FAINT};
}}

/* Inputs: cálidos, foco caramelo */
QLineEdit {{
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 0 12px;
    font-size: 13px;
    background-color: {SURFACE};
    min-height: 34px;
}}
QLineEdit:focus {{
    border: 1px solid {CARAMEL};
    background-color: {SURFACE};
}}
QLineEdit::placeholder {{
    color: {FAINT};
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
    border: 1px solid {CARAMEL_LINE};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {SURFACE};
    border: 1px solid {LINE};
    selection-background-color: {CARAMEL_SOFT};
    selection-color: {INK};
    outline: none;
}}

/* Botones: 34px, sentence case, sin gritar */
QPushButton {{
    border-radius: 10px;
    font-size: 12.5px;
    font-weight: 600;
    padding: 0 14px;
    min-height: 34px;
}}
QPushButton[role="primary"] {{
    background-color: {ESPRESSO};
    color: #FFF8F0;
    border: none;
}}
QPushButton[role="primary"]:hover {{
    background-color: {ESPRESSO_HOVER};
}}
QPushButton[role="primary"]:disabled {{
    background-color: #C9BBAE;
    color: #FFF8F0;
}}
QPushButton[role="secondary"] {{
    background-color: #EFE7DA;
    color: {INK};
    border: none;
}}
QPushButton[role="secondary"]:hover {{
    background-color: #E6DAC7;
}}
QPushButton[role="outline"] {{
    background-color: {SURFACE};
    color: {INK};
    border: 1px solid {LINE};
}}
QPushButton[role="outline"]:hover {{
    border: 1px solid {CARAMEL};
    color: {ESPRESSO};
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
    background-color: #EFE7DA;
}}

/* Navegación segmentada */
QFrame[role="segNav"] {{
    background-color: #EFE7DA;
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

/* Tarjetas: radio amplio, borde cálido fino, sin sombra */
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
    selection-background-color: {CARAMEL_SOFT};
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
    background-color: {CARAMEL_SOFT};
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
    background: #D8CBB9;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
