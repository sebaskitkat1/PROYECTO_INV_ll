"""Pantalla de gestion de inventario: existencias, rotacion y curva ABC."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import analytics, mock_data, repository
from app.data import store
from app.data.app_state import AppState
from app.data.db import DBError
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar

ESTADO_CONFIG = {
    "optimo": (styles.SUCCESS_BG, styles.SUCCESS, "ÓPTIMO"),
    "advertencia": (styles.WARNING_BG, styles.WARNING, "ADVERTENCIA"),
    "critico": (styles.DANGER_BG, styles.DANGER, "CRÍTICO"),
    "sin_minimo": (styles.BG_LIGHT, styles.MUTED, "SIN MÍNIMO"),
}

ESTADO_ORDEN = {"critico": 0, "advertencia": 1, "optimo": 2, "sin_minimo": 3}


class NumericItem(QTableWidgetItem):
    """Item que ordena por valor numerico (UserRole), no por texto."""

    def __lt__(self, other):
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except Exception:
            return super().__lt__(other)


class EstadoItem(QTableWidgetItem):
    """Ordena por criticidad, no alfabeticamente."""

    def __lt__(self, other):
        try:
            return ESTADO_ORDEN[self.data(Qt.UserRole)] < ESTADO_ORDEN[other.data(Qt.UserRole)]
        except Exception:
            return super().__lt__(other)


class StockDelegate(QStyledItemDelegate):
    """editor numerico segun unidad: decimales en kg/L, enteros en pzas/bidones."""

    def __init__(self, buscar_unidad, parent=None):
        super().__init__(parent)
        self._buscar_unidad = buscar_unidad

    def createEditor(self, parent, option, index):
        if self._buscar_unidad(index.row()) in analytics.ENTERO_UNIDADES:
            editor = QSpinBox(parent)
            editor.setRange(0, 99999)
        else:
            editor = QDoubleSpinBox(parent)
            editor.setRange(0.0, 99999.0)
            editor.setDecimals(2)
        return editor


class InventoryScreen(QWidget):
    """Pantalla de gestion de inventario y niveles de stock."""

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
                title="Inventario",
                subtitle="",
                active_screen="inventory",
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

        # lista compartida: lo editado sigue ahi al volver
        self.inventory: list[dict] = store.get_inventory()

        self.alert_banner = self._build_alert_banner()
        content_layout.addWidget(self.alert_banner)
        content_layout.addLayout(self._build_summary_row())
        self.table = self._build_table()
        content_layout.addWidget(self.table)
        content_layout.addLayout(self._build_charts_row())
        content_layout.addLayout(self._build_actions_row())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
        self._refresh_summary_and_alert()

    # -- resumen -------------------------------------------------------

    def _build_alert_banner(self) -> QFrame:
        banner = QFrame()
        banner.setProperty("role", "alertDanger")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(16, 12, 16, 12)
        self.alert_label = QLabel("")
        self.alert_label.setWordWrap(True)
        self.alert_label.setStyleSheet(f"color: {styles.CLAY}; font-size: 12.5px; font-weight: 600;")
        layout.addWidget(self.alert_label, stretch=1)
        banner.setVisible(False)
        return banner

    def _build_summary_row(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        card_total, self.lbl_total = self._summary_card("Referencias", "0", styles.INK)
        card_opt, self.lbl_optimo = self._summary_card("En orden", "0", styles.SAGE)
        card_riesgo, self.lbl_riesgo = self._summary_card("Por pedir", "0", styles.CLAY)
        grid.addWidget(card_total, 0, 0)
        grid.addWidget(card_opt, 0, 1)
        grid.addWidget(card_riesgo, 0, 2)
        return grid

    @staticmethod
    def _summary_card(label: str, value: str, accent: str, background: str | None = None):
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(16, 16, 16, 16)
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignCenter)
        label_widget.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 500;")
        value_widget = QLabel(value)
        value_widget.setAlignment(Qt.AlignCenter)
        value_widget.setStyleSheet(f"color: {accent}; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;")
        layout.addWidget(label_widget)
        layout.addWidget(value_widget)
        return card, value_widget

    def _refresh_summary_and_alert(self) -> None:
        # cuentas desde la lista compartida, asi valen lo editado
        health = analytics.inventory_health(self.inventory)
        self.lbl_total.setText(str(health["total"]))
        self.lbl_optimo.setText(str(health["optimo"]))
        self.lbl_riesgo.setText(str(health["critico"]))
        if health["critico"]:
            criticos = health["criticos"]
            self.alert_label.setText(
                f"{health['critico']} por pedir: {', '.join(criticos[:4])}"
                + ("…" if len(criticos) > 4 else "")
                + " · Conviene pedir hoy."
            )
            self.alert_banner.setVisible(True)
        else:
            self.alert_banner.setVisible(False)

    def _build_actions_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        order_btn = QPushButton("Generar orden de compra")
        order_btn.setProperty("role", "primary")
        order_btn.setCursor(Qt.PointingHandCursor)
        order_btn.clicked.connect(self._export_order)
        row.addWidget(order_btn)
        reset_btn = QPushButton("Restablecer")
        reset_btn.setProperty("role", "outline")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_data)
        row.addWidget(reset_btn)
        row.addStretch()
        return row

    def _export_order(self) -> None:
        import csv
        bajos = [i for i in self.inventory if i["estado"] in ("critico", "advertencia")]
        if not bajos:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar orden de compra", "orden_compra.csv", "CSV (*.csv)")
        if not path:
            return
        # cantidad sugerida = llevar el stock al doble del minimo
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["nombre", "stockActual", "stockMinimo", "diasAgotar", "estado", "sugerido"])
            w.writeheader()
            for r in sorted(bajos, key=lambda r: ESTADO_ORDEN[r["estado"]]):
                fila = {k: r.get(k, "") for k in ["nombre", "stockActual", "stockMinimo", "diasAgotar", "estado"]}
                fila["sugerido"] = analytics.reorder_qty(r)
                w.writerow(fila)

    def _reset_data(self) -> None:
        self.inventory = store.reset_inventory()
        self._reload_table()
        self._refresh_summary_and_alert()

    # -- tabla -----------------------------------------------------------

    def _build_table(self) -> QTableWidget:
        columns = ["Nombre Producto", "Stock Actual", "Stock Mínimo", "Días Para Agotar", "Estado"]
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.AnyKeyPressed)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._reload_table(table)
        table.setItemDelegateForColumn(1, StockDelegate(self._unidad_fila, table))
        table.setItemDelegateForColumn(2, StockDelegate(self._unidad_fila, table))
        table.cellChanged.connect(self._on_cell_changed)
        table.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)
        return table

    def _on_sort_changed(self, col: int, order) -> None:
        # recuerda el orden del usuario para mantenerlo al recargar
        self._user_sort = (col, order)

    def _reload_table(self, table: QTableWidget | None = None) -> None:
        tbl = table if table is not None else self.table
        tbl.blockSignals(True)
        tbl.setSortingEnabled(False)
        rows = sorted(self.inventory, key=lambda r: ESTADO_ORDEN[r["estado"]])
        tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            name_item = QTableWidgetItem(row["nombre"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 0, name_item)
            tbl.setItem(r, 1, self._stock_item(row["stockActual"], row.get("unidad")))
            tbl.setItem(r, 2, self._stock_item(row["stockMinimo"], row.get("unidad")))

            dias = row.get("diasAgotar")
            if dias is None:
                dias_item = NumericItem("—")
                dias_item.setData(Qt.UserRole, float("inf"))
            else:
                dias_item = self._numeric_item(self._fmt_dias(float(dias), row.get("unidad")))
                dias_item.setData(Qt.UserRole, float(dias))
            dias_item.setFlags(dias_item.flags() & ~Qt.ItemIsEditable)
            if dias is not None and dias <= 5:
                dias_item.setForeground(QColor(styles.DANGER))
                font = dias_item.font()
                font.setBold(True)
                dias_item.setFont(font)
            tbl.setItem(r, 3, dias_item)

            bg, fg, label = ESTADO_CONFIG[row["estado"]]
            estado_item = EstadoItem(label)
            estado_item.setData(Qt.UserRole, row["estado"])
            estado_item.setTextAlignment(Qt.AlignCenter)
            estado_item.setBackground(QColor(bg))
            estado_item.setForeground(QColor(fg))
            font = estado_item.font()
            font.setBold(True)
            estado_item.setFont(font)
            estado_item.setFlags(estado_item.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 4, estado_item)

        tbl.setMinimumHeight(min(40 * len(rows) + 40, 420) if rows else 120)
        tbl.resizeColumnsToContents()
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tbl.setSortingEnabled(True)
        # respeta el orden que eligio el usuario; si no, queda el de estado
        user_sort = getattr(self, "_user_sort", None)
        if user_sort is not None:
            tbl.sortItems(user_sort[0], user_sort[1])
        tbl.blockSignals(False)

    def _on_cell_changed(self, row: int, col: int) -> None:
        # solo columnas 1 y 2 son editables
        if col not in (1, 2):
            return
        name = self.table.item(row, 0).text()
        inv = next((i for i in self.inventory if i["nombre"] == name), None)
        if inv is None:
            self._reload_table()
            return
        try:
            nuevo = float(self.table.item(row, col).text().strip().split()[0].replace(",", "."))
        except (ValueError, AttributeError, IndexError):
            QMessageBox.warning(self, "Valor invalido", f"{name}: escribe un numero.")
            self._reload_table()
            return
        entero = inv.get("unidad") in analytics.ENTERO_UNIDADES
        if nuevo < 0 or (entero and not nuevo.is_integer()):
            QMessageBox.warning(self, "Valor invalido", f"{name}: cantidad no valida para {inv.get('unidad')}.")
            self._reload_table()
            return
        nuevo = int(nuevo) if entero else round(nuevo, 2)
        if inv.get("id_ingrediente") is not None and repository.activa():
            # guarda en la base (kardex) y recarga desde la vista
            try:
                if col == 1:
                    repository.save_stock(inv["id_ingrediente"], nuevo, AppState.user_id,
                                          f"Ajuste manual desde inventario ({name})")
                else:
                    repository.update_minimo(inv["id_ingrediente"], nuevo)
            except DBError:
                QMessageBox.warning(self, "Sin conexion", "No se pudo guardar en la base.")
                self._reload_table()
                return
            self.inventory = store.reset_inventory()
            self._reload_table()
            self._refresh_summary_and_alert()
            return
        if col == 1:
            inv["stockActual"] = nuevo
        else:
            inv["stockMinimo"] = nuevo
        estado, dias = analytics.stock_status(inv["stockActual"], inv["stockMinimo"], inv.get("consumoDiario"))
        inv["estado"], inv["diasAgotar"] = estado, dias
        self._reload_table()
        self._refresh_summary_and_alert()

    def _unidad_fila(self, fila: int) -> str:
        item = self.table.item(fila, 0)
        if item is None:
            return "kg"
        inv = next((i for i in self.inventory if i["nombre"] == item.text()), None)
        return (inv or {}).get("unidad", "kg")

    @staticmethod
    def _fmt_stock(value: float, unidad) -> str:
        if unidad in analytics.ENTERO_UNIDADES:
            return f"{int(value):,}"
        return f"{float(value):.2f}".rstrip("0").rstrip(".")

    @classmethod
    def _stock_item(cls, value: float, unidad) -> NumericItem:
        item = NumericItem(cls._fmt_stock(value, unidad))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setData(Qt.UserRole, float(value))
        return item

    @staticmethod
    def _fmt_dias(dias: float, unidad) -> str:
        if unidad in analytics.ENTERO_UNIDADES:
            return f"{int(round(dias))} días"
        return f"{dias:.1f}".rstrip("0").rstrip(".") + " días"

    @staticmethod
    def _numeric_item(value, suffix: str = "") -> NumericItem:
        item = NumericItem(f"{value}{suffix}")
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setData(Qt.UserRole, value)
        return item

    # -- graficas ----------------------------------------------------------

    def _build_charts_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._rotation_chart_card())
        row.addWidget(self._pareto_chart_card())
        return row

    def _rotation_chart_card(self) -> QFrame:
        card = self._chart_card("Cobertura (días)")
        canvas = MplCanvas(height=2.6)
        # misma fuente que la tabla: stock / consumo; color segun estado
        items = [i for i in self.inventory if i.get("diasAgotar") is not None]
        items.sort(key=lambda i: float(i["diasAgotar"]))
        names = [i["nombre"].split("(")[0].strip() for i in items][::-1]
        values = [float(i["diasAgotar"]) for i in items][::-1]
        color_por_estado = {"critico": styles.CLAY, "advertencia": styles.MENTA}
        colors = [color_por_estado.get(i["estado"], styles.MENTA_SOFT) for i in items][::-1]
        canvas.axes.barh(names, values, color=colors, height=0.55)
        canvas.axes.set_xlabel("días", fontsize=9, color=styles.MUTED)
        canvas.axes.tick_params(axis="y", labelsize=8)
        canvas.redraw()
        card.layout().addWidget(canvas)
        return card

    def _pareto_chart_card(self) -> QFrame:
        card = self._chart_card("Qué deja más")
        canvas = MplCanvas(height=2.6)
        # clases ABC calculadas, no a mano
        data = analytics.abc_classes(mock_data.get_pareto_data())
        names = [d["nombre"] for d in data]
        values = [d["ingresos"] for d in data]
        cum_pct = [d["acum_pct"] for d in data]
        bars = canvas.axes.bar(names, values, color=styles.VERDE, label="Ingresos")
        canvas.axes.yaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.axes.tick_params(axis="x", labelsize=7, rotation=15)
        ax2 = canvas.axes.twinx()
        ax2.plot(names, cum_pct, color=styles.MENTA, marker="o", markersize=3, linewidth=1.6, label="% acum.")
        ax2.axhline(80, color=styles.MENTA, linestyle="--", linewidth=1, alpha=0.7)
        ax2.set_ylim(0, 105)
        ax2.tick_params(labelsize=7, colors=styles.MUTED)
        # etiqueta clase A/B/C sobre cada barra
        for bar, d in zip(bars, data):
            canvas.axes.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 80, d["clase"],
                             ha="center", fontsize=7, fontweight="bold", color=styles.MUTED)
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
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
            layout.addWidget(subtitle_label)
        return card
