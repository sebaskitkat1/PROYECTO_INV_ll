"""F08/F09/F11 + caducidad: orden, formato, export y alerta."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget

from app.data import export_csv, repository
from app.widgets.mpl_canvas import fmt_miles
from app.widgets.table_items import NumericItem, TextItem


class TestOrden(unittest.TestCase):
    def test_numeros_no_texto(self):
        t = QTableWidget(4, 1)
        for i, v in enumerate([842, 1200, 95, 1500]):
            t.setItem(i, 0, NumericItem(str(v), v))
        t.setSortingEnabled(True)
        t.sortByColumn(0, Qt.AscendingOrder)
        self.assertEqual([t.item(r, 0).text() for r in range(4)],
                         ["95", "842", "1200", "1500"])

    def test_acentos_no_separan(self):
        t = QTableWidget(3, 1)
        for i, v in enumerate(["Torta", "Té Negro", "Te Verde"]):
            t.setItem(i, 0, TextItem(v))
        t.setSortingEnabled(True)
        t.sortByColumn(0, Qt.AscendingOrder)
        nombres = [t.item(r, 0).text() for r in range(3)]
        # sin acentos: te negro < te verde < torta (Té junto a Te, no al final)
        self.assertEqual(nombres, ["Té Negro", "Te Verde", "Torta"])


class TestFormato(unittest.TestCase):
    def test_miles_sin_duplicar(self):
        self.assertEqual(fmt_miles(4000), "$4k")
        self.assertEqual(fmt_miles(3500), "$3.5k")
        self.assertEqual(fmt_miles(4500), "$4.5k")
        self.assertEqual(fmt_miles(0), "$0k")


class TestExport(unittest.TestCase):
    def test_bom_formulas_y_conteo(self):
        import tempfile
        ruta = tempfile.mktemp(suffix=".csv")
        n = export_csv.guardar_csv(
            ruta, ["nombre", "nota"],
            [{"nombre": "Mango", "nota": "=1+1"},
             {"nombre": "Fresa", "nota": "ok"}])
        self.assertEqual(n, 2)
        crudo = open(ruta, "rb").read()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"))
        texto = crudo.decode("utf-8-sig")
        self.assertIn("'=1+1", texto)

    def test_error_claro_en_ruta_mala(self):
        from app.data.export_csv import ExportError
        with self.assertRaises(ExportError):
            export_csv.guardar_csv("/ruta/que/no/existe/x.csv", ["a"], [{"a": 1}])


class TestCaducidad(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_mapeo_lote(self):
        r = repository.map_lote_row({"ingrediente": "Fresa", "unidad": "kg", "cantidad": 6,
                                     "fecha_caducidad": "2026-10-09", "dias_restantes": 2,
                                     "estado_lote": "por_caducar"})
        self.assertEqual((r["ingrediente"], r["dias"], r["estado"]),
                         ("Fresa", 2, "por_caducar"))

    def test_sin_base_se_oculta(self):
        from app.screens.inventory_screen import InventoryScreen
        s = InventoryScreen(on_navigate=lambda x: None, on_logout=lambda: None)
        self.assertEqual(s.expiry_label.text(), "")
        self.assertEqual(s.purge_btn.text(), "Purgar vencidos")


if __name__ == "__main__":
    unittest.main()
