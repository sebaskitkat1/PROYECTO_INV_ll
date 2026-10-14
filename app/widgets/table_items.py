"""Items de tabla que ordenan por valor, no por texto."""
from __future__ import annotations

import unicodedata

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


class NumericItem(QTableWidgetItem):
    """Ordena por el numero en UserRole (ej. 95 < 842 < 1200)."""

    def __init__(self, texto: str, valor: float):
        super().__init__(texto)
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setData(Qt.UserRole, float(valor))

    def __lt__(self, other):
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except Exception:
            return super().__lt__(other)


class TextItem(QTableWidgetItem):
    """Ordena sin importar mayusculas ni acentos (Té junto a Te)."""

    def __init__(self, texto: str):
        super().__init__(texto)
        self.setData(Qt.UserRole, _sin_acentos(texto).casefold())

    def __lt__(self, other):
        try:
            return str(self.data(Qt.UserRole)) < str(other.data(Qt.UserRole))
        except Exception:
            return super().__lt__(other)
