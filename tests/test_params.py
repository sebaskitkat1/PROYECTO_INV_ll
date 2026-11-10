"""Umbrales desde parametros_sistema y defaults equivalentes."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from app.data import analytics, params, repository


class TestDefaults(unittest.TestCase):
    def test_claves_esperadas(self):
        d = params.defaults()
        for clave in ("umbral_advertencia", "objetivo_reorden", "alerta_caducidad_dias",
                      "dias_alerta_agotar", "abc_corte_a", "abc_corte_b",
                      "ventana_consumo_dias", "lead_time_default",
                      "dias_seguridad", "dias_cobertura"):
            self.assertIn(clave, d)
        self.assertEqual(d["umbral_advertencia"], 1.25)
        self.assertEqual(d["objetivo_reorden"], 2.0)
        self.assertEqual(d["lead_time_default"], 2.0)
        self.assertEqual(d["dias_seguridad"], 1.0)

    def test_parse_sobrescribe_y_ignora_basura(self):
        out = params.parse([
            {"clave": "umbral_advertencia", "valor": "1.10"},
            {"clave": "objetivo_reorden", "valor": "no-numero"},
            {"clave": "desconocida", "valor": "9"},
        ])
        self.assertEqual(out["umbral_advertencia"], 1.10)
        self.assertEqual(out["objetivo_reorden"], 2.0)
        self.assertNotIn("desconocida", out)

    def test_repository_sin_base_usa_defaults(self):
        self.assertEqual(repository.system_params(), params.defaults())


class TestReglasConParametros(unittest.TestCase):
    def test_stock_status_con_umbral_custom(self):
        self.assertEqual(analytics.stock_status(11, 10, 1)[0], "advertencia")
        self.assertEqual(analytics.stock_status(11, 10, 1, umbral_advertencia=1.0)[0], "optimo")
        self.assertEqual(analytics.stock_status(11, 10, 1, umbral_advertencia=1.5)[0], "advertencia")

    def test_reorder_con_objetivo_custom(self):
        item = {"stockActual": 5, "stockMinimo": 10}
        self.assertEqual(analytics.reorder_qty(item), 15)
        self.assertEqual(analytics.reorder_qty(item, objetivo=3.0), 25)

    def test_reorder_con_consumo_y_lead_time(self):
        item = {"stockActual": 5, "stockMinimo": 10, "consumoDiario": 2}
        # 2 unidades/dia x (2 lead + 1 seguridad + 7 cobertura) = 20
        self.assertEqual(analytics.reorder_qty(item), 15)
        self.assertEqual(analytics.reorder_qty(item, lead_time=4), 19)
        self.assertEqual(analytics.reorder_point(item), 10)
        self.assertEqual(analytics.reorder_point(item, lead_time=4, dias_seguridad=2), 12)

    def test_abc_con_cortes_custom(self):
        pareto = [{"nombre": "A", "ingresos": 50}, {"nombre": "B", "ingresos": 50}]
        default = analytics.abc_classes(pareto)
        self.assertEqual([d["clase"] for d in default], ["A", "C"])
        custom = analytics.abc_classes(pareto, corte_a=60, corte_b=100)
        self.assertEqual([d["clase"] for d in custom], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
