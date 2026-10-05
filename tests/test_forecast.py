"""F02+F06: pronostico sobre fecha real, sin sesgo, con backtest y reparto."""
import datetime as dt
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app import styles
from app.data import analytics


def serie_lineal(inicio, n, paso=10):
    base = dt.date(2026, 9, 1)
    return [(base + dt.timedelta(days=i), inicio + paso * i) for i in range(n)]


class TestPronosticoFechas(unittest.TestCase):
    def test_nivel_en_ultimo_punto_sin_sesgo(self):
        hist = serie_lineal(100, 10)
        fut = analytics.forecast_daily(hist, 3)
        self.assertEqual([v for _, v in fut], [200.0, 210.0, 220.0])

    def test_pasos_diarios_consecutivos(self):
        hist = serie_lineal(100, 7)
        fut = analytics.forecast_daily(hist, 30)
        self.assertEqual(len(fut), 30)
        dias = [d for d, _ in fut]
        self.assertEqual(dias[0], dt.date(2026, 9, 8))
        self.assertTrue(all((b - a).days == 1 for a, b in zip(dias, dias[1:])))
        self.assertTrue(all(v >= 0 for _, v in fut))

    def test_parse_dia(self):
        hoy = dt.date(2026, 9, 30)
        self.assertEqual(analytics.parse_dia("Hoy", hoy), hoy)
        self.assertEqual(analytics.parse_dia("25 Sep", hoy), dt.date(2026, 9, 25))
        self.assertIsNone(analytics.parse_dia("ayer", hoy))
        self.assertIsNone(analytics.parse_dia("", hoy))

    def test_dow_neutro_con_pocos_datos(self):
        hist = serie_lineal(100, 7)
        self.assertEqual(analytics.dow_factors([d for d, _ in hist], [v for _, v in hist]), {})

    def test_dow_recupera_patron_semanal(self):
        base = dt.date(2026, 8, 3)  # lunes
        hist = [(base + dt.timedelta(days=i), 1000 + (300 if (base + dt.timedelta(days=i)).weekday() >= 5 else 0))
                for i in range(35)]
        fac = analytics.dow_factors([d for d, _ in hist], [v for _, v in hist])
        self.assertGreater(fac[5], fac[0])
        self.assertAlmostEqual(sum(fac.values()) / len(fac), 1.0, places=6)

    def test_backtest_gana_en_tendencia_clara(self):
        hist = serie_lineal(100, 14)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        self.assertTrue(bt["gana"])
        self.assertLess(bt["mae_modelo"], bt["mae_naive"])
        self.assertGreaterEqual(bt["mape_modelo"], 0.0)

    def test_backtest_claves(self):
        hist = serie_lineal(100, 10)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        for k in ("mae_modelo", "mae_naive", "mae_ma7", "mape_modelo", "gana", "n"):
            self.assertIn(k, bt)


class TestReparto(unittest.TestCase):
    def test_suma_cuadra_y_piso_cero(self):
        from app.data import mock_data
        det = mock_data.get_sales_detail()
        todos = analytics.product_forecast_share(det, 45000.0, len(det))
        self.assertLessEqual(abs(sum(r["predicho"] for r in todos) - 45000.0), len(det))
        self.assertTrue(all(r["predicho"] >= 0 for r in todos))
        top5 = analytics.product_forecast_share(det, 45000.0, 5)
        self.assertEqual([r["nombre"] for r in top5],
                         ["Mango", "Manzana Roja", "Uva",
                          "Naranja", "Fresa"])

    def test_tendencia_negativa_da_negativos(self):
        from app.data import mock_data
        det = mock_data.get_sales_detail()
        hist = serie_lineal(6000, 7, paso=-200)
        g = analytics.horizon_growth(4800.0, [v for _, v in analytics.forecast_daily(hist, 6)])
        self.assertLess(g, 0)


class TestSignoColor(unittest.TestCase):
    def test_signo_y_color(self):
        from app.screens.prediction_screen import PredictionScreen
        txt, color = PredictionScreen._crec_texto_color(12.5)
        self.assertEqual(txt, "+12.5%")
        self.assertEqual(color, styles.SAGE)
        txt, color = PredictionScreen._crec_texto_color(-22.8)
        self.assertEqual(txt, "-22.8%")
        self.assertEqual(color, styles.CLAY)
        txt, color = PredictionScreen._crec_texto_color(0.0)
        self.assertEqual(txt, "+0.0%")
        self.assertEqual(color, styles.SAGE)


if __name__ == "__main__":
    unittest.main()
