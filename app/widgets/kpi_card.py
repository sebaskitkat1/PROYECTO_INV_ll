"""Tarjeta KPI reutilizable (usada en Dashboard e Inventario)."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app import styles


class KpiCard(QFrame):
    """
    Tarjeta con una etiqueta, un valor grande y, opcionalmente, una
    variación porcentual (delta) respecto al día anterior.

    Si se pasa ``on_click``, la tarjeta se comporta como un botón y
    navega a otra pantalla (igual que en la versión web).
    """

    def __init__(
        self,
        label: str,
        value: str,
        delta: Optional[str] = None,
        delta_positive: bool = True,
        accent: str = styles.PRIMARY,
        on_click: Optional[Callable[[], None]] = None,
        background: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setStyleSheet(self.styleSheet())  # asegura que el QSS por rol se aplique
        if background:
            self.setStyleSheet(f"QFrame[role='card'] {{ background-color: {background}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        label_widget = QLabel(label.upper())
        label_widget.setProperty("role", "cardLabel")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setProperty("role", "cardValue")
        value_widget.setStyleSheet(f"color: {accent};")
        layout.addWidget(value_widget)

        if delta:
            arrow = "\u2191" if delta_positive else "\u2193"
            color = styles.SUCCESS if delta_positive else styles.DANGER
            delta_widget = QLabel(f"{arrow} {delta} vs ayer")
            delta_widget.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 600;")
            layout.addWidget(delta_widget)

        if on_click:
            self.setCursor(Qt.PointingHandCursor)
            self._on_click = on_click
        else:
            self._on_click = None

    def mousePressEvent(self, event):  # noqa: N802 (nombre requerido por Qt)
        if self._on_click:
            self._on_click()
        super().mousePressEvent(event)
