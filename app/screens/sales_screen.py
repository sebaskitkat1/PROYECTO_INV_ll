"""Pantalla de analisis de ventas: filtros, tabla e ingresos por categoria."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
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
