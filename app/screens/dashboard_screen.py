"""Pantalla principal: resumen del día, KPIs y gráficas generales."""
from __future__ import annotations

import datetime
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app import styles
from app.data import mock_data
from app.widgets.kpi_card import KpiCard
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar

DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


class DashboardScreen(QWidget):
    """Pantalla de inicio con el resumen del día y las gráficas clave."""

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
                title="Café Mi Favorito",
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
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(20)

        section_title = QLabel("Resumen del Día")
        section_title.setProperty("role", "sectionTitle")
        content_layout.addWidget(section_title)

        content_layout.addLayout(self._build_kpi_row(on_navigate))
        content_layout.addLayout(self._build_charts_row())
        content_layout.addStretch()

        footer = QLabel("Datos actualizados hace 2 horas · Sistema CaféData v1.0")
        footer.setStyleSheet(f"color: {styles.TEXT_LIGHT_GRAY}; font-size: 10px;")
        content_layout.addWidget(footer)

        scroll.setWidget(content)
        root.addWidget(scroll)

    # -- secciones -----------------------------------------------------

    def _build_kpi_row(self, on_navigate: Callable[[str], None]) -> QGridLayout:
        kpis = mock_data.get_kpis()
        grid = QGridLayout()
        grid.setSpacing(14)

        cards = [
            KpiCard(
                "Ventas Hoy", kpis["ventas_hoy"]["valor"], kpis["ventas_hoy"]["delta"],
                kpis["ventas_hoy"]["positivo"], accent=styles.PRIMARY,
                on_click=lambda: on_navigate("sales"),
            ),
            KpiCard(
                "Ticket Promedio", kpis["ticket_promedio"]["valor"], kpis["ticket_promedio"]["delta"],
                kpis["ticket_promedio"]["positivo"], accent=styles.PRIMARY,
                on_click=lambda: on_navigate("sales"),
            ),
            KpiCard(
                "Productos Vendidos", kpis["productos_vendidos"]["valor"], kpis["productos_vendidos"]["delta"],
                kpis["productos_vendidos"]["positivo"], accent=styles.PRIMARY,
                on_click=lambda: on_navigate("sales"),
            ),
            KpiCard(
                "Stock en Riesgo", kpis["stock_en_riesgo"]["valor"], accent=styles.DANGER,
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
        card = self._chart_card("Ventas Últimos 7 Días")
        canvas = MplCanvas(height=2.6)
        data = mock_data.get_sales_last_7_days()
        days = [d["day"] for d in data]
        values = [d["ventas"] for d in data]

        canvas.axes.plot(days, values, color=styles.PRIMARY, linewidth=2, marker="o", markersize=4)
        canvas.axes.set_ylabel("")
        canvas.axes.yaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.redraw()

        card.layout().addWidget(canvas)
        return card

    def _top_products_bar_chart_card(self) -> QFrame:
        card = self._chart_card("Top 5 Productos por Ingresos")
        canvas = MplCanvas(height=2.6)
        data = mock_data.get_top5_products()
        products = [d["product"] for d in data][::-1]
        values = [d["ingresos"] for d in data][::-1]
        colors = [styles.LIGHT_BLUE] * (len(values) - 1) + [styles.PRIMARY]

        canvas.axes.barh(products, values, color=colors)
        canvas.axes.xaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.axes.tick_params(axis="y", labelsize=8)
        canvas.redraw()

        card.layout().addWidget(canvas)
        return card

    @staticmethod
    def _chart_card(title: str) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {styles.TEXT_DARK};")
        layout.addWidget(title_label)
        return card

    @staticmethod
    def _today_label() -> str:
        today = datetime.date.today()
        dia = DIAS_ES[today.weekday()]
        mes = MESES_ES[today.month - 1]
        label = f"{dia}, {today.day} de {mes} de {today.year}"
        return label[0].upper() + label[1:]
