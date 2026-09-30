"""Pantalla de prediccion de demanda a 30 dias."""
from __future__ import annotations

import datetime
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
        # historico del mock con fecha real, futuro diario calculado
        hoy = datetime.date.today()
        hist = []
        for d in mock_data.get_prediction_data():
            f = analytics.parse_dia(d["dia"], hoy)
            if f is not None and d["historico"] is not None:
                hist.append((f, float(d["historico"])))
        hist.sort()
        futuro = analytics.forecast_daily(hist, 30)
        dias = [d for d, _ in hist] + [d for d, _ in futuro]
        historico = [v for _, v in hist] + [None] * len(futuro)
        prediccion = [None] * (len(hist) - 1) + [hist[-1][1]] + [v for _, v in futuro] if hist else [None] * len(dias)

        x = list(range(len(dias)))
        canvas.axes.plot(
            x, historico, color=styles.ESPRESSO, linewidth=2.2, marker="o", markersize=4, label="Histórico"
        )
        canvas.axes.plot(
            x, prediccion, color=styles.CARAMEL, linewidth=2, linestyle="--",
            marker="o", markersize=4, label="Pronóstico",
        )
        etiquetas = [analytics.etiqueta_corta(d) for d in dias]
        paso = 5
        canvas.axes.set_xticks(x[::paso])
        canvas.axes.set_xticklabels(etiquetas[::paso], rotation=30, fontsize=7, ha="right")
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

        # backtest: si el modelo no gana a lo simple, se avisa preliminar
        hoy = datetime.date.today()
        hist = []
        for d in mock_data.get_prediction_data():
            f = analytics.parse_dia(d["dia"], hoy)
            if f is not None and d["historico"] is not None:
                hist.append((f, float(d["historico"])))
        hist.sort()
        futuro = analytics.forecast_daily(hist, 30)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        total_30 = sum(v for _, v in futuro)

        header = QFrame()
        header.setStyleSheet(f"background-color: {styles.SURFACE_WARM}; border-bottom: 1px solid {styles.LINE};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Estimación preliminar" if not bt["gana"] else "Qué esperar el próximo mes")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        header_layout.addWidget(title)
        layout.addWidget(header)

        columns = ["Producto", "Ventas Actuales", "Ventas Predichas", "Crecimiento Esperado"]
        # reparto por participacion: la suma cuadra con el total pronosticado
        rows = analytics.product_forecast_share(mock_data.get_sales_detail(), total_30, 5)

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

            crecimiento_txt, crecimiento_color = self._crec_texto_color(row["crecimiento"])
            crecimiento_item = self._right_aligned(crecimiento_txt)
            crecimiento_item.setForeground(QColor(crecimiento_color))
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
    def _crec_texto_color(crec: float) -> tuple[str, str]:
        # signo siempre visible, color segun el signo (F02)
        return (f"{crec:+.1f}%", styles.SAGE if crec >= 0 else styles.CLAY)

    @staticmethod
    def _right_aligned(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item
