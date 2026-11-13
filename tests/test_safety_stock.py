"""Stock de seguridad XYZ: formula estadistica y respaldo por dias."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"

from app.data import analytics, store


class TestSafetyStock(unittest.TestCase):
    def test_formula_por_clase(self):
        # z * sigma * sqrt(lead): 1.28, 1.65 y 2.33 con sigma=2 y lead=4.
        self.assertAlmostEqual(
            analytics.xyz_safety_stock(
                2.0, 4.0, "X", dias_con_datos=20), 5.12, places=3)
        self.assertAlmostEqual(
            analytics.xyz_safety_stock(
                2.0, 4.0, "Y", dias_con_datos=20), 6.60, places=3)
        self.assertAlmostEqual(
            analytics.xyz_safety_stock(
                2.0, 4.0, "Z", dias_con_datos=20), 9.32, places=3)

    def test_respaldo_por_dias(self):
        # Sin clase o con pocos dias con venta: consumo * dias_seguridad.
        self.assertAlmostEqual(
            analytics.xyz_safety_stock(
                2.0, 4.0, None, consumo_diario=3.0, dias_seguridad=1.5),
            4.5)
        self.assertAlmostEqual(
            analytics.xyz_safety_stock(
                2.0, 4.0, "Z", consumo_diario=3.0, dias_seguridad=1.5,
                dias_con_datos=3, min_dias=7),
            4.5)

    def test_sigma_cero_y_lead_minimo(self):
        # Demanda perfectamente estable: el colchon estadistico es cero.
        self.assertEqual(
            analytics.xyz_safety_stock(
                0.0, 2.0, "X", consumo_diario=5.0, dias_con_datos=20),
            0.0)
        # Un lead time de 0 no elimina el colchon: se usa 1 dia como minimo.
        self.assertAlmostEqual(
            analytics.xyz_safety_stock(2.0, 0.0, "X", dias_con_datos=20),
            2.56, places=3)

    def test_punto_y_cantidad_usan_el_colchon_xyz(self):
        item = {"stockActual": 5, "stockMinimo": 10, "consumoDiario": 2}
        self.assertEqual(
            analytics.reorder_point(item, lead_time=3, stock_seguridad=4), 10)
        self.assertEqual(
            analytics.reorder_point(item, lead_time=5, stock_seguridad=4), 14)
        self.assertEqual(
            analytics.reorder_qty(
                item, lead_time=2, dias_cobertura=7, stock_seguridad=4),
            17)

    def test_ejemplo_tiene_xyz_y_colchon(self):
        inv = store.reset_inventory()
        self.assertTrue(inv)
        for fila in inv:
            self.assertIn(fila.get("xyzClase"), ("X", "Y", "Z"))
            self.assertIsNotNone(fila.get("xyzCv"))
            self.assertIsNotNone(fila.get("stockSeguridad"))
            self.assertIsNotNone(fila.get("puntoReorden"))


if __name__ == "__main__":
    unittest.main()
