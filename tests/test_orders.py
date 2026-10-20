"""Compras: mapeo de ordenes, detalle y ejemplo sin base."""
import datetime
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtWidgets import QApplication, QMessageBox

from app.data import repository
from app.data.app_state import AppState
from app.data.db import DBError
from app.screens.purchases_screen import PurchasesScreen


class TestMapeoCompras(unittest.TestCase):
    def test_orden(self):
        r = repository.map_orden_row({
            "id_orden": 7, "proveedor": "Huerta", "fecha_creacion":
            datetime.datetime(2026, 10, 19, 8, 40), "estado": "borrador",
            "total": "723.70"})
        self.assertEqual(r, {"id_orden": 7, "proveedor": "Huerta",
                             "fecha": "2026-10-19 08:40", "estado": "borrador",
                             "total": 723.70})

    def test_detalle(self):
        r = repository.map_orden_detalle_row({
            "nombre": "Fresa", "unidad": "kg", "cantidad_solicitada": 10,
            "cantidad_recibida": None, "precio_unitario": 23.45,
            "importe": 234.5})
        self.assertEqual((r["nombre"], r["cantidad"], r["recibido"], r["importe"]),
                         ("Fresa", 10.0, None, 234.5))
        self.assertAlmostEqual(r["precio"], 23.45)


class TestPantallaCompras(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.screen = PurchasesScreen(on_navigate=lambda _x: None, on_logout=lambda: None)

    def tearDown(self):
        AppState.clear()

    def _seleccionar(self, id_orden):
        for r in range(self.screen.orders_table.rowCount()):
            if self.screen.orders_table.item(r, 0).text() == str(id_orden):
                self.screen.orders_table.selectRow(r)
                return
        self.fail(f"no aparece la orden {id_orden}")

    def test_ejemplo_solo_lectura(self):
        self.assertEqual(self.screen.orders_table.rowCount(), 3)
        self.assertFalse(self.screen.generate_btn.isEnabled())
        self.assertFalse(self.screen.receive_btn.isEnabled())
        self.assertIn("ejemplo", self.screen.status_label.text())

    def test_detalle_de_la_orden(self):
        self._seleccionar(1048)
        self.assertIn("1048", self.screen.detail_title.text())
        self.assertEqual(self.screen.detail_table.rowCount(), 4)
        self.assertEqual(self.screen.detail_table.item(0, 0).text(), "Fresa")

    def test_filtro_por_estado(self):
        self.screen.filter_combo.setCurrentIndex(3)  # recibida
        self.assertEqual(self.screen.orders_table.rowCount(), 1)
        self.assertEqual(self.screen.detail_table.rowCount(), 3)
        self.assertFalse(self.screen.receive_btn.isEnabled())

    def test_generar_llama_al_sp(self):
        AppState.set_user("gerente@frutidata.local", user_id=9)
        self.screen._online = True
        with patch.object(type(self.screen), "_reload_orders") as reload, \
                patch("app.screens.purchases_screen.repository.generate_purchase_orders",
                      return_value=2) as generar, \
                patch("app.screens.purchases_screen.QMessageBox.question",
                      return_value=QMessageBox.Yes), \
                patch("app.screens.purchases_screen.QMessageBox.information") as aviso:
            self.screen._generate_orders()
        generar.assert_called_once_with(9)
        reload.assert_called_once()
        self.assertIn("2", aviso.call_args[0][2])

    def test_recibir_llama_al_sp_y_refresca(self):
        AppState.set_user("admin@frutidata.local", user_id=1)
        self.screen._online = True
        self._seleccionar(1048)
        with patch.object(type(self.screen), "_reload_orders") as reload, \
                patch("app.screens.purchases_screen.repository.receive_purchase_order") as recibir, \
                patch("app.screens.purchases_screen.store.reset_inventory") as reset, \
                patch("app.screens.purchases_screen.QMessageBox.question",
                      return_value=QMessageBox.Yes), \
                patch("app.screens.purchases_screen.QMessageBox.information"):
            self.screen._receive_order()
        recibir.assert_called_once_with(1048, 1)
        reset.assert_called_once()
        reload.assert_called_once()

    def test_si_falla_la_carga_usa_ejemplo(self):
        self.screen._online = True
        with patch("app.screens.purchases_screen.repository.purchase_orders",
                   side_effect=DBError("sin conexion")):
            self.screen._reload_orders()
        self.assertFalse(self.screen._online)
        self.assertEqual(self.screen.orders_table.rowCount(), 3)
        self.assertFalse(self.screen.generate_btn.isEnabled())


if __name__ == "__main__":
    unittest.main()
