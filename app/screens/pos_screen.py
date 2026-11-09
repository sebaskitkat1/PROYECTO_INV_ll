"""Punto de venta: buscar productos, armar el ticket y registrar la venta."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import analytics, repository
from app.data.app_state import AppState
from app.data.db import DBError
from app.widgets.nav_bar import NavBar
from app.widgets.table_items import NumericItem, TextItem

COLUMNAS_PRODUCTO = ["Producto", "Categoría", "Precio", "Unidad"]
COLUMNAS_TICKET = ["Producto", "Cant.", "Precio", "Importe"]


class PosScreen(QWidget):
    """Caja sencilla: catálogo a la izquierda, ticket a la derecha."""

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        on_logout: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self.cart: dict[int, dict] = {}
        self.products: list[dict] = []
        self.db_ok = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(
            NavBar(
                title="Caja",
                subtitle="Registra la venta y alimenta el pronóstico",
                active_screen="pos",
                on_navigate=on_navigate,
                on_logout=on_logout,
                on_back=lambda: on_navigate("dashboard"),
            )
        )

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(28, 20, 28, 24)
        body_layout.setSpacing(16)
        body_layout.addWidget(self._build_catalog_panel(), stretch=1)
        body_layout.addWidget(self._build_ticket_panel())
        root.addWidget(body, stretch=1)

        self._load_catalog()

    # -- construccion ---------------------------------------------------

    def _build_catalog_panel(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Productos")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {styles.INK};")
        header.addWidget(title)
        header.addStretch()
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.offline_banner = QFrame()
        self.offline_banner.setProperty("role", "alertDanger")
        offline_layout = QHBoxLayout(self.offline_banner)
        offline_layout.setContentsMargins(12, 9, 12, 9)
        offline_label = QLabel(
            "Sin conexión a la base. La caja necesita MySQL para registrar ventas."
        )
        offline_label.setWordWrap(True)
        offline_label.setStyleSheet(
            f"color: {styles.CLAY}; font-size: 12px; font-weight: 600;"
        )
        offline_layout.addWidget(offline_label)
        self.offline_banner.setVisible(False)
        layout.addWidget(self.offline_banner)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar producto…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh_products)
        self.search.returnPressed.connect(self._add_first)
        filters.addWidget(self.search, stretch=1)
        self.category = QComboBox()
        self.category.setMinimumWidth(150)
        self.category.currentIndexChanged.connect(self._refresh_products)
        filters.addWidget(self.category)
        layout.addLayout(filters)

        self.product_table = QTableWidget(0, len(COLUMNAS_PRODUCTO))
        self.product_table.setHorizontalHeaderLabels(COLUMNAS_PRODUCTO)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.product_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.product_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.product_table.setAlternatingRowColors(True)
        self.product_table.setSortingEnabled(False)
        self.product_table.verticalHeader().setDefaultSectionSize(36)
        header_view = self.product_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3):
            header_view.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.product_table.itemActivated.connect(lambda _item: self._add_selected())
        layout.addWidget(self.product_table, stretch=1)

        footer = QHBoxLayout()
        hint = QLabel("Doble clic o Enter para agregar.")
        hint.setStyleSheet(f"color: {styles.MUTED}; font-size: 11.5px;")
        footer.addWidget(hint)
        footer.addStretch()
        add_btn = QPushButton("Agregar al ticket")
        add_btn.setProperty("role", "secondary")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_selected)
        footer.addWidget(add_btn)
        layout.addLayout(footer)
        return card

    def _build_ticket_panel(self) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        card.setFixedWidth(380)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Ticket")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {styles.INK};")
        header.addWidget(title)
        header.addStretch()
        self.ticket_count = QLabel("0 artículos")
        self.ticket_count.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px;")
        header.addWidget(self.ticket_count)
        layout.addLayout(header)

        self.cart_table = QTableWidget(0, len(COLUMNAS_TICKET))
        self.cart_table.setHorizontalHeaderLabels(COLUMNAS_TICKET)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cart_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setSortingEnabled(False)
        self.cart_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cart_table.verticalHeader().setDefaultSectionSize(36)
        cart_header = self.cart_table.horizontalHeader()
        cart_header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col, ancho in ((1, 58), (2, 72), (3, 78)):
            cart_header.setSectionResizeMode(col, QHeaderView.Fixed)
            self.cart_table.setColumnWidth(col, ancho)
        self.cart_table.itemSelectionChanged.connect(self._sync_qty_input)
        layout.addWidget(self.cart_table, stretch=1)

        qty_row = QHBoxLayout()
        qty_row.setSpacing(6)
        qty_label = QLabel("Cantidad")
        qty_label.setStyleSheet(
            f"color: {styles.MUTED}; font-size: 12px; font-weight: 600;"
        )
        qty_row.addWidget(qty_label)
        self.minus_btn = QPushButton("−")
        self.minus_btn.setProperty("role", "outline")
        self.minus_btn.setFixedWidth(36)
        self.minus_btn.setCursor(Qt.PointingHandCursor)
        self.minus_btn.clicked.connect(lambda: self._change_qty(-self._qty_step()))
        qty_row.addWidget(self.minus_btn)
        self.qty_input = QDoubleSpinBox()
        self.qty_input.setDecimals(3)
        self.qty_input.setMinimum(0.0)
        self.qty_input.setMaximum(9999999.999)
        self.qty_input.setSingleStep(1.0)
        self.qty_input.setKeyboardTracking(False)
        self.qty_input.setAlignment(Qt.AlignRight)
        self.qty_input.setFixedWidth(86)
        self.qty_input.setEnabled(False)
        self.qty_input.valueChanged.connect(self._apply_qty_input)
        qty_row.addWidget(self.qty_input)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setProperty("role", "outline")
        self.plus_btn.setFixedWidth(36)
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.clicked.connect(lambda: self._change_qty(self._qty_step()))
        qty_row.addWidget(self.plus_btn)
        self.remove_btn = QPushButton("Quitar")
        self.remove_btn.setProperty("role", "ghost")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.clicked.connect(self._remove_selected)
        qty_row.addWidget(self.remove_btn)
        qty_row.addStretch()
        layout.addLayout(qty_row)

        total_row = QHBoxLayout()
        total_label = QLabel("Total")
        total_label.setStyleSheet(f"color: {styles.MUTED}; font-size: 13px; font-weight: 600;")
        total_row.addWidget(total_label)
        total_row.addStretch()
        self.total_label = QLabel("$0.00")
        self.total_label.setStyleSheet(
            f"color: {styles.INK}; font-size: 28px; font-weight: 600; letter-spacing: -0.5px;"
        )
        total_row.addWidget(self.total_label)
        layout.addLayout(total_row)

        pay_row = QHBoxLayout()
        pay_label = QLabel("Pago")
        pay_label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 600;")
        pay_row.addWidget(pay_label)
        self.payment = QComboBox()
        self.payment.setMinimumWidth(150)
        pay_row.addWidget(self.payment, stretch=1)
        layout.addLayout(pay_row)

        self.cobrar_btn = QPushButton("Cobrar venta")
        self.cobrar_btn.setProperty("role", "primary")
        self.cobrar_btn.setMinimumHeight(44)
        self.cobrar_btn.setCursor(Qt.PointingHandCursor)
        self.cobrar_btn.setEnabled(False)
        self.cobrar_btn.clicked.connect(self._checkout)
        layout.addWidget(self.cobrar_btn)

        self.clear_btn = QPushButton("Cancelar ticket")
        self.clear_btn.setProperty("role", "ghost")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self._clear_cart)
        layout.addWidget(self.clear_btn)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {styles.SAGE}; font-size: 11.5px;")
        layout.addWidget(self.status_label)
        return card

    # -- carga de datos -------------------------------------------------

    def _load_catalog(self) -> None:
        try:
            categorias = repository.pos_categories()
            metodos = repository.pos_payment_methods()
            self.products = repository.pos_products()
        except DBError:
            self._set_offline()
            return

        self.db_ok = True
        self.offline_banner.setVisible(False)

        self.category.blockSignals(True)
        self.category.clear()
        self.category.addItem("Todas las categorías", None)
        for nombre in categorias:
            self.category.addItem(nombre, nombre)
        self.category.blockSignals(False)

        self.payment.clear()
        for metodo in metodos:
            self.payment.addItem(metodo["nombre"], metodo["id"])

        self._refresh_products()
        self._refresh_cart()

    def _set_offline(self) -> None:
        self.db_ok = False
        self.offline_banner.setVisible(True)
        self.products = []
        self.product_table.setRowCount(0)
        self.search.setEnabled(False)
        self.category.setEnabled(False)
        self.payment.setEnabled(False)
        self.count_label.setText("Sin conexión")
        self._refresh_cart()

    # -- catalogo -------------------------------------------------------

    def _refresh_products(self) -> None:
        if not self.db_ok:
            return
        categoria = self.category.currentData()
        try:
            self.products = repository.pos_products(self.search.text(), categoria)
        except DBError:
            self._set_offline()
            return
        self._fill_product_table()

    def _fill_product_table(self) -> None:
        self.product_table.setRowCount(len(self.products))
        for row, producto in enumerate(self.products):
            nombre = TextItem(producto["nombre"])
            nombre.setData(Qt.UserRole, producto["id_producto"])
            nombre.setFlags(nombre.flags() & ~Qt.ItemIsEditable)
            self.product_table.setItem(row, 0, nombre)

            categoria = TextItem(producto["categoria"])
            categoria.setFlags(categoria.flags() & ~Qt.ItemIsEditable)
            self.product_table.setItem(row, 1, categoria)

            precio = NumericItem(f"${producto['precio']:,.2f}", producto["precio"])
            precio.setFlags(precio.flags() & ~Qt.ItemIsEditable)
            self.product_table.setItem(row, 2, precio)

            unidad = TextItem(producto["unidad"])
            unidad.setTextAlignment(Qt.AlignCenter)
            unidad.setFlags(unidad.flags() & ~Qt.ItemIsEditable)
            self.product_table.setItem(row, 3, unidad)

        total = len(self.products)
        self.count_label.setText(f"{total} producto{'s' if total != 1 else ''}")

    def _selected_product(self) -> dict | None:
        row = self.product_table.currentRow()
        if row < 0:
            return None
        item = self.product_table.item(row, 0)
        if item is None:
            return None
        id_producto = item.data(Qt.UserRole)
        return next(
            (p for p in self.products if p["id_producto"] == id_producto), None
        )

    def _add_selected(self) -> None:
        producto = self._selected_product()
        if producto is None:
            QMessageBox.information(self, "Caja", "Selecciona un producto de la lista.")
            return
        self._add_product(producto)

    def _add_first(self) -> None:
        if self.product_table.rowCount() == 0:
            return
        item = self.product_table.item(0, 0)
        if item is None:
            return
        id_producto = item.data(Qt.UserRole)
        producto = next(
            (p for p in self.products if p["id_producto"] == id_producto), None
        )
        if producto is not None:
            self._add_product(producto)

    def _add_product(self, producto: dict) -> None:
        id_producto = int(producto["id_producto"])
        linea = self.cart.get(id_producto)
        if linea is None:
            self.cart[id_producto] = {"producto": producto, "cantidad": 1.0}
        else:
            linea["cantidad"] = round(linea["cantidad"] + 1.0, 3)
        self._refresh_cart(select_id=id_producto)
        self.search.setFocus()
        self.search.selectAll()

    # -- ticket ---------------------------------------------------------

    def _selected_cart_id(self) -> int | None:
        row = self.cart_table.currentRow()
        if row < 0:
            return None
        item = self.cart_table.item(row, 0)
        if item is None:
            return None
        return int(item.data(Qt.UserRole))

    def _qty_step(self) -> float:
        id_producto = self._selected_cart_id()
        linea = self.cart.get(id_producto) if id_producto is not None else None
        if linea and linea["producto"].get("solo_enteros"):
            return 1.0
        return 0.5

    def _change_qty(self, delta: float) -> None:
        id_producto = self._selected_cart_id()
        if id_producto is None:
            return
        linea = self.cart[id_producto]
        self._set_qty(id_producto, linea["cantidad"] + delta)

    def _set_qty(self, id_producto: int, valor: float) -> None:
        linea = self.cart.get(id_producto)
        if linea is None:
            return
        cantidad = round(float(valor), 3)
        if linea["producto"].get("solo_enteros"):
            cantidad = float(int(round(cantidad)))
        if cantidad < 0.001:
            self.cart.pop(id_producto, None)
            self._refresh_cart()
            return
        linea["cantidad"] = cantidad
        self._refresh_cart(select_id=id_producto)

    def _apply_qty_input(self, valor: float) -> None:
        id_producto = self._selected_cart_id()
        if id_producto is not None:
            self._set_qty(id_producto, valor)

    def _sync_qty_input(self) -> None:
        id_producto = self._selected_cart_id()
        linea = self.cart.get(id_producto) if id_producto is not None else None
        self.qty_input.blockSignals(True)
        try:
            if linea is None:
                self.qty_input.setDecimals(3)
                self.qty_input.setSingleStep(1.0)
                self.qty_input.setValue(0.0)
                self.qty_input.setEnabled(False)
            else:
                solo_enteros = bool(linea["producto"].get("solo_enteros"))
                self.qty_input.setDecimals(0 if solo_enteros else 3)
                self.qty_input.setSingleStep(1.0 if solo_enteros else 0.5)
                self.qty_input.setValue(float(linea["cantidad"]))
                self.qty_input.setEnabled(True)
        finally:
            self.qty_input.blockSignals(False)

    def _remove_selected(self) -> None:
        id_producto = self._selected_cart_id()
        if id_producto is None:
            return
        self.cart.pop(id_producto, None)
        self._refresh_cart()

    def _refresh_cart(self, select_id: int | None = None) -> None:
        self.cart_table.setRowCount(len(self.cart))
        for row, (id_producto, linea) in enumerate(self.cart.items()):
            producto = linea["producto"]
            nombre = TextItem(producto["nombre"])
            nombre.setData(Qt.UserRole, id_producto)
            nombre.setFlags(nombre.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 0, nombre)

            cantidad = NumericItem(
                analytics.fmt_qty(linea["cantidad"]), linea["cantidad"]
            )
            cantidad.setFlags(cantidad.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 1, cantidad)

            precio = NumericItem(f"${producto['precio']:,.2f}", producto["precio"])
            precio.setFlags(precio.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 2, precio)

            importe = round(producto["precio"] * linea["cantidad"], 2)
            importe_item = NumericItem(f"${importe:,.2f}", importe)
            importe_item.setFlags(importe_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 3, importe_item)

        if select_id is not None and select_id in self.cart:
            self.cart_table.selectRow(list(self.cart).index(select_id))

        total = self._total()
        unidades = sum(linea["cantidad"] for linea in self.cart.values())
        self.total_label.setText(f"${total:,.2f}")
        self.ticket_count.setText(
            f"{analytics.fmt_qty(unidades)} artículo{'s' if unidades != 1 else ''}"
        )
        hay_ticket = bool(self.cart)
        self.cobrar_btn.setEnabled(self.db_ok and hay_ticket)
        self.clear_btn.setEnabled(hay_ticket)
        self.plus_btn.setEnabled(hay_ticket)
        self.minus_btn.setEnabled(hay_ticket)
        self.remove_btn.setEnabled(hay_ticket)
        self._sync_qty_input()

    def _total(self) -> float:
        return round(
            sum(
                linea["producto"]["precio"] * linea["cantidad"]
                for linea in self.cart.values()
            ),
            2,
        )

    def _clear_cart(self) -> None:
        if not self.cart:
            return
        respuesta = QMessageBox.question(
            self,
            "Cancelar ticket",
            "¿Vaciar el ticket actual?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return
        self.cart.clear()
        self.status_label.setText("")
        self._refresh_cart()

    # -- cobro ----------------------------------------------------------

    def _checkout(self) -> None:
        if not self.cart:
            return
        if not AppState.user_id:
            QMessageBox.warning(
                self, "Caja", "No hay usuario en sesión. Vuelve a iniciar sesión."
            )
            return
        id_metodo = self.payment.currentData()
        if id_metodo is None:
            QMessageBox.warning(self, "Caja", "Selecciona un método de pago.")
            return

        items = [
            {"id_producto": id_producto, "cantidad": linea["cantidad"]}
            for id_producto, linea in self.cart.items()
        ]
        self.cobrar_btn.setEnabled(False)
        try:
            venta = repository.register_sale(items, int(id_metodo), AppState.user_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Caja", str(exc))
            return
        except DBError:
            QMessageBox.warning(
                self, "Caja", "Sin conexión a la base. La venta no se registró."
            )
            return
        except Exception as exc:  # noqa: BLE001 - se muestra el error al cajero
            QMessageBox.warning(
                self, "Caja", f"No se pudo registrar la venta:\n{exc}"
            )
            return
        finally:
            self.cobrar_btn.setEnabled(self.db_ok and bool(self.cart))

        self.cart.clear()
        self.search.clear()
        self.status_label.setText(
            f"Venta #{venta['id_venta']} registrada · ${venta['total']:,.2f}"
        )
        self._refresh_cart()
        QMessageBox.information(
            self,
            "Venta registrada",
            f"Venta #{venta['id_venta']}\n"
            f"{analytics.fmt_qty(venta['unidades'])} "
            f"artículo{'s' if venta['unidades'] != 1 else ''}\n"
            f"Total: ${venta['total']:,.2f}",
        )
