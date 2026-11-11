"""F02+F06: pronostico sobre fecha real, sin sesgo, con backtest y reparto."""
import datetime as dt
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from app import styles
from app.data import analytics


def serie_lineal(inicio, n, paso=10):
    base = dt.date(2026, 9, 1)
    return [(base + dt.timedelta(days=i), inicio + paso * i) for i in range(n)]


def tras_historial(hist):
    """Primer dia despues del historico (para pruebas deterministas)."""
    return hist[-1][0] + dt.timedelta(days=1)


class TestPronosticoFechas(unittest.TestCase):
    def test_nivel_en_ultimo_punto_sin_sesgo(self):
        hist = serie_lineal(100, 10)
        fut = analytics.forecast_daily(hist, 3, start=tras_historial(hist))
        self.assertEqual([v for _, v in fut], [200.0, 210.0, 220.0])

    def test_ndigits_segun_escala(self):
        hist = serie_lineal(100, 10)
        inicio = tras_historial(hist)
        unid = [(d, 6.3) for d, _ in hist]
        self.assertEqual(
            [v for _, v in analytics.forecast_daily(unid, 1, 0, start=inicio)],
            [6.0])
        # en pesos se redondea a decenas como antes
        self.assertEqual(
            [v for _, v in analytics.forecast_daily(hist, 1, start=inicio)],
            [200.0])

    def test_pasos_diarios_consecutivos(self):
        hist = serie_lineal(100, 7)
        fut = analytics.forecast_daily(hist, 30, start=tras_historial(hist))
        self.assertEqual(len(fut), 30)
        dias = [d for d, _ in fut]
        self.assertEqual(dias[0], dt.date(2026, 9, 8))
        self.assertTrue(all((b - a).days == 1 for a, b in zip(dias, dias[1:])))
        self.assertTrue(all(v >= 0 for _, v in fut))

    def test_arranca_hoy_si_el_historial_es_viejo(self):
        hoy = dt.date.today()
        hist = [(hoy - dt.timedelta(days=90), 100.0),
                (hoy - dt.timedelta(days=60), 120.0)]
        fut = analytics.forecast_daily(hist, 3)
        self.assertEqual(fut[0][0], hoy)
        self.assertTrue(all(d >= hoy for d, _ in fut))

    def test_start_no_pisa_el_ultimo_dato(self):
        hist = serie_lineal(100, 5)
        fut = analytics.forecast_daily(hist, 2, start=hist[-1][0])
        self.assertEqual(fut[0][0], hist[-1][0] + dt.timedelta(days=1))

    def test_sin_historial_o_sin_pasos(self):
        self.assertEqual(analytics.forecast_daily([], 3), [])
        hist = serie_lineal(100, 5)
        self.assertEqual(analytics.forecast_daily(hist, 0), [])

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

    def test_backtest_claves_y_metricas(self):
        hist = serie_lineal(100, 14)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        for k in ("mae_modelo", "mae_naive", "mae_ma7", "mape_modelo",
                  "wape_modelo", "wape_naive", "wape_ma7", "smape_modelo",
                  "sesgo_modelo", "gana", "n", "n_origenes",
                  "horizonte_medio", "horizonte_max", "suficiente", "motivo"):
            self.assertIn(k, bt)
        self.assertGreaterEqual(bt["wape_modelo"], 0.0)
        self.assertIsNotNone(bt["sesgo_modelo"])
        self.assertTrue(bt["suficiente"])

    def test_backtest_insuficiente_sin_metricas(self):
        hist = serie_lineal(100, 1)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        self.assertFalse(bt["suficiente"])
        self.assertFalse(bt["gana"])
        self.assertEqual(bt["n_origenes"], 0)
        self.assertIsNone(bt["wape_modelo"])
        self.assertIsNone(bt["sesgo_modelo"])

    def test_backtest_mide_horizonte_real(self):
        # una observacion cada 7 dias: el error se mide a 7 dias, no a 1
        base = dt.date(2026, 1, 5)
        hist = [(base + dt.timedelta(days=7 * i), 100.0 + 10 * i)
                for i in range(12)]
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        self.assertEqual(bt["horizonte_medio"], 7.0)
        self.assertEqual(bt["horizonte_max"], 7)

    def test_backtest_sesgo_con_signo(self):
        # el modelo se queda corto frente al salto final: sesgo negativo
        hist = serie_lineal(100, 10)
        hist[-1] = (hist[-1][0], 900.0)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        self.assertLess(bt["sesgo_modelo"], 0.0)


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
        hist = serie_lineal(6000, 7, paso=-200)
        fut = analytics.forecast_daily(hist, 6, start=tras_historial(hist))
        g = analytics.horizon_growth(4800.0, [v for _, v in fut])
        self.assertLess(g, 0)

    def test_reparto_compara_ventanas_equivalentes(self):
        det = [{"nombre": "A", "ingresos": 1000.0},
               {"nombre": "B", "ingresos": 1000.0}]
        filas = analytics.product_forecast_share(det, 3000.0, 2)
        self.assertEqual(sum(r["predicho"] for r in filas), 3000)
        for fila in filas:
            self.assertEqual(fila["predicho"], 1500)
            self.assertEqual(fila["crecimiento"], 50.0)

    def test_reparto_ajusta_redondeo(self):
        det = [{"nombre": "A", "ingresos": 1.0},
               {"nombre": "B", "ingresos": 1.0},
               {"nombre": "C", "ingresos": 1.0}]
        filas = analytics.product_forecast_share(det, 100.0, 3)
        self.assertEqual(sum(r["predicho"] for r in filas), 100)

    def test_reparto_sin_detalle(self):
        self.assertEqual(analytics.product_forecast_share([], 1000.0, 5), [])


class TestGraficaPronostico(unittest.TestCase):
    def test_ventana_acota_historia_y_termina_antes_del_pronostico(self):
        base = dt.date(2026, 9, 1)
        hist = [(base + dt.timedelta(days=i), 100.0 + i) for i in range(90)]
        futuro = [(base + dt.timedelta(days=90 + i), 200.0) for i in range(5)]
        visible = analytics.chart_history_window(hist, futuro)
        self.assertEqual(visible[0][0], base + dt.timedelta(days=60))
        self.assertEqual(visible[-1][0], base + dt.timedelta(days=89))
        self.assertEqual(len(visible), 30)

    def test_ventana_usa_ultimo_dato_si_no_hay_pronostico(self):
        hist = [(dt.date(2026, 9, 1), 100.0), (dt.date(2026, 9, 2), 110.0)]
        visible = analytics.chart_history_window(hist)
        self.assertEqual(visible, hist)

    def test_pico_aislado_queda_fuera_de_escala(self):
        base = dt.date(2026, 11, 1)
        hist = [(base + dt.timedelta(days=i), v) for i, v in enumerate(
            [100.0, 110.0, 120.0, 130.0, 140.0, 900.0])]
        futuro = [(base + dt.timedelta(days=6 + i), 150.0) for i in range(3)]
        escala = analytics.chart_scale(hist, futuro)
        self.assertIsNotNone(escala["tope"])
        self.assertLess(escala["tope"], 900.0)
        self.assertGreaterEqual(escala["tope"], 150.0 * 1.05)
        self.assertEqual([v for _, v in escala["fuera"]], [900.0])

    def test_sin_picos_no_fija_tope(self):
        base = dt.date(2026, 11, 1)
        hist = [(base + dt.timedelta(days=i), v) for i, v in enumerate(
            [100.0, 110.0, 120.0, 130.0])]
        futuro = [(base + dt.timedelta(days=4 + i), 140.0) for i in range(2)]
        escala = analytics.chart_scale(hist, futuro)
        self.assertIsNone(escala["tope"])
        self.assertEqual(escala["fuera"], [])

    def test_serie_plana_con_pico_tambien_se_recorta(self):
        base = dt.date(2026, 11, 1)
        hist = [(base + dt.timedelta(days=i), v) for i, v in enumerate(
            [0.0, 0.0, 0.0, 0.0, 900.0])]
        escala = analytics.chart_scale(hist, [])
        self.assertIsNotNone(escala["tope"])
        self.assertLess(escala["tope"], 900.0)
        self.assertEqual([v for _, v in escala["fuera"]], [900.0])

    def test_periodo_anterior_incluye_29_febrero(self):
        desde, hasta = analytics.previous_period(
            dt.date(2028, 2, 29), dt.date(2028, 3, 10))
        self.assertEqual(desde, dt.date(2027, 2, 28))
        self.assertEqual(hasta, dt.date(2027, 3, 10))


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
