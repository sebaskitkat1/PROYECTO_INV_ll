"""Roles: permisos, navegacion filtrada y bitacora consultable."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtWidgets import QApplication, QPushButton

from app.data import roles
from app.data.app_state import AppState
from app.screens.bitacora_screen import BitacoraScreen
from app.screens.inventory_screen import InventoryScreen
from app.widgets.nav_bar import NavBar


class TestPermisos(unittest.TestCase):
    def test_cajero_sin_pronostico_ni_bitacora(self):
        self.assertTrue(roles.puede_ver(roles.ROL_CAJERO, "sales"))
        self.assertTrue(roles.puede_ver(roles.ROL_CAJERO, "inventory"))
        self.assertFalse(roles.puede_ver(roles.ROL_CAJERO, "prediction"))
        self.assertFalse(roles.puede_ver(roles.ROL_CAJERO, "compras"))
        self.assertFalse(roles.puede_ver(roles.ROL_CAJERO, "bitacora"))

    def test_gerente_y_admin(self):
        self.assertTrue(roles.puede_ver(roles.ROL_GERENTE, "prediction"))
        self.assertTrue(roles.puede_ver(roles.ROL_GERENTE, "compras"))
        self.assertFalse(roles.puede_ver(roles.ROL_GERENTE, "bitacora"))
        self.assertTrue(roles.puede_ver(roles.ROL_ADMIN, "compras"))
        self.assertTrue(roles.puede_ver(roles.ROL_ADMIN, "bitacora"))

    def test_compras(self):
        self.assertFalse(roles.puede_comprar(roles.ROL_CAJERO))
        self.assertTrue(roles.puede_comprar(roles.ROL_GERENTE))
        self.assertTrue(roles.puede_comprar(roles.ROL_ADMIN))

    def test_rol_desde_id(self):
        self.assertEqual(roles.rol_desde_id(1), roles.ROL_ADMIN)
        self.assertEqual(roles.rol_desde_id("3"), roles.ROL_CAJERO)
        self.assertEqual(roles.rol_desde_id(99), roles.ROL_CAJERO)


class TestNavBar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _nav(self, role):
        return NavBar("Hoy", "", "dashboard", lambda _s: None, lambda: None, role=role)

    def _botones(self, nav):
        return [b.text() for b in nav.findChildren(QPushButton)]

    def test_cajero_sin_prediccion_ni_bitacora(self):
        nav = self._nav(roles.ROL_CAJERO)
        botones = self._botones(nav)
        self.assertIn("Inventario", botones)
        self.assertNotIn("Compras", botones)
        self.assertNotIn("Predicción", botones)
        self.assertNotIn("Bitácora", botones)
        self.assertEqual(nav.role_label.text(), roles.ROL_CAJERO)

    def test_admin_ve_todo(self):
        nav = self._nav(roles.ROL_ADMIN)
        botones = self._botones(nav)
        self.assertIn("Compras", botones)
        self.assertIn("Predicción", botones)
        self.assertIn("Bitácora", botones)
        self.assertEqual(nav.role_label.text(), roles.ROL_ADMIN)


class TestPantallasPorRol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        AppState.clear()

    def test_cajero_no_ve_orden_de_compra(self):
        from app.data import store
        AppState.set_user("caja@frutidata.local", role=roles.ROL_CAJERO)
        store.reset_inventory()
        s = InventoryScreen(on_navigate=lambda _x: None, on_logout=lambda: None)
        self.assertTrue(s.order_btn.isHidden())
        self.assertFalse(s.can_buy)

    def test_admin_ve_orden_de_compra(self):
        from app.data import store
        AppState.set_user("admin@frutidata.local", role=roles.ROL_ADMIN)
        store.reset_inventory()
        s = InventoryScreen(on_navigate=lambda _x: None, on_logout=lambda: None)
        self.assertFalse(s.order_btn.isHidden())
        self.assertTrue(s.can_buy)

    def test_bitacora_sin_base(self):
        s = BitacoraScreen(on_navigate=lambda _x: None, on_logout=lambda: None)
        self.assertEqual(s.table.rowCount(), 0)
        self.assertIn("sin conexión", s.status_label.text())

    def test_navegacion_bloqueada_para_cajero(self):
        from app.main_window import MainWindow
        AppState.set_user("caja@frutidata.local", role=roles.ROL_CAJERO)
        w = MainWindow()
        w.navigate("compras")
        self.assertIs(w.stack.currentWidget(), w.screens["dashboard"])
        w.navigate("prediction")
        self.assertIs(w.stack.currentWidget(), w.screens["dashboard"])
        w.navigate("bitacora")
        self.assertIs(w.stack.currentWidget(), w.screens["dashboard"])

    def test_admin_navega_a_compras(self):
        from app.main_window import MainWindow
        AppState.set_user("admin@frutidata.local", role=roles.ROL_ADMIN)
        w = MainWindow()
        w.navigate("compras")
        self.assertIs(w.stack.currentWidget(), w.screens["compras"])


if __name__ == "__main__":
    unittest.main()
