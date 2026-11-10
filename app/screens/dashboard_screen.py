"""Pantalla principal: resumen del dia, KPIs y graficas generales."""
from __future__ import annotations

import datetime
from typing import Callable

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app import styles
from app.data import analytics, mock_data, repository
from app.data.async_loader import async_disponible, run_async
from app.data.db import DBError
from app.data.store import get_inventory
from app.widgets.chart_card import PreviewChartCard
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
        self.on_navigate = on_navigate

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(
            NavBar(
                title="Hoy",
                subtitle=self._subtitle(),
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

        # contenedores vacios: primero se pinta la pantalla, luego llegan los datos
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(14)
        content_layout.addLayout(self.kpi_grid)

        self.charts_row = QHBoxLayout()
        self.charts_row.setSpacing(16)
        content_layout.addLayout(self.charts_row)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

        self._load_dashboard()

    # -- carga de datos -------------------------------------------------

    def _load_dashboard(self) -> None:
        if not async_disponible():
            self._apply_dashboard(self._fetch_dashboard())
            return
        run_async(self, self._fetch_dashboard, self._apply_dashboard,
                  lambda _mensaje: self._apply_dashboard(self._fallback_dashboard()))

    @staticmethod
    def _fetch_dashboard() -> dict:
        try:
            kpis = repository.dashboard_kpis()
        except DBError:
            kpis = analytics.dashboard_kpis(
                mock_data.get_sales_detail(), mock_data.get_sales_last_7_days(), get_inventory()
            )
        try:
            sales_7 = repository.sales_last_7_days()
        except DBError:
            sales_7 = mock_data.get_sales_last_7_days()
        try:
            detalle = repository.sales_detail()
        except DBError:
            detalle = mock_data.get_sales_detail()
        try:
            inventario = repository.inventory_rows()
        except DBError:
            inventario = get_inventory()
        return {"kpis": kpis, "sales_7": sales_7,
                "detalle": detalle, "inventario": inventario}

    @staticmethod
    def _fallback_dashboard() -> dict:
        return {
            "kpis": analytics.dashboard_kpis(
                mock_data.get_sales_detail(), mock_data.get_sales_last_7_days(),
                get_inventory()),
            "sales_7": mock_data.get_sales_last_7_days(),
            "detalle": mock_data.get_sales_detail(),
            "inventario": get_inventory(),
        }

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _apply_dashboard(self, data: dict) -> None:
        self._clear_layout(self.kpi_grid)
        self._clear_layout(self.charts_row)

        kpis = data["kpis"]
        cards = [
            KpiCard(
                "Ventas hoy", kpis["ventas_hoy"]["valor"], kpis["ventas_hoy"]["delta"],
                kpis["ventas_hoy"]["positivo"], accent=styles.INK,
                on_click=lambda: self.on_navigate("sales"),
            ),
            KpiCard(
                "Precio por unidad", kpis["ticket_promedio"]["valor"], kpis["ticket_promedio"]["delta"],
                kpis["ticket_promedio"]["positivo"], accent=styles.INK,
                on_click=lambda: self.on_navigate("sales"),
            ),
            KpiCard(
                "Productos vendidos", kpis["productos_vendidos"]["valor"], kpis["productos_vendidos"]["delta"],
                kpis["productos_vendidos"]["positivo"], accent=styles.INK,
                on_click=lambda: self.on_navigate("sales"),
            ),
            KpiCard(
                "Stock en riesgo", kpis["stock_en_riesgo"]["valor"], accent=styles.CLAY,
                on_click=lambda: self.on_navigate("inventory"),
            ),
        ]
        for i, card in enumerate(cards):
            self.kpi_grid.addWidget(card, 0, i)

        self.charts_row.addWidget(self._sales_line_chart_card(data["sales_7"]), 1)
        self.charts_row.addWidget(self._top_products_chart_card(data["detalle"]), 1)
        self.charts_row.addWidget(self._coverage_chart_card(data["inventario"]), 1)

    # -- secciones -----------------------------------------------------

    def _sales_line_chart_card(self, data: list[dict]) -> PreviewChartCard:
        card = PreviewChartCard(
            "Ventas, últimos 7 días",
            "Días con venta en la última semana",
            draw=lambda c: self._draw_sales_line(c, data, expanded=False),
            expanded_draw=lambda c: self._draw_sales_line(c, data, expanded=True),
            canvas_height=2.3,
            expanded_height=5.2,
        )
        card.activated.connect(lambda: card.open_expanded(self))
        return card

    def _top_products_chart_card(self, detalle: list[dict]) -> PreviewChartCard:
        total = len(detalle)
        card = PreviewChartCard(
            "Lo más vendido",
            f"Top 5 de {total} productos" if total > 5 else f"{total} productos",
            draw=lambda c: self._draw_top_products(c, detalle, expanded=False),
            expanded_draw=lambda c: self._draw_top_products(c, detalle, expanded=True),
            canvas_height=2.3,
            expanded_height=5.2,
        )
        card.activated.connect(lambda: card.open_expanded(self))
        return card

    def _coverage_chart_card(self, inventario: list[dict]) -> PreviewChartCard:
        con_consumo = [i for i in inventario if i.get("diasAgotar") is not None]
        total = len(con_consumo)
        subtitle = (f"6 de {total} más urgentes" if total > 6
                    else f"{total} ingredientes con consumo")
        card = PreviewChartCard(
            "Cobertura de inventario",
            subtitle,
            draw=lambda c: self._draw_coverage(c, inventario, expanded=False),
            expanded_draw=lambda c: self._draw_coverage(c, inventario, expanded=True),
            canvas_height=2.3,
            expanded_height=max(5.2, 1.2 + 0.3 * total),
            expanded_scrollable=total > 14,
        )
        card.activated.connect(lambda: card.open_expanded(self))
        return card

    # -- dibujo de graficas (vista previa y ampliada) -------------------

    @staticmethod
    def _draw_sales_line(canvas: MplCanvas, data: list[dict], expanded: bool) -> None:
        canvas.clear()
        ax = canvas.axes
        days = [d["day"] for d in data]
        values = [float(d["ventas"]) for d in data]
        x = list(range(len(days)))
        ax.plot(
            x, values, color=styles.VERDE, linewidth=2.2,
            marker="o", markersize=5 if expanded else 3.5,
            markerfacecolor=styles.MENTA, markeredgecolor=styles.VERDE,
        )
        ax.set_xticks(x)
        ax.set_xticklabels(days, fontsize=9 if expanded else 7.5)
        ax.yaxis.set_major_formatter(MplCanvas.miles_formatter())
        ax.margins(y=0.22 if expanded else 0.12)
        if expanded and values:
            for xi, valor in zip(x, values):
                ax.annotate(
                    analytics.fmt_money(valor), (xi, valor),
                    textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=9, color=styles.MUTED,
                )
            promedio = sum(values) / len(values)
            ax.axhline(promedio, color=styles.FAINT, linestyle="--", linewidth=1)
            ax.annotate(
                f"Promedio {analytics.fmt_money(promedio)}",
                (x[0], promedio), textcoords="offset points", xytext=(4, 6),
                ha="left", fontsize=9, color=styles.MUTED,
            )
        canvas.redraw()

    @staticmethod
    def _draw_top_products(canvas: MplCanvas, detalle: list[dict], expanded: bool) -> None:
        canvas.clear()
        ax = canvas.axes
        cantidad = 15 if expanded else 5
        data = analytics.top_products(detalle, cantidad)
        products = [d["product"] for d in data][::-1]
        values = [float(d["ingresos"]) for d in data][::-1]
        colors = [styles.LINE] * (len(values) - 1) + [styles.MENTA] if values else []
        ax.barh(products, values, color=colors, height=0.62)
        ax.xaxis.set_major_formatter(MplCanvas.miles_formatter())
        ax.tick_params(axis="y", labelsize=9 if expanded else 8)
        if expanded and values:
            tope = max(values) or 1.0
            for y, valor in enumerate(values):
                ax.text(
                    valor + tope * 0.012, y, analytics.fmt_money(valor),
                    va="center", fontsize=9, color=styles.MUTED,
                )
            ax.set_xlim(0, tope * 1.18)
        canvas.redraw()

    @staticmethod
    def _draw_coverage(canvas: MplCanvas, inventario: list[dict], expanded: bool) -> None:
        canvas.clear()
        ax = canvas.axes
        items = [i for i in inventario if i.get("diasAgotar") is not None]
        # orden descendente: el de menor cobertura queda arriba en la barra
        items.sort(key=lambda i: float(i["diasAgotar"]), reverse=True)
        if not expanded:
            items = items[-6:]
        if not items:
            ax.text(0.5, 0.5, "Sin consumo registrado", ha="center", va="center",
                    fontsize=10, color=styles.MUTED, transform=ax.transAxes)
            canvas.redraw()
            return
        names = [i["nombre"].split("(")[0].strip() for i in items]
        values = [float(i["diasAgotar"]) for i in items]
        color_por_estado = {
            "critico": styles.CLAY,
            "advertencia": styles.HONEY,
            "optimo": styles.MENTA,
            "sin_minimo": styles.FAINT,
        }
        colors = [color_por_estado.get(i.get("estado"), styles.MENTA_SOFT) for i in items]
        ax.barh(names, values, color=colors, height=0.62)
        ax.set_xlabel("días de cobertura", fontsize=9, color=styles.MUTED)
        ax.tick_params(axis="y", labelsize=9 if expanded else 8)
        if expanded:
            tope = max(values) or 1.0
            for y, valor in enumerate(values):
                ax.text(
                    valor + tope * 0.012, y, analytics.fmt_qty(valor),
                    va="center", fontsize=9, color=styles.MUTED,
                )
            ax.set_xlim(0, tope * 1.14)
        canvas.redraw()

    @staticmethod
    def _subtitle() -> str:
        texto = DashboardScreen._today_label()
        try:
            datos = repository.data_origin()
        except DBError:
            return texto + " · ejemplo"
        if datos["total"]:
            if datos["pct_simulado"] >= 99.9:
                return texto + " · datos simulados"
            if datos["pct_simulado"] > 0:
                return texto + f" · {datos['pct_simulado']:.0f}% simulado"
        return texto

    @staticmethod
    def _today_label() -> str:
        today = datetime.date.today()
        dia = DIAS_ES[today.weekday()]
        mes = MESES_ES[today.month - 1]
        label = f"{dia}, {today.day} de {mes} de {today.year}"
        return label[0].upper() + label[1:]
