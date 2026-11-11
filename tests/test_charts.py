"""Graficas del dashboard y resumenes para las pantallas de analisis."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.data import analytics
from app.widgets.chart_card import ChartDialog, PreviewChartCard


class TestResumenes(unittest.TestCase):
    def test_ingresos_por_categoria_agrupa_y_ordena(self):
        filas = [
            {"categoria": "Frutas", "ingresos": 100.0},
            {"categoria": "Bebidas", "ingresos": 40.0},
            {"categoria": "Frutas", "ingresos": 60.0},
        ]
        data = analytics.revenue_by_category(filas)
        self.assertEqual([d["categoria"] for d in data], ["Bebidas", "Frutas"])
        self.assertEqual(data[-1]["ingresos"], 160.0)

    def test_abc_summary_reparte_ingresos_y_productos(self):
        clases = [
            {"clase": "A", "ingresos": 80.0},
            {"clase": "A", "ingresos": 20.0},
            {"clase": "B", "ingresos": 50.0},
            {"clase": "C", "ingresos": 50.0},
        ]
        resumen = analytics.abc_summary(clases)
        por_clase = {r["clase"]: r for r in resumen}
        self.assertEqual(por_clase["A"]["productos"], 2)
        self.assertEqual(por_clase["A"]["pct_ingresos"], 50.0)
        self.assertEqual(por_clase["B"]["productos"], 1)
        self.assertAlmostEqual(
            sum(r["pct_ingresos"] for r in resumen), 100.0, places=6)


class TestXYZ(unittest.TestCase):
    def test_clase_por_variabilidad(self):
        self.assertEqual(analytics.xyz_class([10, 10, 10, 10])["clase"], "X")
        self.assertEqual(analytics.xyz_class([10, 0, 10, 5])["clase"], "Y")
        self.assertEqual(analytics.xyz_class([10, 0, 0, 0])["clase"], "Z")
        self.assertEqual(analytics.xyz_class([0, 0, 0])["clase"], "—")
        self.assertIsNone(analytics.xyz_class([])["cv"])

    def test_matriz_abc_xyz_cruza_productos(self):
        abc = [
            {"nombre": "A1", "clase": "A", "ingresos": 100.0},
            {"nombre": "C1", "clase": "C", "ingresos": 10.0},
            {"nombre": "SinXYZ", "clase": "B", "ingresos": 5.0},
        ]
        xyz = {"A1": {"clase": "X"}, "C1": {"clase": "Z"}}
        celdas = {(c["abc"], c["xyz"]): c
                  for c in analytics.abc_xyz_matrix(abc, xyz)}
        self.assertEqual(celdas[("A", "X")]["productos"], ["A1"])
        self.assertEqual(celdas[("C", "Z")]["productos"], ["C1"])
        self.assertEqual(celdas[("B", "Y")]["productos"], [])

    def test_reporte_diario_agrega_y_ordena(self):
        filas = [
            {"fecha": "2026-11-02", "cantidad": 2, "ingresos": 20},
            {"fecha": "2026-11-01", "cantidad": 1, "ingresos": 10},
            {"fecha": "2026-11-02", "cantidad": 3, "ingresos": 30},
        ]
        serie = analytics.report_daily_series(filas)
        self.assertEqual([d["fecha"] for d in serie], ["2026-11-01", "2026-11-02"])
        self.assertEqual(serie[-1]["cantidad"], 5)
        self.assertEqual(serie[-1]["ingresos"], 50)


class TestReporteVentas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _screen(self):
        from app.screens.sales_screen import SalesScreen
        return SalesScreen(on_navigate=lambda _s: None, on_logout=lambda: None)

    def test_lista_de_productos_y_reporte_filtrado(self):
        screen = self._screen()
        self.assertGreater(screen.product_list.count(), 0)
        for i in range(screen.product_list.count()):
            item = screen.product_list.item(i)
            item.setCheckState(Qt.Checked if item.text() == "Mango" else Qt.Unchecked)
        screen._generate_report()
        self.assertIsNotNone(screen.report)
        self.assertEqual([r["nombre"] for r in screen.report["por_producto"]], ["Mango"])
        self.assertIn("420 unidades", screen.report_totals.text())
        self.assertEqual(screen.report_table.rowCount(), 1)

    def test_sin_seleccion_usa_todos(self):
        screen = self._screen()
        screen._check_all_products(False)
        screen._generate_report()
        self.assertEqual(len(screen.report["por_producto"]), len(screen.all_rows))

    def test_comparacion_anual_con_y_sin_datos(self):
        from app.screens.sales_screen import SalesScreen
        actual = {"ingresos": 120.0}
        previo = {"totales": {"ingresos": 100.0}}
        self.assertIn("+20.0%", SalesScreen._comparison_text(actual, previo))
        sin_datos = {"totales": {"ingresos": 0.0}}
        self.assertIn("sin ventas", SalesScreen._comparison_text(actual, sin_datos))
        self.assertEqual(SalesScreen._comparison_text(actual, None), "")


class TestTarjetaGrafica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_tarjeta_muestra_titulo_y_abre_dialogo(self):
        def dibujar(canvas):
            canvas.axes.bar(["A", "B"], [1, 2])
            canvas.redraw()

        card = PreviewChartCard(
            "Prueba", "Subtitulo", draw=dibujar,
            expanded_draw=dibujar, expanded_height=4.0,
        )
        self.assertEqual(card.title_label.text(), "Prueba")
        self.assertEqual(card.subtitle_label.text(), "Subtitulo")
        self.assertTrue(card.canvas.axes.patches)
        dialogo = ChartDialog(card, "Prueba", "Subtitulo", dibujar, height=4.0)
        self.assertEqual(dialogo.windowTitle(), "Prueba")
        dialogo.close()

    def test_clic_en_la_grafica_emite_ampliar(self):
        card = PreviewChartCard("Prueba", "Subtitulo")
        eventos = []
        card.activated.connect(lambda: eventos.append(True))
        QTest.mouseClick(card.canvas, Qt.LeftButton)
        self.assertEqual(len(eventos), 1)


if __name__ == "__main__":
    unittest.main()
