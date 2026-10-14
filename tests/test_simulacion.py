"""Simulacion: FIFO exacto, caducidad, politicas sin futuro y walk-forward."""
import datetime as dt
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from scripts.simulacion import sim_lib


def serie_lineal(inicio, n, paso=10):
    base = dt.date(2026, 9, 1)
    return [(base + dt.timedelta(days=i), inicio + paso * i) for i in range(n)]


class TestInventarioFIFO(unittest.TestCase):
    def test_venta_exacta_sin_merma(self):
        r = sim_lib.simulate_inventory([5, 5], [5, 5], vida=3, costo=10, precio=18)
        self.assertEqual((r["vendido"], r["merma"], r["perdidas"], r["utilidad"]), (10.0, 0.0, 0.0, 80.0))
        self.assertEqual(r["inv_final"], 0.0)
        # la suma diaria economica cuadra con el cierre
        self.assertAlmostEqual(sum(f["eco"] for f in r["filas"]), r["utilidad_cierre"])

    def test_cierre_valua_inventario_final(self):
        r = sim_lib.simulate_inventory([0], [5], vida=30, costo=10, precio=18)
        self.assertEqual(r["utilidad"], -50.0)
        self.assertEqual(r["utilidad_cierre"], 0.0)  # lo comprado sigue valiendo a costo

    def test_caducidad_se_tira_y_cuenta(self):
        r = sim_lib.simulate_inventory([1, 1, 1], [10, 0, 0], vida=2, costo=10, precio=18)
        self.assertEqual(r["vendido"], 2.0)
        self.assertEqual(r["merma"], 8.0)

    def test_faltante_es_venta_perdida(self):
        r = sim_lib.simulate_inventory([10], [4], vida=5, costo=10, precio=18)
        self.assertEqual((r["vendido"], r["perdidas"]), (4.0, 6.0))

    def test_fifo_vende_lo_viejo(self):
        # lote viejo de 3 y lote nuevo de 10, demanda 5: el viejo se agota
        r = sim_lib.simulate_inventory([0, 5], [3, 10], vida=10, costo=10, precio=18)
        self.assertEqual(r["vendido"], 5.0)
        self.assertEqual(r["merma"], 0.0)


class TestPoliticas(unittest.TestCase):
    def test_base_usa_semana_pasada(self):
        fechas = [dt.date(2026, 9, 1) + dt.timedelta(days=i) for i in range(10)]
        vals = [float(i) for i in range(10)]
        self.assertEqual(sim_lib.pedido_base(fechas, vals), 2.0)

    def test_modelo_deriva_solo_de_historia(self):
        from app.data import analytics
        hist = serie_lineal(100, 22)
        fechas = [d for d, _ in hist]
        vals = [v for _, v in hist]
        p = sim_lib.pedido_modelo(fechas, vals, 5.0)
        f = analytics.forecast_daily(list(zip(fechas, vals)), 1)[0][1]
        self.assertAlmostEqual(p, f + 5.0)


class TestNewsvendor(unittest.TestCase):
    def test_caro_pide_conservador(self):
        res = {0: [-2.0, -1.0, 0.0, 1.0, 2.0], 1: [-2.0, -1.0, 0.0, 1.0, 2.0]}
        # margen alto (60/18): cuantil 0.7 -> sobre el pronostico
        alto = sim_lib.pedido_newsvendor(10.0, res, precio=60.0, costo=18.0)
        # margen bajo (60/54): cuantil 0.1 -> bajo el pronostico
        bajo = sim_lib.pedido_newsvendor(10.0, res, precio=60.0, costo=54.0)
        self.assertGreater(alto, 10.0)
        self.assertLess(bajo, 10.0)

    def test_residuales_solo_pasado(self):
        hist = serie_lineal(100, 30)
        fechas = [d for d, _ in hist]
        vals = [v for _, v in hist]
        res = sim_lib.residuales_rodantes(fechas[:20], vals[:20])
        self.assertTrue(len(res) > 0)
        self.assertTrue(all(0 <= wd <= 6 for wd in res))
        # serie perfecta de paso 10: ningun error supera un paso
        todos = [e for v in res.values() for e in v]
        self.assertLessEqual(max(abs(e) for e in todos), 10.0)

class TestWalkForward(unittest.TestCase):
    def test_metricas_y_residuales(self):
        hist = serie_lineal(100, 30)
        wf = sim_lib.walk_forward_weekly([d for d, _ in hist], [v for _, v in hist])
        self.assertGreater(wf["origenes"], 0)
        self.assertLess(wf["mae_modelo"], wf["mae_naive"])
        self.assertTrue(wf["gana"])
        self.assertIn(5, wf["residuales"])  # hay sabados en la ventana


if __name__ == "__main__":
    unittest.main()
