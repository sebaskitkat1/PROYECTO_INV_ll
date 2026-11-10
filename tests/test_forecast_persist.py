"""Guardado del pronostico en pronosticos* y boton de la pantalla."""
import datetime as dt
import os
import unittest
from contextlib import nullcontext
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"  # pruebas deterministas, sin base

from PySide6.QtWidgets import QApplication

from app.data import repository
from app.data.app_state import AppState
from app.screens.prediction_screen import PredictionScreen


class _Cursor:
    def __init__(self):
        self.ejecutados = []
        self._fila = None
        self.lastrowid = 0
        self.productos = {"Mango": 10, "Fresa": 11}

    def execute(self, sql, params=()):
        self.ejecutados.append((sql, params))
        if "FROM modelos_pronostico" in sql:
            self._fila = {"id_modelo": 1}
        elif "FROM productos" in sql:
            self._fila = {"id_producto": self.productos.get(params[0])}
        elif sql.startswith("INSERT INTO pronosticos"):
            self.lastrowid = 77
            self._fila = None
        else:
            self._fila = None

    def fetchone(self):
        return self._fila

    def executemany(self, sql, filas):
        self.ejecutados.append((sql, list(filas)))


class TestGuardarPronostico(unittest.TestCase):
    def test_inserta_cabecera_diario_y_reparto(self):
        cur = _Cursor()
        hist = [(dt.date(2026, 9, 1), 100.0), (dt.date(2026, 9, 2), 110.0)]
        diario = [(dt.date(2026, 9, 3), 120.0), (dt.date(2026, 9, 4), 130.0)]
        productos = [{"nombre": "Mango", "actual": 100, "predicho": 120,
                      "crecimiento": 20.0}]
        bt = {"mae_modelo": 1.5, "mae_naive": 2.0, "mae_ma7": 2.5, "gana": False}
        with patch("app.data.repository._hay_base", return_value=True), \
                patch("app.data.repository._require_role", return_value="Administrador"), \
                patch("app.data.repository.sucursal_id", return_value=3), \
                patch("app.data.repository.db.transaction",
                      return_value=nullcontext(cur)):
            id_pronostico = repository.save_forecast(hist, diario, productos, bt, 9)

        self.assertEqual(id_pronostico, 77)
        cabecera = next(p for s, p in cur.ejecutados if s.startswith("INSERT INTO pronosticos"))
        self.assertEqual(cabecera[:4], (1, 3, 9, 2))
        self.assertAlmostEqual(cabecera[4], 18.18)
        self.assertEqual(cabecera[-1], 1)
        diarios = next(f for s, f in cur.ejecutados if "pronostico_diario" in s)
        self.assertEqual(len(diarios), 2)
        self.assertIn(("INSERT INTO pronostico_producto (id_pronostico, id_producto, "
                       "ingresos_actual, ingresos_predicho, crecimiento_pct) "
                       "VALUES (%s, %s, %s, %s, %s)",
                       (77, 10, 100.0, 120.0, 20.0)), cur.ejecutados)


class TestPantallaPronostico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        AppState.clear()

    def test_sin_base_no_guarda(self):
        s = PredictionScreen(on_navigate=lambda _x: None, on_logout=lambda: None)
        self.assertFalse(s._online)
        self.assertFalse(s.save_btn.isEnabled())
        self.assertIn("ejemplo", s.status_label.text())

    def test_guardar_llama_al_repositorio(self):
        AppState.set_user("admin@frutidata.local", user_id=1)
        s = PredictionScreen(on_navigate=lambda _x: None, on_logout=lambda: None)
        s._online = True
        s.save_btn.setEnabled(True)
        with patch("app.screens.prediction_screen.repository.save_forecast",
                   return_value=42) as guardar, \
                patch("app.screens.prediction_screen.QMessageBox.warning"):
            s._save_forecast()
        args = guardar.call_args[0]
        self.assertEqual(len(args[0]), len(s._historia()))
        self.assertEqual(len(args[1]), 30)
        self.assertEqual(len(args[2]), 10)
        self.assertIn("mae_modelo", args[3])
        self.assertIn("gana", args[3])
        self.assertEqual(args[4], 1)
        self.assertIn("42", s.status_label.text())


if __name__ == "__main__":
    unittest.main()
