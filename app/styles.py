"""
Paleta de colores y hoja de estilos (QSS) compartida por toda la aplicación.

Los valores replican la identidad visual del prototipo web original
(CaféData) para que la versión de escritorio se sienta consistente con
el diseño de referencia.
"""

# --- Paleta de colores -------------------------------------------------

PRIMARY = "#1F4E78"
PRIMARY_HOVER = "#2E5C8A"
LIGHT_BLUE = "#E8F0F7"
LIGHT_BLUE_BORDER = "#A9C5E0"

TEXT_DARK = "#333333"
TEXT_GRAY = "#666666"
TEXT_LIGHT_GRAY = "#999999"

BORDER = "#E0E0E0"
BG_WHITE = "#FFFFFF"
BG_LIGHT = "#F0F0F0"
BG_LIGHTER = "#F9F9F9"

SUCCESS = "#27AE60"
SUCCESS_BG = "#E8F8F5"
DANGER = "#E74C3C"
DANGER_BG = "#FADBD8"
WARNING = "#F39C12"
WARNING_BG = "#FEF5E7"

FONT_FAMILY = "Segoe UI, Arial, sans-serif"

# --- Hoja de estilos global (QSS) --------------------------------------

GLOBAL_STYLESHEET = f"""
QWidget {{
    font-family: {FONT_FAMILY};
    color: {TEXT_DARK};
    background-color: {BG_WHITE};
}}

QMainWindow {{
    background-color: {BG_WHITE};
}}

QLabel[role="pageTitle"] {{
    font-size: 15px;
    font-weight: 700;
    color: {PRIMARY};
}}

QLabel[role="pageSubtitle"] {{
    font-size: 10px;
    color: {TEXT_LIGHT_GRAY};
}}

QLabel[role="sectionTitle"] {{
    font-size: 16px;
    font-weight: 700;
    color: {TEXT_DARK};
}}

QLabel[role="cardLabel"] {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_GRAY};
}}

QLabel[role="cardValue"] {{
    font-size: 30px;
    font-weight: 700;
}}

QLineEdit {{
    border: 1px solid #CCCCCC;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    background-color: {BG_WHITE};
}}

QLineEdit:focus {{
    border: 1px solid {PRIMARY};
}}

QComboBox {{
    border: 1px solid #CCCCCC;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
    background-color: {BG_WHITE};
}}

QPushButton {{
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 16px;
}}

QPushButton[role="primary"] {{
    background-color: {PRIMARY};
    color: {BG_WHITE};
    border: none;
}}
QPushButton[role="primary"]:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton[role="primary"]:disabled {{
    background-color: {PRIMARY_HOVER};
}}

QPushButton[role="secondary"] {{
    background-color: {BG_LIGHT};
    color: {TEXT_DARK};
    border: none;
}}
QPushButton[role="secondary"]:hover {{
    background-color: #E0E0E0;
}}

QPushButton[role="outline"] {{
    background-color: transparent;
    color: {PRIMARY};
    border: 1px solid {PRIMARY};
}}
QPushButton[role="outline"]:hover {{
    background-color: {LIGHT_BLUE};
}}

QPushButton[role="nav"] {{
    background-color: transparent;
    color: {TEXT_GRAY};
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
}}
QPushButton[role="nav"]:hover {{
    background-color: {BG_LIGHT};
}}
QPushButton[role="navActive"] {{
    background-color: {LIGHT_BLUE};
    color: {PRIMARY};
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
    font-weight: 700;
}}

QPushButton[role="link"] {{
    background-color: transparent;
    color: {TEXT_GRAY};
    border: none;
    font-weight: 600;
}}
QPushButton[role="link"]:hover {{
    background-color: {BG_LIGHT};
    border-radius: 6px;
}}

QFrame[role="card"] {{
    background-color: {BG_WHITE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QFrame[role="filterBar"] {{
    background-color: {BG_LIGHTER};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QFrame[role="infoBanner"] {{
    background-color: {LIGHT_BLUE};
    border: 1px solid {LIGHT_BLUE_BORDER};
    border-radius: 8px;
}}

QTableWidget {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    font-size: 13px;
    selection-background-color: {LIGHT_BLUE};
    selection-color: {TEXT_DARK};
}}

QHeaderView::section {{
    background-color: {BG_LIGHT};
    color: {TEXT_DARK};
    font-size: 11px;
    font-weight: 700;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}

QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {BORDER};
}}

QScrollArea {{
    border: none;
}}

QStatusBar {{
    color: {TEXT_LIGHT_GRAY};
    font-size: 10px;
}}
"""
