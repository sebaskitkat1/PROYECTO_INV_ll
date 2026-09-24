"""Pantalla de gestión de inventario: existencias, rotación y curva ABC."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
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

ESTADO_CONFIG = {
    "optimo": (styles.SUCCESS_BG, styles.SUCCESS, "ÓPTIMO"),
    "advertencia": (styles.WARNING_BG, styles.WARNING, "ADVERTENCIA"),
    "critico": (styles.DANGER_BG, styles.DANGER, "CRÍTICO"),
}

ESTADO_ORDEN = {"critico": 0, "advertencia": 1, "optimo": 2}


class NumericItem(QTableWidgetItem):
    """Item que ordena por valor numérico (UserRole), no por texto."""

    def __lt__(self, other):
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except Exception:
            return super().__lt__(other)


class EstadoItem(QTableWidgetItem):
    """Ordena por criticidad, no alfabéticamente."""

    def __lt__(self, other):
        try:
            return ESTADO_ORDEN[self.data(Qt.UserRole)] < ESTADO_ORDEN[other.data(Qt.UserRole)]
        except Exception:
            return super().__lt__(other)


def calc_estado(stock_actual: int, stock_minimo: int) -> str:
    if stock_minimo <= 0:
        return "optimo"
    if stock_actual < stock_minimo:
        return "critico"
    if stock_actual < stock_minimo * 1.25:
        return "advertencia"
    return "optimo"


class InventoryScreen(QWidget):
    """Pantalla de gestión de inventario y niveles de stock."""

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
                subtitle="Qué pedir y qué rota",
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

        # Modelo editable en memoria (copia del mock para no mutar global)
        self.inventory: list[dict] = [dict(r) for r in mock_data.get_inventory()]

        self.alert_banner = self._build_alert_banner()
        content_layout.addWidget(self.alert_banner)
        content_layout.addLayout(self._build_summary_row())
        self.table = self._build_table()
        content_layout.addWidget(self.table)
        hint = QLabel("Doble clic en stock para corregir. Todo se recalcula solo.")
        hint.setProperty("role", "micro")
        content_layout.addWidget(hint)
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
        total = len(self.inventory)
        en_riesgo = sum(1 for i in self.inventory if i["estado"] == "critico")
        optimo = sum(1 for i in self.inventory if i["estado"] == "optimo")
        self.lbl_total.setText(str(total))
        self.lbl_optimo.setText(str(optimo))
        self.lbl_riesgo.setText(str(en_riesgo))
        if en_riesgo:
            criticos = [i["nombre"] for i in self.inventory if i["estado"] == "critico"]
            self.alert_label.setText(
                f"{en_riesgo} por pedir: {', '.join(criticos[:4])}"
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
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["nombre", "stockActual", "stockMinimo", "diasAgotar", "estado"])
            w.writeheader()
            w.writerows(sorted(bajos, key=lambda r: ESTADO_ORDEN[r["estado"]]))

    def _reset_data(self) -> None:
        self.inventory = [dict(r) for r in mock_data.get_inventory()]
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
        table.cellChanged.connect(self._on_cell_changed)
        return table

    def _reload_table(self, table: QTableWidget | None = None) -> None:
        tbl = table or self.table
        tbl.blockSignals(True)
        rows = sorted(self.inventory, key=lambda r: ESTADO_ORDEN[r["estado"]])
        tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            name_item = QTableWidgetItem(row["nombre"])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(r, 0, name_item)
            tbl.setItem(r, 1, self._numeric_item(row["stockActual"]))
            tbl.setItem(r, 2, self._numeric_item(row["stockMinimo"]))

            dias_item = self._numeric_item(row["diasAgotar"], suffix=" días")
            dias_item.setFlags(dias_item.flags() & ~Qt.ItemIsEditable)
            if row["diasAgotar"] <= 5:
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
        tbl.blockSignals(False)

    def _on_cell_changed(self, row: int, col: int) -> None:
        # Solo columnas 1 y 2 son editables
        if col not in (1, 2):
            return
        name = self.table.item(row, 0).text()
        try:
            new_val = int(self.table.item(row, col).text().strip().split()[0])
            if new_val < 0:
                raise ValueError
        except Exception:
            self._reload_table()  # revierte texto inválido
            return
        for inv in self.inventory:
            if inv["nombre"] == name:
                if col == 1:
                    inv["stockActual"] = new_val
                else:
                    inv["stockMinimo"] = new_val
                inv["estado"] = calc_estado(inv["stockActual"], inv["stockMinimo"])
                break
        self._reload_table()
        self._refresh_summary_and_alert()

    @staticmethod
    def _numeric_item(value, suffix: str = "") -> NumericItem:
        item = NumericItem(f"{value}{suffix}")
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setData(Qt.UserRole, value)
        return item

    # -- gráficas ----------------------------------------------------------

    def _build_charts_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._rotation_chart_card())
        row.addWidget(self._pareto_chart_card())
        return row

    def _rotation_chart_card(self) -> QFrame:
        card = self._chart_card("Rotación", "Menos días, más movimiento")
        canvas = MplCanvas(height=2.6)
        data = mock_data.get_rotation_data()
        names = [d["nombre"] for d in data][::-1]
        values = [d["dias"] for d in data][::-1]
        colors = [styles.CLAY if v <= 1.5 else styles.CARAMEL_SOFT for v in values]
        canvas.axes.barh(names, values, color=colors, height=0.55)
        canvas.axes.tick_params(axis="y", labelsize=8)
        canvas.redraw()
        card.layout().addWidget(canvas)
        return card

    def _pareto_chart_card(self) -> QFrame:
        card = self._chart_card("Qué deja más", "Barras lo que ingresa, línea lo acumulado")
        canvas = MplCanvas(height=2.6)
        data = sorted(mock_data.get_pareto_data(), key=lambda d: d["ingresos"], reverse=True)
        names = [d["nombre"] for d in data]
        values = [d["ingresos"] for d in data]
        total = sum(values) or 1
        cum_pct = []
        acc = 0
        for v in values:
            acc += v
            cum_pct.append(acc / total * 100)
        bars = canvas.axes.bar(names, values, color=styles.ESPRESSO, label="Ingresos")
        canvas.axes.yaxis.set_major_formatter(lambda v, _: f"${v/1000:.0f}k")
        canvas.axes.tick_params(axis="x", labelsize=7, rotation=15)
        ax2 = canvas.axes.twinx()
        ax2.plot(names, cum_pct, color=styles.CARAMEL, marker="o", markersize=3, linewidth=1.6, label="% acum.")
        ax2.axhline(80, color=styles.CARAMEL, linestyle="--", linewidth=1, alpha=0.7)
        ax2.set_ylim(0, 105)
        ax2.tick_params(labelsize=7, colors=styles.MUTED)
        # Etiqueta clase A/B/C sobre cada barra
        for i, (bar, pct) in enumerate(zip(bars, cum_pct)):
            clase = "A" if pct <= 80 else ("B" if pct <= 95 else "C")
            canvas.axes.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 80, clase,
                             ha="center", fontsize=7, fontweight="bold", color=styles.MUTED)
        canvas.redraw()
        card.layout().addWidget(canvas)
        return card

    @staticmethod
    def _chart_card(title: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(f"font-size: 12px; color: {styles.MUTED};")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return card
