"""Tarjeta KPI minimalista: valor tinta, delta en píldora suave."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app import styles


class KpiCard(QFrame):
    def __init__(
        self,
        label: str,
        value: str,
        delta: Optional[str] = None,
        delta_positive: bool = True,
        accent: str = styles.INK,
        on_click: Optional[Callable[[], None]] = None,
        background: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("role", "card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Etiqueta en minúsculas suaves, no gritada
        label_widget = QLabel(label.capitalize() if label.isupper() else label)
        label_widget.setProperty("role", "cardLabel")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setProperty("role", "cardValue")
        layout.addWidget(value_widget)

        if delta:
            pill = QLabel(f"{'Sube' if delta_positive else 'Baja'} {delta} · ayer")
            if delta in ("CSV",):
                pill.setText("Datos cargados")
            bg = styles.SAGE_BG if delta_positive else styles.CLAY_BG
            fg = styles.SAGE if delta_positive else styles.CLAY
            pill.setStyleSheet(
                f"background-color: {bg}; color: {fg}; font-size: 11px; font-weight: 600;"
                "border-radius: 999px; padding: 3px 9px;"
            )
            pill.setAlignment(Qt.AlignLeft)
            layout.addWidget(pill)

        if on_click:
            self.setCursor(Qt.PointingHandCursor)
            self._on_click = on_click
            self.setStyleSheet(
                "QFrame[role='card']:hover { border: 1px solid #D9C6AC; }"
            )
        else:
            self._on_click = None

    def mousePressEvent(self, event):  # noqa: N802 (nombre requerido por Qt)
        if self._on_click:
            self._on_click()
        super().mousePressEvent(event)
