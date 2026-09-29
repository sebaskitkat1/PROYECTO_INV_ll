"""Pantalla de prediccion de demanda a 30 dias."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import analytics, mock_data
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar


class PredictionScreen(QWidget):
    """Pantalla de prediccion de demanda basada en datos historicos."""

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
                title="Pronóstico",
                subtitle="",
                active_screen="prediction",
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

        content_layout.addWidget(self._build_line_chart_card())
        content_layout.addWidget(self._build_table_card())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # -- grafica historico vs prediccion -----------------------------------

    def _build_line_chart_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("Histórico y pronóstico · 30 días")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        layout.addWidget(title)

        canvas = MplCanvas(height=3.2)
        # historico del mock, futuro calculado con promedio + tendencia
        base = mock_data.get_prediction_data()
        dias = [d["dia"] for d in base]
        historico = [d["historico"] for d in base]
        hist_vals = [float(v) for v in historico if v is not None]
        fut_labels = [d["dia"] for d in base if d["historico"] is None]
        fut_vals = analytics.forecast_values(hist_vals, len(fut_labels))
        prediccion: list[float | None] = []
        it = iter(fut_vals)
        for d in base:
            if d["historico"] is None:
                prediccion.append(next(it))
            elif d["dia"] == "Hoy":
                prediccion.append(d["historico"])
            else:
                prediccion.append(None)

        x = list(range(len(dias)))
        canvas.axes.plot(
            x, historico, color=styles.ESPRESSO, linewidth=2.2, marker="o", markersize=4, label="Histórico"
        )
        canvas.axes.plot(
            x, prediccion, color=styles.CARAMEL, linewidth=2, linestyle="--",
            marker="o", markersize=4, label="Pronóstico",
        )
        canvas.axes.set_xticks(x)
        canvas.axes.set_xticklabels(dias, rotation=40, fontsize=7, ha="right")
        canvas.axes.yaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.axes.legend(fontsize=8, frameon=False, loc="upper left")
        canvas.redraw()
        layout.addWidget(canvas)

        return card

    # -- tabla de productos predichos --------------------------------------

    def _build_table_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QFrame()
        header.setStyleSheet(f"background-color: {styles.SURFACE_WARM}; border-bottom: 1px solid {styles.LINE};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Qué esperar el próximo mes")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        header_layout.addWidget(title)
        layout.addWidget(header)

        columns = ["Producto", "Ventas Actuales", "Ventas Predichas", "Crecimiento Esperado"]
        # crecimiento repartido desde la tendencia global y el margen
        hist = [float(d["historico"]) for d in mock_data.get_prediction_data() if d["historico"] is not None]
        g30 = analytics.overall_growth(hist, 6)
        rows = analytics.product_forecast(mock_data.get_sales_detail(), g30, 5)

        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setFrameShape(QFrame.NoFrame)

        for r, row in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(row["nombre"]))
            table.setItem(r, 1, self._right_aligned(f"${row['actual']:,}"))

            predicho_item = self._right_aligned(f"${row['predicho']:,}")
            predicho_item.setForeground(QColor(styles.ESPRESSO))
            font = predicho_item.font()
            font.setBold(True)
            predicho_item.setFont(font)
            table.setItem(r, 2, predicho_item)

            crecimiento_item = self._right_aligned(f"+{row['crecimiento']}%")
            crecimiento_item.setForeground(QColor(styles.SAGE))
            font = crecimiento_item.font()
            font.setBold(True)
            crecimiento_item.setFont(font)
            table.setItem(r, 3, crecimiento_item)

        table.setMinimumHeight(min(40 * len(rows) + 40, 320))
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(table)

        return card

    @staticmethod
    def _right_aligned(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item
