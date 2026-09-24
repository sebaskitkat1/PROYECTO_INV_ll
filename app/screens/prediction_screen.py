"""Pantalla de predicción de demanda a 30 días."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
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


class PredictionScreen(QWidget):
    """Pantalla de predicción de demanda basada en datos históricos."""

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
                subtitle="Próximos 30 días",
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

        content_layout.addWidget(self._build_info_banner())
        content_layout.addWidget(self._build_line_chart_card())
        content_layout.addWidget(self._build_table_card())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # -- banner informativo ----------------------------------------------

    def _build_info_banner(self) -> QFrame:
        banner = QFrame()
        banner.setProperty("role", "infoBanner")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 12, 16, 12)

        text = QLabel(
            "Estimación con los últimos 3 meses. Úsala para compras y turnos, no como cifra exacta."
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {styles.MUTED}; font-size: 12.5px;")

        layout.addWidget(text, stretch=1)
        return banner

    # -- gráfica histórico vs predicción -----------------------------------

    def _build_line_chart_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("Histórico y pronóstico · 30 días")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        subtitle = QLabel("Continua lo que ya vendiste, punteada lo esperado")
        subtitle.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        canvas = MplCanvas(height=3.2)
        data = mock_data.get_prediction_data()
        dias = [d["dia"] for d in data]
        historico = [d["historico"] for d in data]
        prediccion = [d["prediccion"] for d in data]

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
        subtitle = QLabel("Crecimiento por producto")
        subtitle.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        columns = ["Producto", "Ventas Actuales", "Ventas Predichas", "Crecimiento Esperado"]
        rows = mock_data.get_top_predicted()

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
