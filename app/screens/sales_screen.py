"""Pantalla de análisis de ventas: filtros, tabla y dispersión ingresos/margen."""
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
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import mock_data
from app.data.app_state import AppState
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar

PERIODOS = ["Hoy", "Últimos 7 días", "Último mes", "Rango custom"]
CATEGORIAS = ["Todos", "Bebidas", "Alimentos", "Postres"]

# Mapeo categoría para datos de ejemplo (mock no trae categoría).
CATEGORY_MAP = {
    "Café Americano": "Bebidas",
    "Capuchino": "Bebidas",
    "Torta de Chocolate": "Postres",
    "Sandwich Club": "Alimentos",
    "Agua Mineral": "Bebidas",
    "Jugo Natural": "Bebidas",
    "Croissant": "Alimentos",
    "Té Negro": "Bebidas",
    "Pan Dulce": "Alimentos",
    "Frappé": "Bebidas",
}


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
                title="Ventas",
                subtitle="Por producto y margen",
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
        self.scatter_card, self.scatter_canvas = self._build_scatter_card()
        content_layout.addWidget(self.scatter_card)
        self.status_label = QLabel("")
        self.status_label.setProperty("role", "micro")
        content_layout.addWidget(self.status_label)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)

        self.all_rows = self._load_rows()
        self._refresh()

    # -- filtros ---------------------------------------------------------

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("role", "filterBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        layout.addWidget(self._filter_label("Período"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(PERIODOS)
        self.period_combo.setCurrentText("Últimos 7 días")
        self.period_combo.currentTextChanged.connect(lambda _t: self._refresh())
        layout.addWidget(self.period_combo)

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
        self.period_combo.setCurrentText("Últimos 7 días")
        self.category_combo.setCurrentText("Todos")
        if hasattr(self, "search_input"):
            self.search_input.clear()
        self._refresh()

    # -- datos -----------------------------------------------------------

    def _load_rows(self) -> list[dict]:
        """Filas normalizadas desde AppState.df o mock + categoría."""
        if AppState.has_data():
            try:
                mapped = self._rows_from_dataframe(AppState.df)
                if mapped:
                    return mapped
            except Exception:
                pass
        rows = []
        for r in mock_data.get_sales_detail():
            d = dict(r)
            d["categoria"] = CATEGORY_MAP.get(r["nombre"], "Bebidas")
            rows.append(d)
        return rows

    @staticmethod
    def _rows_from_dataframe(df) -> list[dict]:
        cols = {str(c).lower(): c for c in df.columns}
        def pick(*names):
            for n in names:
                if n in cols:
                    return cols[n]
            return None
        c_nom = pick("nombre", "producto", "product", "nombre_producto")
        c_cant = pick("cantidad", "cant", "qty", "cantidad_vendida", "unidades")
        c_ing = pick("ingresos", "total", "ventas", "monto", "importe", "ingresos_totales")
        c_cat = pick("categoria", "categoría", "category", "tipo")
        c_margen = pick("margen", "margen_pct", "margin")
        if c_nom is None:
            return []
        rows = []
        for _, r in df.iterrows():
            try:
                nombre = str(r[c_nom])
                cantidad = int(float(r[c_cant])) if c_cant else 0
                if c_ing:
                    ingresos = float(r[c_ing])
                elif c_cant and pick("precio", "price", "precio_unitario"):
                    ingresos = cantidad * float(r[pick("precio", "price", "precio_unitario")])
                else:
                    ingresos = 0.0
                margen = int(float(r[c_margen])) if c_margen else 55
                categoria = str(r[c_cat]) if c_cat else CATEGORY_MAP.get(nombre, "Bebidas")
                tendencia = "up" if ingresos >= 3000 else "down"
                rows.append({
                    "nombre": nombre, "cantidad": cantidad, "ingresos": ingresos,
                    "margen": margen, "tendencia": tendencia, "categoria": categoria,
                })
            except Exception:
                continue
        return rows

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        cat = self.category_combo.currentText() if hasattr(self, "category_combo") else "Todos"
        q = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        # Período: con mock (sin fechas) no altera valores; con CSV real que
        # traiga columna fecha se filtraría aquí. Se deja cableado para no
        # romper y se informa en el status.
        out = []
        for r in rows:
            if cat != "Todos" and r.get("categoria", "Bebidas") != cat:
                continue
            if q and q not in r["nombre"].lower():
                continue
            out.append(r)
        return out

    def _refresh(self) -> None:
        if not hasattr(self, "table") or not hasattr(self, "all_rows"):
            return
        # Recarga si se cargó un CSV después de abrir la pantalla
        if AppState.has_data():
            fresh = self._load_rows()
            # Solo reemplaza si cambió el tamaño (evita perder estado en cada tecla)
            if len(fresh) != len(self.all_rows):
                self.all_rows = fresh
        filtered = self._apply_filters(self.all_rows)
        self._populate_table(filtered)
        self._update_scatter(filtered)
        fuente = AppState.describe_source()
        periodo = self.period_combo.currentText()
        self.status_label.setText(
            f"{len(filtered)} de {len(self.all_rows)} productos · {fuente} · Período: {periodo}"
        )

    def _export_csv(self) -> None:
        import csv
        filtered = self._apply_filters(self.all_rows)
        if not filtered:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar ventas filtradas", "ventas_filtradas.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["nombre", "categoria", "cantidad", "ingresos", "margen", "tendencia"])
            w.writeheader()
            w.writerows(filtered)

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
            self.table.setItem(r, 0, QTableWidgetItem(row["nombre"]))
            self.table.setItem(r, 1, self._right_aligned(f"{row['cantidad']:,}"))
            self.table.setItem(r, 2, self._right_aligned(f"${row['ingresos']:,.2f}"))
            self.table.setItem(r, 3, self._right_aligned(f"{row['margen']}%"))
            trend_item = QTableWidgetItem("+ " if row["tendencia"] == "up" else "- ")
            trend_item.setTextAlignment(Qt.AlignCenter)
            color = styles.SAGE if row["tendencia"] == "up" else styles.CLAY
            trend_item.setForeground(QColor(color))
            self.table.setItem(r, 4, trend_item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setMinimumHeight(min(40 * len(rows) + 40, 420) if rows else 120)
        self.table.setSortingEnabled(was_sorting)

    @staticmethod
    def _right_aligned(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    # -- gráfica de dispersión ---------------------------------------------

    def _build_scatter_card(self):
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("Ingresos y margen")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        subtitle = QLabel("Arriba a la derecha, lo ideal")
        subtitle.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        canvas = MplCanvas(height=3)
        canvas.axes.set_xlabel("Ingresos", fontsize=9, color=styles.MUTED)
        canvas.axes.set_ylabel("Margen %", fontsize=9, color=styles.MUTED)
        canvas.axes.xaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        layout.addWidget(canvas)
        return card, canvas

    def _update_scatter(self, rows: list[dict]) -> None:
        self.scatter_canvas.axes.clear()
        # Reaplica estilo base (clear borra grid/spines del MplCanvas)
        self.scatter_canvas._style_axes(self.scatter_canvas.axes)
        self.scatter_canvas.axes.set_xlabel("Ingresos", fontsize=9, color=styles.MUTED)
        self.scatter_canvas.axes.set_ylabel("Margen %", fontsize=9, color=styles.MUTED)
        self.scatter_canvas.axes.xaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        if rows:
            self.scatter_canvas.axes.scatter(
                [d["ingresos"] for d in rows],
                [d["margen"] for d in rows],
                color=styles.ESPRESSO, alpha=0.7, s=46, edgecolors="white", linewidths=0.8,
            )
            # Anota el top por ingresos para orientar rápido
            top = max(rows, key=lambda d: d["ingresos"])
            self.scatter_canvas.axes.annotate(
                top["nombre"], (top["ingresos"], top["margen"]),
                fontsize=7, color=styles.TEXT_GRAY,
                xytext=(6, 6), textcoords="offset points",
            )
        self.scatter_canvas.redraw()
