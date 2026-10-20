"""Compras: ordenes sugeridas por la base y recepcion de mercancia."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import analytics, mock_data, repository, store
from app.data.app_state import AppState
from app.data.db import DBError
from app.widgets.nav_bar import NavBar
from app.widgets.table_items import NumericItem

ESTADO_CONFIG = {
    "borrador": (styles.WARNING_BG, styles.WARNING, "Borrador"),
    "enviada": (styles.MENTA_SOFT, styles.VERDE, "Enviada"),
    "recibida": (styles.SUCCESS_BG, styles.SUCCESS, "Recibida"),
    "cancelada": (styles.DANGER_BG, styles.DANGER, "Cancelada"),
}

FILTROS = [
    ("Todos", ""),
    ("Borrador", "borrador"),
    ("Enviada", "enviada"),
    ("Recibida", "recibida"),
    ("Cancelada", "cancelada"),
]

ORDEN_COLUMNS = ["Orden", "Proveedor", "Fecha", "Estado", "Total"]
DETALLE_COLUMNS = ["Producto", "Solicitado", "Recibido", "Precio", "Importe"]


class PurchasesScreen(QWidget):
    """Ordenes de compra: generar lo sugerido y recibir mercancia."""

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        on_logout: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self._online = repository.activa()
        self.orders: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(
            NavBar(
                title="Compras",
                subtitle="",
                active_screen="compras",
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
        self.orders_table = self._build_orders_table()
        self.orders_table.itemSelectionChanged.connect(self._refresh_detail)
        content_layout.addWidget(self.orders_table)
        content_layout.addWidget(self._build_detail_card())
        content_layout.addLayout(self._build_actions_row())

        self.status_label = QLabel("")
        self.status_label.setProperty("role", "micro")
        content_layout.addWidget(self.status_label)
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
        self._reload_orders()

    # -- construccion -----------------------------------------------------

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setProperty("role", "filterBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        label = QLabel("Estado")
        label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 500;")
        layout.addWidget(label)

        self.filter_combo = QComboBox()
        for texto, clave in FILTROS:
            self.filter_combo.addItem(texto, clave)
        self.filter_combo.currentIndexChanged.connect(lambda _i: self._populate_orders())
        layout.addWidget(self.filter_combo)
        layout.addStretch()
        return bar

    @staticmethod
    def _build_orders_table() -> QTableWidget:
        table = QTableWidget(0, len(ORDEN_COLUMNS))
        table.setHorizontalHeaderLabels(ORDEN_COLUMNS)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setMinimumHeight(220)
        return table

    def _build_detail_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.detail_title = QLabel("Detalle de la orden")
        self.detail_title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        layout.addWidget(self.detail_title)

        self.detail_table = QTableWidget(0, len(DETALLE_COLUMNS))
        self.detail_table.setHorizontalHeaderLabels(DETALLE_COLUMNS)
        self.detail_table.verticalHeader().setVisible(False)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setAlternatingRowColors(True)
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.detail_table.setMinimumHeight(140)
        layout.addWidget(self.detail_table)
        return card

    def _build_actions_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.generate_btn = QPushButton("Generar órdenes")
        self.generate_btn.setProperty("role", "primary")
        self.generate_btn.setCursor(Qt.PointingHandCursor)
        self.generate_btn.clicked.connect(self._generate_orders)
        row.addWidget(self.generate_btn)

        self.receive_btn = QPushButton("Recibir orden")
        self.receive_btn.setProperty("role", "secondary")
        self.receive_btn.setCursor(Qt.PointingHandCursor)
        self.receive_btn.setEnabled(False)
        self.receive_btn.clicked.connect(self._receive_order)
        row.addWidget(self.receive_btn)

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setProperty("role", "outline")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self._reload_orders)
        row.addWidget(refresh_btn)

        row.addStretch()
        return row

    # -- datos ------------------------------------------------------------

    def _reload_orders(self) -> None:
        seleccionada = self._selected_id()
        if self._online:
            try:
                self.orders = repository.purchase_orders()
            except DBError:
                self._online = False
        if not self._online:
            self.orders = mock_data.get_purchase_orders()
        self.generate_btn.setEnabled(self._online)
        self._populate_orders(seleccionada)

    def _visible_orders(self) -> list[dict]:
        clave = self.filter_combo.currentData()
        if not clave:
            return list(self.orders)
        return [o for o in self.orders if o["estado"] == clave]

    def _populate_orders(self, seleccionada: int | None = None) -> None:
        rows = self._visible_orders()
        self.orders_table.blockSignals(True)
        self.orders_table.setSortingEnabled(False)
        self.orders_table.setRowCount(len(rows))
        for r, order in enumerate(rows):
            self.orders_table.setItem(r, 0, NumericItem(str(order["id_orden"]), order["id_orden"]))
            self.orders_table.setItem(r, 1, QTableWidgetItem(order["proveedor"]))
            self.orders_table.setItem(r, 2, QTableWidgetItem(order["fecha"]))
            estado = QTableWidgetItem(ESTADO_CONFIG.get(order["estado"], (styles.BG_LIGHT, styles.MUTED,
                                                                        order["estado"]))[2])
            estado.setTextAlignment(Qt.AlignCenter)
            bg, fg, _ = ESTADO_CONFIG.get(order["estado"], (styles.BG_LIGHT, styles.MUTED, ""))
            estado.setBackground(QColor(bg))
            estado.setForeground(QColor(fg))
            self.orders_table.setItem(r, 3, estado)
            self.orders_table.setItem(r, 4, NumericItem(f"${order['total']:,.2f}", order["total"]))

        self.orders_table.resizeColumnsToContents()
        self.orders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.orders_table.setMinimumHeight(min(40 * len(rows) + 40, 360) if rows else 120)

        objetivo = seleccionada
        if objetivo is None and rows:
            objetivo = rows[0]["id_orden"]
        fila = next((r for r in range(len(rows)) if rows[r]["id_orden"] == objetivo), None)
        if fila is not None:
            self.orders_table.selectRow(fila)
        else:
            self.orders_table.clearSelection()
        self.orders_table.setSortingEnabled(True)
        self.orders_table.blockSignals(False)

        if fila is not None:
            self._refresh_detail()
        else:
            self._clear_detail()
        self._update_status(rows)

    def _update_status(self, rows: list[dict]) -> None:
        fuente = repository.etiqueta_fuente() if self._online else "ejemplo (solo lectura)"
        self.status_label.setText(f"{len(rows)} de {len(self.orders)} órdenes · {fuente}")

    def _selected_id(self) -> int | None:
        row = self.orders_table.currentRow() if hasattr(self, "orders_table") else -1
        if row < 0:
            return None
        item = self.orders_table.item(row, 0)
        try:
            return int(item.text()) if item is not None else None
        except ValueError:
            return None

    def _selected_order(self) -> dict | None:
        oid = self._selected_id()
        return next((o for o in self.orders if o["id_orden"] == oid), None)

    def _refresh_detail(self) -> None:
        order = self._selected_order()
        if order is None:
            self._clear_detail()
            return
        self.detail_title.setText(f"Orden #{order['id_orden']} · {order['proveedor']}")
        if self._online:
            try:
                filas = repository.purchase_order_detail(order["id_orden"])
            except DBError:
                self._online = False
                self.generate_btn.setEnabled(False)
                self.status_label.setText("sin conexión · detalle no disponible")
                filas = []
        else:
            filas = mock_data.get_purchase_order_detail(order["id_orden"])
        self._populate_detail(filas)
        self.receive_btn.setEnabled(self._online and order["estado"] in ("borrador", "enviada"))

    def _clear_detail(self) -> None:
        self.detail_title.setText("Detalle de la orden")
        self.detail_table.setRowCount(0)
        self.receive_btn.setEnabled(False)

    def _populate_detail(self, filas: list[dict]) -> None:
        self.detail_table.setRowCount(len(filas))
        for r, fila in enumerate(filas):
            self.detail_table.setItem(r, 0, QTableWidgetItem(fila["nombre"]))
            self.detail_table.setItem(r, 1, self._qty_item(fila["cantidad"], fila["unidad"]))
            recibido = fila.get("recibido")
            if recibido is None:
                self.detail_table.setItem(r, 2, NumericItem("—", float("-inf")))
            else:
                self.detail_table.setItem(r, 2, self._qty_item(recibido, fila["unidad"]))
            self.detail_table.setItem(r, 3, NumericItem(f"${fila['precio']:,.2f}", fila["precio"]))
            self.detail_table.setItem(r, 4, NumericItem(f"${fila['importe']:,.2f}", fila["importe"]))
        self.detail_table.resizeColumnsToContents()
        self.detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.detail_table.setMinimumHeight(min(34 * len(filas) + 40, 240) if filas else 140)

    @staticmethod
    def _qty_item(value: float, unidad: str) -> NumericItem:
        if unidad in analytics.ENTERO_UNIDADES:
            texto = f"{int(round(value)):,}"
        else:
            texto = f"{value:.2f}".rstrip("0").rstrip(".")
        return NumericItem(texto, value)

    # -- acciones ---------------------------------------------------------

    def _generate_orders(self) -> None:
        if not self._online:
            QMessageBox.information(self, "Compras", "Sin conexión a la base.")
            return
        respuesta = QMessageBox.question(
            self, "Compras", "¿Generar órdenes con lo sugerido por inventario?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if respuesta != QMessageBox.Yes:
            return
        try:
            n = repository.generate_purchase_orders(AppState.user_id)
        except DBError:
            QMessageBox.warning(self, "Compras", "Sin conexión a la base.")
            return
        except Exception as e:
            QMessageBox.warning(self, "Compras", str(e))
            return
        if n:
            QMessageBox.information(self, "Compras", f"Se generaron {n} órdenes de compra.")
        else:
            QMessageBox.information(self, "Compras", "No hay productos por pedir.")
        self._reload_orders()

    def _receive_order(self) -> None:
        order = self._selected_order()
        if order is None or order["estado"] not in ("borrador", "enviada"):
            return
        if not self._online:
            QMessageBox.information(self, "Compras", "Sin conexión a la base.")
            return
        respuesta = QMessageBox.question(
            self, "Compras", f"¿Recibir completa la orden #{order['id_orden']}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if respuesta != QMessageBox.Yes:
            return
        try:
            repository.receive_purchase_order(order["id_orden"], AppState.user_id)
        except DBError:
            QMessageBox.warning(self, "Compras", "Sin conexión a la base.")
            return
        except Exception as e:
            QMessageBox.warning(self, "Compras", str(e))
            return
        store.reset_inventory()
        self._reload_orders()
        QMessageBox.information(self, "Compras", f"Orden #{order['id_orden']} recibida.")
