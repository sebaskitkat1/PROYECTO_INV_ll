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
