"""Bitacora de accesos: intentos, resultado y equipo."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import repository
from app.data.db import DBError
from app.widgets.nav_bar import NavBar

COLUMNS = ["Fecha", "Usuario", "Correo", "Resultado", "Equipo"]


class BitacoraScreen(QWidget):
    """Lista los ultimos accesos registrados en la base."""

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        on_logout: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(
            NavBar(
                title="Bitácora",
                subtitle="",
                active_screen="bitacora",
                on_navigate=on_navigate,
                on_logout=on_logout,
                on_back=lambda: on_navigate("dashboard"),
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(14)

        self.table = self._build_table()
        content_layout.addWidget(self.table)

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setProperty("role", "outline")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self._reload)
        content_layout.addWidget(refresh_btn, alignment=Qt.AlignLeft)

        self.status_label = QLabel("")
        self.status_label.setProperty("role", "micro")
        content_layout.addWidget(self.status_label)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
        self._reload()

    @staticmethod
    def _build_table() -> QTableWidget:
        table = QTableWidget(0, len(COLUMNS))
        table.setHorizontalHeaderLabels(COLUMNS)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        return table

    def _reload(self) -> None:
        try:
            rows = repository.bitacora_rows()
        except DBError:
            rows = []
        self._populate(rows)
        fuente = "sin conexión" if not rows else repository.etiqueta_fuente()
        self.status_label.setText(f"{len(rows)} registros · {fuente}")

    def _populate(self, rows: list[dict]) -> None:
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(row["fecha"]))
            self.table.setItem(r, 1, QTableWidgetItem(row["usuario"]))
            self.table.setItem(r, 2, QTableWidgetItem(row["correo"]))
            resultado = QTableWidgetItem(row["resultado"])
            ok = row["resultado"] == "Correcto"
            resultado.setForeground(QColor(styles.SAGE if ok else styles.CLAY))
            self.table.setItem(r, 3, resultado)
            self.table.setItem(r, 4, QTableWidgetItem(row["equipo"]))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setMinimumHeight(min(40 * len(rows) + 40, 420) if rows else 120)
        self.table.setSortingEnabled(True)
