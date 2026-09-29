"""Pantalla principal: resumen del dia, KPIs y graficas generales."""
from __future__ import annotations

import datetime
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app import styles
from app.data import analytics, mock_data
from app.data.store import get_inventory
from app.widgets.kpi_card import KpiCard
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar

DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


class DashboardScreen(QWidget):
    """Pantalla de inicio con el resumen del dia y las graficas clave."""

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
                title="Hoy",
                subtitle=self._today_label(),
                active_screen="dashboard",
                on_navigate=on_navigate,
                on_logout=on_logout,
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(18)

        section_title = QLabel("Resumen del día")
        section_title.setProperty("role", "sectionTitle")
        content_layout.addWidget(section_title)

        content_layout.addLayout(self._build_kpi_row(on_navigate))
        content_layout.addLayout(self._build_charts_row())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

    # -- secciones -----------------------------------------------------

    def _build_kpi_row(self, on_navigate: Callable[[str], None]) -> QGridLayout:
        # todo sale de los dicts: serie de 7 dias, detalle y stock compartido
        kpis = analytics.dashboard_kpis(
            mock_data.get_sales_detail(), mock_data.get_sales_last_7_days(), get_inventory()
        )
        grid = QGridLayout()
        grid.setSpacing(14)

        cards = [
            KpiCard(
                "Ventas hoy", kpis["ventas_hoy"]["valor"], kpis["ventas_hoy"]["delta"],
                kpis["ventas_hoy"]["positivo"], accent=styles.INK,
                on_click=lambda: on_navigate("sales"),
            ),
            KpiCard(
                "Ticket promedio", kpis["ticket_promedio"]["valor"], kpis["ticket_promedio"]["delta"],
                kpis["ticket_promedio"]["positivo"], accent=styles.INK,
                on_click=lambda: on_navigate("sales"),
            ),
            KpiCard(
                "Productos vendidos", kpis["productos_vendidos"]["valor"], kpis["productos_vendidos"]["delta"],
                kpis["productos_vendidos"]["positivo"], accent=styles.INK,
                on_click=lambda: on_navigate("sales"),
            ),
            KpiCard(
                "Stock en riesgo", kpis["stock_en_riesgo"]["valor"], accent=styles.CLAY,
                on_click=lambda: on_navigate("inventory"),
            ),
        ]
        for i, card in enumerate(cards):
            grid.addWidget(card, 0, i)
        return grid

    def _build_charts_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._sales_line_chart_card())
        row.addWidget(self._top_products_bar_chart_card())
        return row

    def _sales_line_chart_card(self) -> QFrame:
        card = self._chart_card("Ventas, últimos 7 días")
        canvas = MplCanvas(height=2.6)
        data = mock_data.get_sales_last_7_days()
        days = [d["day"] for d in data]
        values = [d["ventas"] for d in data]

        canvas.axes.plot(days, values, color=styles.ESPRESSO, linewidth=2.2, marker="o", markersize=4,
                         markerfacecolor=styles.CARAMEL, markeredgecolor=styles.ESPRESSO)
        canvas.axes.set_ylabel("")
        canvas.axes.yaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.redraw()

        card.layout().addWidget(canvas)
        return card

    def _top_products_bar_chart_card(self) -> QFrame:
        card = self._chart_card("Lo más vendido")
        canvas = MplCanvas(height=2.6)
        # top real por ingresos, no lista fija
        data = analytics.top_products(mock_data.get_sales_detail(), 5)
        products = [d["product"] for d in data][::-1]
        values = [d["ingresos"] for d in data][::-1]
        colors = [styles.LINE] * (len(values) - 1) + [styles.CARAMEL]

        canvas.axes.barh(products, values, color=colors, height=0.55)
        canvas.axes.xaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.axes.tick_params(axis="y", labelsize=8)
        canvas.redraw()

        card.layout().addWidget(canvas)
        return card

    @staticmethod
    def _chart_card(title: str, subtitle: str = "") -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        layout.addWidget(title_label)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
            layout.addWidget(sub)
        return card

    @staticmethod
    def _today_label() -> str:
        today = datetime.date.today()
        dia = DIAS_ES[today.weekday()]
        mes = MESES_ES[today.month - 1]
        label = f"{dia}, {today.day} de {mes} de {today.year}"
        return label[0].upper() + label[1:]
