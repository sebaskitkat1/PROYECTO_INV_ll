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
                title="Predicción de Demanda",
                subtitle="Café Mi Favorito · Próximos 30 días",
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
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(16)

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
        layout.setContentsMargins(14, 10, 14, 10)

        icon = QLabel("\u2139")
        icon.setStyleSheet(f"color: {styles.PRIMARY}; font-size: 15px;")
        icon.setAlignment(Qt.AlignTop)
        text = QLabel(
            "Esta es una estimación basada en los últimos 3 meses de datos. "
            "Úsela como referencia para compras y planificación, no como certeza absoluta."
        )
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {styles.TEXT_GRAY}; font-size: 12px;")

        layout.addWidget(icon)
        layout.addWidget(text, stretch=1)
        return banner

    # -- gráfica histórico vs predicción -----------------------------------

    def _build_line_chart_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)

        title = QLabel("Demanda Histórica vs Predicción (30 días)")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {styles.TEXT_DARK};")
        subtitle = QLabel("Línea sólida = datos reales · Línea punteada = pronóstico")
        subtitle.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_LIGHT_GRAY};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        canvas = MplCanvas(height=3.2)
        data = mock_data.get_prediction_data()
        dias = [d["dia"] for d in data]
        historico = [d["historico"] for d in data]
        prediccion = [d["prediccion"] for d in data]

        x = list(range(len(dias)))
        canvas.axes.plot(
            x, historico, color=styles.PRIMARY, linewidth=2, marker="o", markersize=4, label="Histórico"
        )
        canvas.axes.plot(
            x, prediccion, color=styles.LIGHT_BLUE_BORDER, linewidth=2, linestyle="--",
            marker="o", markersize=4, label="Predicción (30 días)",
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
        header.setStyleSheet(f"background-color: {styles.BG_LIGHTER}; border-bottom: 1px solid {styles.BORDER};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        title = QLabel("Top Productos Predichos")
        title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {styles.TEXT_DARK};")
        subtitle = QLabel("Crecimiento esperado próximo mes")
        subtitle.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_LIGHT_GRAY};")
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
            predicho_item.setForeground(QColor(styles.PRIMARY))
            font = predicho_item.font()
            font.setBold(True)
            predicho_item.setFont(font)
            table.setItem(r, 2, predicho_item)

            crecimiento_item = self._right_aligned(f"\u2191 {row['crecimiento']}%")
            crecimiento_item.setForeground(QColor(styles.SUCCESS))
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
