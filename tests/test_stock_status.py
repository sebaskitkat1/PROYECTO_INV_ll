"""F05: estado y dias salen de una sola funcion pura."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QSpinBox

from app.data import analytics, mock_data
from app.data.analytics import stock_status


class TestStockStatus(unittest.TestCase):
    def test_bordes(self):
        self.assertEqual(stock_status(10, 10, 2)[0], "advertencia")  # == minimo
        self.assertEqual(stock_status(12.5, 10, 2)[0], "optimo")  # == 1.25 * minimo
        self.assertEqual(stock_status(9.9, 10, 2)[0], "critico")
        self.assertEqual(stock_status(0, 10, 2), ("critico", 0.0))  # stock 0 siempre
        self.assertEqual(stock_status(5, 0, 2)[0], "sin_minimo")  # minimo 0 neutro
        self.assertIsNone(stock_status(8, 5, 0)[1])  # consumo 0
        self.assertIsNone(stock_status(8, 5, None)[1])  # consumo desconocido
        self.assertAlmostEqual(stock_status(9, 3, 3)[1], 3.0)

    def test_mock_alineado(self):
        mal = []
        for r in mock_data.get_inventory():
            consumo = r["stockActual"] / r["diasAgotar"] if r["diasAgotar"] else None
            estado, _ = stock_status(r["stockActual"], r["stockMinimo"], consumo)
            if estado != r["estado"]:
                mal.append((r["nombre"], r["estado"], estado))
        self.assertEqual(mal, [])

    def test_reorder_con_minimo_cero(self):
        self.assertEqual(analytics.reorder_qty({"stockActual": 5, "stockMinimo": 0}), 0)


class TestDelegateUnidades(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_editor_segun_unidad(self):
        from app.screens.inventory_screen import InventoryScreen, StockDelegate
        s = InventoryScreen(on_navigate=lambda x: None, on_logout=lambda: None)
        dep = StockDelegate(s._unidad_fila, s.table)
        # busca una fila de pzas para el otro caso
        fila_pzas = next(r for r in range(s.table.rowCount())
                         if s._unidad_fila(r) in ("pzas", "bidones"))
        ed_kg = dep.createEditor(s.table, None, s.table.model().index(
            next(r for r in range(s.table.rowCount()) if s._unidad_fila(r) == "kg"), 1))
        ed_pzas = dep.createEditor(s.table, None, s.table.model().index(fila_pzas, 1))
        self.assertIsInstance(ed_kg, QDoubleSpinBox)
        self.assertIsInstance(ed_pzas, QSpinBox)


if __name__ == "__main__":
    unittest.main()
