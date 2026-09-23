"""Pantalla de análisis de ventas: filtros, tabla y dispersión ingresos/margen."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
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
from app.data import mock_data
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar

PERIODOS = ["Hoy", "Últimos 7 días", "Último mes", "Rango custom"]
CATEGORIAS = ["Todos", "Bebidas", "Alimentos", "Postres"]


class SalesScreen(QWidget):
    """Pantalla de análisis de ventas por producto."""

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
                title="Análisis de Ventas",
                subtitle="Café Mi Favorito",
                active_screen="sales",
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
        content_layout.setSpacing(16)

        content_layout.addWidget(self._build_filter_bar())
        content_layout.addWidget(self._build_table())
        content_layout.addWidget(self._build_scatter_card())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # -- filtros ---------------------------------------------------------

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("role", "filterBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)

        layout.addWidget(self._filter_label("Período:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(PERIODOS)
        self.period_combo.setCurrentText("Últimos 7 días")
        layout.addWidget(self.period_combo)

        layout.addWidget(self._filter_label("Categoría:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIAS)
        layout.addWidget(self.category_combo)

        clear_btn = QPushButton("LIMPIAR FILTROS")
        clear_btn.setProperty("role", "outline")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._reset_filters)
        layout.addWidget(clear_btn)

        layout.addStretch()
        return bar

    @staticmethod
    def _filter_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {styles.TEXT_GRAY}; font-size: 12px; font-weight: 600;")
        return label

    def _reset_filters(self) -> None:
        self.period_combo.setCurrentText("Últimos 7 días")
        self.category_combo.setCurrentText("Todos")
        # Nota: los filtros aún no re-consultan los datos; ese es el
        # siguiente paso natural una vez que se conecte una fuente real.

    # -- tabla -------------------------------------------------------------

    def _build_table(self) -> QTableWidget:
        columns = ["Nombre Producto", "Cantidad Vendida", "Ingresos Totales", "Margen (%)", "Tendencia"]
        rows = mock_data.get_sales_detail()

        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)

        for r, row in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(row["nombre"]))
            table.setItem(r, 1, self._right_aligned(f"{row['cantidad']:,}"))
            table.setItem(r, 2, self._right_aligned(f"${row['ingresos']:,.2f}"))
            table.setItem(r, 3, self._right_aligned(f"{row['margen']}%"))

            trend_item = QTableWidgetItem("\u2191" if row["tendencia"] == "up" else "\u2193")
            trend_item.setTextAlignment(Qt.AlignCenter)
            color = styles.SUCCESS if row["tendencia"] == "up" else styles.DANGER
            trend_item.setForeground(QColor(color))
            table.setItem(r, 4, trend_item)

        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setMinimumHeight(min(40 * len(rows) + 40, 420))
        return table

    @staticmethod
    def _right_aligned(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    # -- gráfica de dispersión ---------------------------------------------

    def _build_scatter_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)

        title = QLabel("Ingresos vs Margen")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {styles.TEXT_DARK};")
        subtitle = QLabel("Cada punto es un producto. Arriba a la derecha = ideal.")
        subtitle.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_LIGHT_GRAY};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        canvas = MplCanvas(height=3)
        data = mock_data.get_sales_detail()
        canvas.axes.scatter(
            [d["ingresos"] for d in data],
            [d["margen"] for d in data],
            color=styles.PRIMARY,
            alpha=0.75,
            s=50,
        )
        canvas.axes.set_xlabel("Ingresos ($)", fontsize=9, color=styles.TEXT_LIGHT_GRAY)
        canvas.axes.set_ylabel("Margen (%)", fontsize=9, color=styles.TEXT_LIGHT_GRAY)
        canvas.axes.xaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.redraw()
        layout.addWidget(canvas)

        return card
