"""Pantalla de gestión de inventario: existencias, rotación y curva ABC."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import mock_data
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar

ESTADO_CONFIG = {
    "optimo": (styles.SUCCESS_BG, styles.SUCCESS, "ÓPTIMO"),
    "advertencia": (styles.WARNING_BG, styles.WARNING, "ADVERTENCIA"),
    "critico": (styles.DANGER_BG, styles.DANGER, "CRÍTICO"),
}


class InventoryScreen(QWidget):
    """Pantalla de gestión de inventario y niveles de stock."""

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
                title="Gestión de Inventario",
                subtitle="Café Mi Favorito",
                active_screen="inventory",
                on_navigate=on_navigate,
                on_logout=on_logout,
                on_back=lambda: on_navigate("dashboard"),
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(18)

        content_layout.addLayout(self._build_summary_row())
        content_layout.addWidget(self._build_table())
        content_layout.addLayout(self._build_charts_row())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # -- resumen -------------------------------------------------------

    def _build_summary_row(self) -> QGridLayout:
        inventory = mock_data.get_inventory()
        total = len(inventory)
        en_riesgo = sum(1 for i in inventory if i["estado"] == "critico")
        optimo = sum(1 for i in inventory if i["estado"] == "optimo")

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.addWidget(self._summary_card("Total Productos (SKU)", str(total), styles.PRIMARY), 0, 0)
        grid.addWidget(
            self._summary_card("Stock Óptimo", str(optimo), styles.SUCCESS, styles.SUCCESS_BG), 0, 1
        )
        grid.addWidget(
            self._summary_card("En Riesgo (bajo stock)", str(en_riesgo), styles.DANGER, styles.DANGER_BG), 0, 2
        )
        return grid

    @staticmethod
    def _summary_card(label: str, value: str, accent: str, background: str | None = None) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        if background:
            card.setStyleSheet(f"QFrame {{ background-color: {background}; border: 1px solid {styles.BORDER}; border-radius: 8px; }}")
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        label_widget = QLabel(label.upper())
        label_widget.setAlignment(Qt.AlignCenter)
        label_widget.setStyleSheet(f"color: {accent}; font-size: 11px; font-weight: 700;")
        value_widget = QLabel(value)
        value_widget.setAlignment(Qt.AlignCenter)
        value_widget.setStyleSheet(f"color: {accent}; font-size: 30px; font-weight: 700;")
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return card

    # -- tabla -----------------------------------------------------------

    def _build_table(self) -> QTableWidget:
        columns = ["Nombre Producto", "Stock Actual", "Stock Mínimo", "Días Para Agotar", "Estado"]
        # Orden por defecto: crítico primero, igual que en el prototipo web.
        orden_estado = {"critico": 0, "advertencia": 1, "optimo": 2}
        rows = sorted(mock_data.get_inventory(), key=lambda r: orden_estado[r["estado"]])

        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)

        for r, row in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(row["nombre"]))
            table.setItem(r, 1, self._numeric_item(row["stockActual"]))
            table.setItem(r, 2, self._numeric_item(row["stockMinimo"]))

            dias_item = self._numeric_item(row["diasAgotar"], suffix=" días")
            if row["diasAgotar"] <= 5:
                dias_item.setForeground(QColor(styles.DANGER))
                font = dias_item.font()
                font.setBold(True)
                dias_item.setFont(font)
            table.setItem(r, 3, dias_item)

            bg, fg, label = ESTADO_CONFIG[row["estado"]]
            estado_item = QTableWidgetItem(label)
            estado_item.setTextAlignment(Qt.AlignCenter)
            estado_item.setBackground(QColor(bg))
            estado_item.setForeground(QColor(fg))
            font = estado_item.font()
            font.setBold(True)
            estado_item.setFont(font)
            table.setItem(r, 4, estado_item)

        table.setMinimumHeight(min(40 * len(rows) + 40, 420))
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setSortingEnabled(True)  # clic en encabezado = ordenar (punto de partida simple)
        table.sortByColumn(-1, Qt.AscendingOrder)  # sin ordenar por defecto: respeta el orden crítico-primero
        return table

    @staticmethod
    def _numeric_item(value, suffix: str = "") -> QTableWidgetItem:
        item = QTableWidgetItem(f"{value}{suffix}")
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setData(Qt.UserRole, value)
        return item

    # -- gráficas ----------------------------------------------------------

    def _build_charts_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._rotation_chart_card())
        row.addWidget(self._pareto_chart_card())
        return row

    def _rotation_chart_card(self) -> QFrame:
        card = self._chart_card("Rotación de Productos", "Días promedio en inventario")
        canvas = MplCanvas(height=2.6)
        data = mock_data.get_rotation_data()
        names = [d["nombre"] for d in data][::-1]
        values = [d["dias"] for d in data][::-1]
        canvas.axes.barh(names, values, color=styles.LIGHT_BLUE)
        canvas.axes.tick_params(axis="y", labelsize=8)
        canvas.redraw()
        card.layout().addWidget(canvas)
        return card

    def _pareto_chart_card(self) -> QFrame:
        card = self._chart_card("Análisis ABC (Pareto)", "Top productos por ingresos")
        canvas = MplCanvas(height=2.6)
        data = mock_data.get_pareto_data()
        names = [d["nombre"] for d in data]
        values = [d["ingresos"] for d in data]
        canvas.axes.bar(names, values, color=styles.PRIMARY)
        canvas.axes.yaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.axes.tick_params(axis="x", labelsize=7, rotation=15)
        canvas.redraw()
        card.layout().addWidget(canvas)
        return card

    @staticmethod
    def _chart_card(title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {styles.TEXT_DARK};")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_LIGHT_GRAY};")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return card
