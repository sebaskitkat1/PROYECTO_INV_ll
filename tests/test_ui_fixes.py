"""F08/F09/F11 + caducidad: orden, formato, export y alerta."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget

from app.data import export_csv, repository
from app.data.db import DBError
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
        with open(ruta, "rb") as archivo:
            crudo = archivo.read()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"))
        texto = crudo.decode("utf-8-sig")
        self.assertIn("'=1+1", texto)

    def test_error_claro_en_ruta_mala(self):
        from app.data.export_csv import ExportError
        with self.assertRaises(ExportError):
            export_csv.guardar_csv("/ruta/que/no/existe/x.csv", ["a"], [{"a": 1}])

    def test_controles_antes_de_formula(self):
        # Excel ignora tabulador/CR/LF y espacios iniciales antes de evaluar
        for valor in ("\t=1+1", "\r=1+1", "\n=1+1", "\t@SUM(A1)", " =1+1"):
            self.assertTrue(export_csv.limpiar_valor(valor).startswith("'"),
                            repr(valor))
        self.assertEqual(export_csv.limpiar_valor("Mango"), "Mango")
        self.assertEqual(export_csv.limpiar_valor("  Mango"), "  Mango")


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


class TestBitacora(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_consulta_vacia_no_es_sin_conexion(self):
        from app.screens.bitacora_screen import BitacoraScreen
        with patch.object(repository, "bitacora_rows", return_value=[]):
            pantalla = BitacoraScreen(lambda x: None, lambda: None)
        self.assertEqual(pantalla.status_label.text(),
                         "0 registros · base de datos")

    def test_error_de_conexion_si_lo_dice(self):
        from app.screens.bitacora_screen import BitacoraScreen
        with patch.object(repository, "bitacora_rows",
                          side_effect=DBError("sin conexion")):
            pantalla = BitacoraScreen(lambda x: None, lambda: None)
        self.assertEqual(pantalla.status_label.text(),
                         "0 registros · sin conexión")


class TestPrediccionFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_fallback_desactiva_guardar(self):
        from app.screens import prediction_screen as ps
        with patch.object(repository, "activa", return_value=True), \
                patch.object(ps, "async_disponible", return_value=True), \
                patch.object(ps, "run_async",
                             side_effect=lambda _o, _f, _d, on_error:
                             on_error("fallo")):
            pantalla = ps.PredictionScreen(lambda x: None, lambda: None)
        self.assertFalse(pantalla._online)
        self.assertFalse(pantalla.save_btn.isEnabled())
        self.assertIn("ejemplo", pantalla.status_label.text())


class TestErroresCrudosInventario(unittest.TestCase):
    """Un error del motor SQL no debe tumbar la pantalla."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _error_sql():
        from mysql.connector.errors import ProgrammingError
        return ProgrammingError(msg="procedure not found")

    def test_purgar_avisa_sin_escapar(self):
        from app.screens.inventory_screen import InventoryScreen
        pantalla = InventoryScreen(lambda x: None, lambda: None)
        with patch.object(repository, "purge_expired",
                          side_effect=self._error_sql()), \
                patch("app.screens.inventory_screen.QMessageBox.warning") as aviso:
            pantalla._purge_expired()
        aviso.assert_called_once()

    def test_guardar_stock_avisa_sin_escapar(self):
        from app.screens.inventory_screen import InventoryScreen
        pantalla = InventoryScreen(lambda x: None, lambda: None)
        pantalla.inventory[0]["id_ingrediente"] = 1
        nombre = pantalla.inventory[0]["nombre"]
        pantalla._reload_table()
        fila = next(r for r in range(pantalla.table.rowCount())
                    if pantalla.table.item(r, 0).text() == nombre)
        with patch.object(repository, "activa", return_value=True), \
                patch.object(repository, "save_stock",
                             side_effect=self._error_sql()), \
                patch("app.screens.inventory_screen.QMessageBox.warning") as aviso:
            pantalla._on_cell_changed(fila, 1)
        aviso.assert_called_once()


if __name__ == "__main__":
    unittest.main()
