"""Pantalla de analisis de ventas: filtros, tabla e ingresos por categoria."""
from __future__ import annotations

import datetime
from functools import partial
from typing import Callable

from matplotlib import dates as mdates
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import analytics, export_csv, mock_data, repository
from app.data.async_loader import async_disponible, run_async
from app.data.db import DBError
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar
from app.widgets.table_items import NumericItem, TextItem

CATEGORIAS = ["Todos", "Frutas", "Verduras", "Jugos", "Bebidas", "Snacks", "Abarrotes"]

# mapeo categoria para datos de ejemplo (mock no trae categoria).
CATEGORY_MAP = {
    "Mango": "Frutas",
    "Manzana Roja": "Frutas",
    "Uva": "Frutas",
    "Naranja": "Frutas",
    "Fresa": "Frutas",
    "Plátano": "Frutas",
    "Jitomate": "Verduras",
    "Jugo de Naranja": "Jugos",
    "Sandía": "Frutas",
    "Piña": "Frutas",
}


class SalesScreen(QWidget):
    """Pantalla de analisis de ventas por producto."""

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
                title="Ventas",
                subtitle="",
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
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(14)

        content_layout.addWidget(self._build_filter_bar())
        self.report = None
        content_layout.addWidget(self._build_report_card())
        self.table = self._build_table()
        content_layout.addWidget(self.table)
        self.category_card, self.category_canvas = self._build_category_card()
        content_layout.addWidget(self.category_card)
        self.status_label = QLabel("")
        self.status_label.setProperty("role", "micro")
        content_layout.addWidget(self.status_label)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

        self.all_rows = []
        if not async_disponible():
            self.all_rows = self._load_rows()
            self._refresh()
            self._populate_product_list()
        else:
            self.status_label.setText("Cargando ventas…")
            run_async(self, self._load_rows, self._apply_rows, self._on_load_error)

    # -- filtros ---------------------------------------------------------

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("role", "filterBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        layout.addWidget(self._filter_label("Categoría"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(CATEGORIAS)
        self.category_combo.currentTextChanged.connect(lambda _t: self._refresh())
        layout.addWidget(self.category_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar…")
        self.search_input.setFixedWidth(150)
        self.search_input.textChanged.connect(lambda _t: self._refresh())
        layout.addWidget(self.search_input)

        clear_btn = QPushButton("Limpiar")
        clear_btn.setProperty("role", "outline")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._reset_filters)
        layout.addWidget(clear_btn)

        export_btn = QPushButton("Exportar")
        export_btn.setProperty("role", "secondary")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_csv)
        layout.addWidget(export_btn)

        layout.addStretch()
        return bar

    @staticmethod
    def _filter_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 500;")
        return label

    def _reset_filters(self) -> None:
        self.category_combo.setCurrentText("Todos")
        if hasattr(self, "search_input"):
            self.search_input.clear()
        self._refresh()

    # -- reporte por producto y periodo ----------------------------------

    def _build_report_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Reporte por producto y periodo")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        layout.addWidget(title)
        subtitle = QLabel(
            "Elige uno o varios productos y un rango de fechas. Respeta el origen real/simulado.")
        subtitle.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(16)

        # izquierda: seleccion multiple de productos
        left = QVBoxLayout()
        left.setSpacing(6)
        left.addWidget(self._filter_label("Productos (vacío = todos)"))
        self.product_list = QListWidget()
        self.product_list.setMinimumWidth(220)
        self.product_list.setMaximumHeight(150)
        left.addWidget(self.product_list)
        select_row = QHBoxLayout()
        all_btn = QPushButton("Todos")
        all_btn.setProperty("role", "outline")
        all_btn.setCursor(Qt.PointingHandCursor)
        all_btn.clicked.connect(lambda: self._check_all_products(True))
        none_btn = QPushButton("Ninguno")
        none_btn.setProperty("role", "outline")
        none_btn.setCursor(Qt.PointingHandCursor)
        none_btn.clicked.connect(lambda: self._check_all_products(False))
        select_row.addWidget(all_btn)
        select_row.addWidget(none_btn)
        select_row.addStretch()
        left.addLayout(select_row)
        body.addLayout(left)

        # derecha: periodo, origen, totales y grafica
        right = QVBoxLayout()
        right.setSpacing(8)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(self._filter_label("Desde"))
        self.desde_edit = QDateEdit()
        self.desde_edit.setCalendarPopup(True)
        self.desde_edit.setDisplayFormat("yyyy-MM-dd")
        self.desde_edit.setDate(QDate.currentDate().addDays(-29))
        controls.addWidget(self.desde_edit)
        controls.addWidget(self._filter_label("Hasta"))
        self.hasta_edit = QDateEdit()
        self.hasta_edit.setCalendarPopup(True)
        self.hasta_edit.setDisplayFormat("yyyy-MM-dd")
        self.hasta_edit.setDate(QDate.currentDate())
        controls.addWidget(self.hasta_edit)
        controls.addWidget(self._filter_label("Origen"))
        self.origen_combo = QComboBox()
        self.origen_combo.addItem("Todos", None)
        self.origen_combo.addItem("Solo reales", "real")
        self.origen_combo.addItem("Solo simulados", "simulado")
        controls.addWidget(self.origen_combo)
        controls.addStretch()
        right.addLayout(controls)

        actions = QHBoxLayout()
        self.report_btn = QPushButton("Ver reporte")
        self.report_btn.setProperty("role", "primary")
        self.report_btn.setCursor(Qt.PointingHandCursor)
        self.report_btn.clicked.connect(self._generate_report)
        self.report_export_btn = QPushButton("Exportar CSV")
        self.report_export_btn.setProperty("role", "secondary")
        self.report_export_btn.setCursor(Qt.PointingHandCursor)
        self.report_export_btn.clicked.connect(self._export_report_csv)
        actions.addWidget(self.report_btn)
        actions.addWidget(self.report_export_btn)
        actions.addStretch()
        right.addLayout(actions)

        self.report_totals = QLabel("Elige productos y pulsa Ver reporte.")
        self.report_totals.setWordWrap(True)
        self.report_totals.setStyleSheet(f"font-size: 12.5px; color: {styles.INK};")
        right.addWidget(self.report_totals)

        self.report_canvas = MplCanvas(height=2.3)
        self.report_canvas.setMinimumHeight(230)
        right.addWidget(self.report_canvas)
        body.addLayout(right, stretch=1)
        layout.addLayout(body)

        self.report_table = QTableWidget(0, 4)
        self.report_table.setHorizontalHeaderLabels(
            ["Producto", "Unidades", "Ingresos", "Margen (%)"])
        self.report_table.verticalHeader().setVisible(False)
        self.report_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.report_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.report_table.setAlternatingRowColors(True)
        self.report_table.setMaximumHeight(160)
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.report_table)
        return card

    def _populate_product_list(self) -> None:
        if not hasattr(self, "product_list"):
            return
        marcados = set(self._selected_products())
        nombres = sorted({r["nombre"] for r in self.all_rows})
        self.product_list.blockSignals(True)
        self.product_list.clear()
        for nombre in nombres:
            item = QListWidgetItem(nombre)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if nombre in marcados else Qt.Unchecked)
            self.product_list.addItem(item)
        self.product_list.blockSignals(False)

    def _check_all_products(self, checked: bool) -> None:
        estado = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.product_list.count()):
            self.product_list.item(i).setCheckState(estado)

    def _selected_products(self) -> list[str]:
        if not hasattr(self, "product_list"):
            return []
        return [self.product_list.item(i).text()
                for i in range(self.product_list.count())
                if self.product_list.item(i).checkState() == Qt.Checked]

    def _report_dates(self):
        desde = self.desde_edit.date().toPython()
        hasta = self.hasta_edit.date().toPython()
        if hasta < desde:
            desde, hasta = hasta, desde
        return desde, hasta

    def _generate_report(self) -> None:
        productos = self._selected_products()
        desde, hasta = self._report_dates()
        origen = self.origen_combo.currentData()
        self.report_totals.setText("Generando reporte…")
        if not repository.activa():
            self._apply_report(self._mock_report(desde, hasta, productos, origen))
            return
        tarea = partial(repository.sales_report, desde, hasta,
                        productos or None, origen, comparar=True)
        if async_disponible():
            run_async(self, tarea, self._apply_report, self._on_report_error)
        else:
            try:
                self._apply_report(tarea())
            except DBError as exc:
                self._on_report_error(str(exc))

    def _mock_report(self, desde, hasta, productos: list[str], origen) -> dict:
        rows = [dict(r) for r in self.all_rows
                if not productos or r["nombre"] in productos]
        total = analytics.sales_totals(rows)
        return {
            "por_producto": rows,
            "por_dia": [{"fecha": hasta.isoformat(), "cantidad": total["unidades"],
                         "ingresos": total["ingresos"]}],
            "totales": total,
            "desde": desde,
            "hasta": hasta,
            "origen": origen,
            "anterior": None,
            "ejemplo": True,
        }

    def _on_report_error(self, mensaje: str) -> None:
        self.report_totals.setText(f"No se pudo generar el reporte: {mensaje}")

    @staticmethod
    def _comparison_text(total: dict, anterior: dict | None) -> str:
        """Variacion contra el mismo periodo del ano anterior, si hay datos."""
        if not anterior:
            return ""
        previo = float((anterior.get("totales") or {}).get("ingresos") or 0)
        actual = float(total.get("ingresos") or 0)
        if not previo:
            return " · sin ventas en el mismo periodo del año anterior"
        var = analytics.pct_change(actual, previo)
        return "" if var is None else f" · vs. año anterior {var:+.1f}%"

    def _apply_report(self, report: dict) -> None:
        self.report = report
        total = report.get("totales") or {}
        productos = report.get("por_producto") or []
        fuente = "ejemplo" if report.get("ejemplo") else repository.etiqueta_fuente()
        texto = (
            f"{len(productos)} productos · "
            f"{analytics.fmt_qty(float(total.get('unidades') or 0))} unidades · "
            f"{analytics.fmt_money(float(total.get('ingresos') or 0))} · "
            f"margen {float(total.get('margen_pond') or 0):.0f}% · {fuente}"
        )
        texto += self._comparison_text(total, report.get("anterior"))
        self.report_totals.setText(texto)
        self._populate_report_table(productos)
        self._draw_report_chart(report.get("por_dia") or [])

    def _populate_report_table(self, rows: list[dict]) -> None:
        self.report_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            nombre = TextItem(row["nombre"])
            nombre.setFlags(nombre.flags() & ~Qt.ItemIsEditable)
            self.report_table.setItem(r, 0, nombre)
            self.report_table.setItem(
                r, 1, NumericItem(analytics.fmt_qty(row["cantidad"]), row["cantidad"]))
            self.report_table.setItem(
                r, 2, NumericItem(f"${row['ingresos']:,.2f}", row["ingresos"]))
            self.report_table.setItem(
                r, 3, NumericItem(f"{row['margen']:.0f}%", row["margen"]))
        self.report_table.resizeColumnsToContents()
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

    def _draw_report_chart(self, por_dia: list[dict]) -> None:
        canvas = self.report_canvas
        canvas.clear()
        ax = canvas.axes
        puntos = []
        for d in por_dia:
            try:
                fecha = datetime.date.fromisoformat(str(d["fecha"])[:10])
            except ValueError:
                continue
            puntos.append((fecha, float(d.get("ingresos") or 0)))
        if not puntos:
            ax.text(0.5, 0.5, "Sin ventas en el periodo", ha="center", va="center",
                    fontsize=10, color=styles.MUTED, transform=ax.transAxes)
            canvas.redraw()
            return
        # eje de fechas real, no posiciones: un hueco de dias no se disimula
        xs, ys = [], []
        for i, (fecha, valor) in enumerate(puntos):
            if i and (fecha - puntos[i - 1][0]).days > analytics.GRAFICA_HUECO_DIAS:
                xs.append(puntos[i - 1][0] + datetime.timedelta(days=1))
                ys.append(float("nan"))
            xs.append(fecha)
            ys.append(valor)
        ax.plot(xs, ys, color=styles.VERDE, marker="o", linewidth=2)
        ax.fill_between(xs, ys, color=styles.MENTA_SOFT, alpha=0.35)
        if (xs[-1] - xs[0]).days <= 1:
            # un solo dia (o dos) no da rango al AutoDateLocator
            ax.set_xlim(xs[0] - datetime.timedelta(days=1),
                        xs[-1] + datetime.timedelta(days=1))
            ax.xaxis.set_major_locator(mdates.DayLocator())
        else:
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda x, _pos: analytics.etiqueta_corta(
                mdates.num2date(x).date())))
        ax.tick_params(axis="x", labelrotation=30, labelsize=8)
        ax.yaxis.set_major_formatter(MplCanvas.miles_formatter())
        ax.set_ylabel("ingresos", fontsize=9, color=styles.MUTED)
        ax.margins(x=0.02, y=0.15)
        canvas.redraw()

    def _export_report_csv(self) -> None:
        report = getattr(self, "report", None)
        if not report or not report.get("por_producto"):
            QMessageBox.information(
                self, "Exportar", "Genera primero el reporte con Ver reporte.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar reporte de ventas", "reporte_ventas.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            n = export_csv.guardar_csv(
                path, ["nombre", "categoria", "cantidad", "ingresos", "margen"],
                report["por_producto"])
        except export_csv.ExportError as exc:
            QMessageBox.warning(self, "Exportar", str(exc))
            return
        QMessageBox.information(self, "Exportar", f"Se guardaron {n} filas.")

    # -- datos -----------------------------------------------------------

    def _load_rows(self) -> list[dict]:
        try:
            return repository.sales_detail()
        except DBError:
            rows = []
            for r in mock_data.get_sales_detail():
                d = dict(r)
                d["categoria"] = CATEGORY_MAP.get(r["nombre"], "Frutas")
                rows.append(d)
            return rows

    def _apply_rows(self, rows: list[dict]) -> None:
        self.all_rows = rows
        self._refresh()
        self._populate_product_list()

    def _on_load_error(self, _mensaje: str) -> None:
        self._apply_rows([])

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        cat = self.category_combo.currentText() if hasattr(self, "category_combo") else "Todos"
        q = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        out = []
        for r in rows:
            if cat != "Todos" and r.get("categoria", "Frutas") != cat:
                continue
            if q and q not in r["nombre"].lower():
                continue
            out.append(r)
        return out

    def _refresh(self) -> None:
        if not hasattr(self, "table") or not hasattr(self, "all_rows"):
            return
        filtered = self._apply_filters(self.all_rows)
        self._populate_table(filtered)
        self._update_category_chart(filtered)
        # totales del filtro, no del mock fijo
        tot = analytics.sales_totals(filtered)
        self.status_label.setText(
            f"{len(filtered)} de {len(self.all_rows)} · "
            f"{analytics.fmt_money(tot['ingresos'])} · margen {tot['margen_pond']:.0f}% · "
            f"{repository.etiqueta_fuente()}"
        )

    def _export_csv(self) -> None:
        filtered = self._apply_filters(self.all_rows)
        if not filtered:
            QMessageBox.information(self, "Exportar", "No hay filas para exportar.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar ventas filtradas", "ventas_filtradas.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            n = export_csv.guardar_csv(
                path, ["nombre", "categoria", "cantidad", "ingresos", "margen", "tendencia"], filtered)
        except export_csv.ExportError as e:
            QMessageBox.warning(self, "Exportar", str(e))
            return
        QMessageBox.information(self, "Exportar", f"Se guardaron {n} filas.")

    # -- tabla -------------------------------------------------------------

    def _build_table(self) -> QTableWidget:
        columns = ["Nombre Producto", "Cantidad Vendida", "Ingresos Totales", "Margen (%)", "Tendencia"]
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setMinimumHeight(220)
        return table

    def _populate_table(self, rows: list[dict]) -> None:
        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            nombre_item = TextItem(row["nombre"])
            nombre_item.setFlags(nombre_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(r, 0, nombre_item)
            self.table.setItem(r, 1, NumericItem(analytics.fmt_qty(row["cantidad"]), row["cantidad"]))
            self.table.setItem(r, 2, NumericItem(f"${row['ingresos']:,.2f}", row["ingresos"]))
            self.table.setItem(r, 3, NumericItem(f"{row['margen']}%", row["margen"]))
            trend_item = QTableWidgetItem("+ " if row["tendencia"] == "up" else "- ")
            trend_item.setTextAlignment(Qt.AlignCenter)
            color = styles.SAGE if row["tendencia"] == "up" else styles.CLAY
            trend_item.setForeground(QColor(color))
            self.table.setItem(r, 4, trend_item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setMinimumHeight(min(40 * len(rows) + 40, 300) if rows else 120)
        self.table.setSortingEnabled(was_sorting)

    # -- grafica de ingresos por categoria ---------------------------------

    def _build_category_card(self):
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        title = QLabel("Ingresos por categoría")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        layout.addWidget(title)

        subtitle = QLabel("Del filtro actual; la barra verde es la categoría líder")
        subtitle.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
        layout.addWidget(subtitle)

        canvas = MplCanvas(height=2.8)
        canvas.setMinimumHeight(280)
        layout.addWidget(canvas)
        return card, canvas

    def _update_category_chart(self, rows: list[dict]) -> None:
        canvas = self.category_canvas
        canvas.clear()
        ax = canvas.axes
        data = analytics.revenue_by_category(rows)
        if not data:
            ax.text(0.5, 0.5, "Sin datos para el filtro", ha="center", va="center",
                    fontsize=10, color=styles.MUTED, transform=ax.transAxes)
            canvas.redraw()
            return
        names = [d["categoria"] for d in data]
        values = [d["ingresos"] for d in data]
        colors = [styles.LINE] * (len(values) - 1) + [styles.MENTA]
        bars = ax.barh(names, values, color=colors, height=0.62)
        ax.xaxis.set_major_formatter(MplCanvas.miles_formatter())
        ax.tick_params(axis="y", labelsize=9)
        tope = max(values) or 1.0
        for bar, valor in zip(bars, values):
            ax.text(
                bar.get_width() + tope * 0.012,
                bar.get_y() + bar.get_height() / 2,
                analytics.fmt_money(valor),
                va="center", fontsize=9, color=styles.MUTED,
            )
        ax.set_xlim(0, tope * 1.18)
        canvas.redraw()
