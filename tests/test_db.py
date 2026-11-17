"""Cache de disponibilidad de la base: 30 s tras un fallo, sin caducidad tras exito."""
import unittest
from unittest.mock import patch

from app.data import db


class _Conexion:
    def close(self):
        pass


class TestDisponibilidad(unittest.TestCase):
    def setUp(self):
        db.reset_availability()

    def tearDown(self):
        db.reset_availability()

    def test_fallo_se_recuerda_30s_y_exito_no_caduca(self):
        reloj = [100.0]
        intentos = [0]

        def falso_connect():
            intentos[0] += 1
            if intentos[0] == 1:
                db._marcar_fallo()
                raise db.DBError("sin conexion")
            db._marcar_exito()
            return _Conexion()

        with patch.object(db, "_reloj", side_effect=lambda: reloj[0]), \
                patch.object(db, "connect", side_effect=falso_connect):
            self.assertFalse(db.available())
            self.assertFalse(db.available())
            self.assertEqual(intentos[0], 1)

            reloj[0] += 29.9
            self.assertFalse(db.available())
            self.assertEqual(intentos[0], 1)

            reloj[0] += 0.2
            self.assertTrue(db.available())
            self.assertEqual(intentos[0], 2)

            reloj[0] += 99999
            self.assertTrue(db.available())
            self.assertEqual(intentos[0], 2)

    def test_reset_permite_reintentar_de_inmediato(self):
        with patch.object(db, "connect", side_effect=db.DBError("sin conexion")):
            self.assertFalse(db.available())
            self.assertFalse(db.available())
        db.reset_availability()
        with patch.object(db, "connect", return_value=_Conexion()):
            self.assertTrue(db.available())


if __name__ == "__main__":
    unittest.main()
