"""Repositorio: mapeo de filas, fallback a ejemplo y auth contra la base."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # por defecto; el test de auth lo quita

from app.data import db, mock_data, repository, store
from app.data.db import DBError


class TestMapeo(unittest.TestCase):
    def test_venta_con_nulos(self):
        r = repository.map_venta_row({"nombre": "X", "categoria": None, "cantidad": None,
                                      "ingresos": None, "margen_pct": None, "tendencia": None})
        self.assertEqual(r, {"nombre": "X", "categoria": "Sin categoria", "cantidad": 0,
                             "ingresos": 0.0, "margen": 0.0, "tendencia": "down"})

    def test_inventario_con_dias_none(self):
        r = repository.map_inventario_row({"id_ingrediente": 1, "nombre": "Y", "unidad": "kg",
                                           "stock_actual": 5, "stock_minimo": 0,
                                           "consumo_diario": None, "dias_agotar": None,
                                           "estado": "sin_minimo"})
        self.assertIsNone(r["diasAgotar"])
        self.assertIsNone(r["consumoDiario"])
        self.assertEqual(r["estado"], "sin_minimo")

    def test_etiqueta_fuente_ejemplo(self):
        self.assertEqual(repository.etiqueta_fuente(), "ejemplo")


class TestFallback(unittest.TestCase):
    def test_sin_base_usa_mock(self):
        with self.assertRaises(DBError):
            repository.sales_detail()
        inv = store.reset_inventory()
        self.assertEqual(len(inv), len(mock_data.get_inventory()))
        self.assertIn("consumoDiario", inv[0])

    def test_load_env(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("# comentario\nDB_HOST = 127.0.0.1\nDB_PASSWORD=\"con espacios\"\nVACIA=\n")
            ruta = f.name
        datos = db.load_env(ruta)
        self.assertEqual(datos["DB_HOST"], "127.0.0.1")
        self.assertEqual(datos["DB_PASSWORD"], "con espacios")
        self.assertEqual(datos["VACIA"], "")


class TestAuthReal(unittest.TestCase):
    def test_rechaza_hash_invalido_y_registra_bitacora(self):
        os.environ["CAFE_DATOS"] = "db"
        try:
            if not db.available():
                self.skipTest("sin MySQL a la mano")
            antes = db.fetchall("SELECT COUNT(*) AS n FROM bitacora_accesos")[0]["n"]
            with self.assertRaises(repository.AuthError):
                repository.auth("caja@frutidata.local", "cualquier-clave")
            despues = db.fetchall("SELECT COUNT(*) AS n FROM bitacora_accesos")[0]["n"]
            self.assertEqual(despues, antes + 1)
        finally:
            os.environ["CAFE_DATOS"] = "mock"


if __name__ == "__main__":
    unittest.main()
