"""F01: la tabla de inventario no se corrompe al llenar."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.data import store
from app.screens.inventory_screen import InventoryScreen

ESTADO_TXT = {"optimo": "ÓPTIMO", "advertencia": "ADVERTENCIA", "critico": "CRÍTICO",
              "sin_minimo": "SIN MÍNIMO"}


def _falla_filas(screen):
    inv = store.get_inventory()
    malas = []
    for r in range(screen.table.rowCount()):
        celdas = [screen.table.item(r, c) for c in (0, 1, 2, 4)]
        if any(c is None for c in celdas):
            malas.append((r, "vacia"))
            continue
        nombre = celdas[0].text()
        base = next(i for i in inv if i["nombre"] == nombre)
        ok = (float(celdas[1].text().replace(",", ".")) == float(base["stockActual"])
              and float(celdas[2].text().replace(",", ".")) == float(base["stockMinimo"])
              and celdas[3].text() == ESTADO_TXT[base["estado"]])
        if not ok:
            malas.append((r, nombre))
    return malas


class TestInventarioTabla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        store.reset_inventory()
        self.s = InventoryScreen(on_navigate=lambda x: None, on_logout=lambda: None)

    def test_llenado_sin_corruptas(self):
        self.assertEqual(_falla_filas(self.s), [])

    def test_orden_usuario_sobrevive_recarga(self):
        self.s.table.sortItems(1, Qt.DescendingOrder)
        antes = [self.s.table.item(r, 0).text() for r in range(self.s.table.rowCount())]
        self.s._reload_table()
        despues = [self.s.table.item(r, 0).text() for r in range(self.s.table.rowCount())]
        self.assertEqual(antes, despues)
        self.assertEqual(_falla_filas(self.s), [])

    def test_edicion_y_restablecer_consistentes(self):
        fila = next(r for r in range(self.s.table.rowCount())
                    if self.s.table.item(r, 0).text() == "Naranja (kg)")
        self.s.table.blockSignals(True)
        self.s.table.item(fila, 1).setText("30")
        self.s.table.blockSignals(False)
        self.s._on_cell_changed(fila, 1)
        self.assertEqual(_falla_filas(self.s), [])
        self.assertEqual(
            next(i for i in store.get_inventory() if i["nombre"] == "Naranja (kg)")["stockActual"], 30)
        self.s._reset_data()
        self.assertEqual(_falla_filas(self.s), [])
        self.assertEqual(
            next(i for i in store.get_inventory() if i["nombre"] == "Naranja (kg)")["stockActual"], 18)


if __name__ == "__main__":
    unittest.main()
