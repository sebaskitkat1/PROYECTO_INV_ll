"""Repositorio: mapeo de filas, fallback a ejemplo y auth contra la base."""
import os
import unittest
import uuid
from unittest.mock import patch

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
        self.assertIsNone(r["leadTimeDias"])
        self.assertIsNone(r["puntoReorden"])
        self.assertIsNone(r["sugerido"])
        self.assertEqual(r["stockSeguridad"], 0.0)
        self.assertIsNone(r["xyzClase"])
        self.assertIsNone(r["xyzCv"])
        self.assertEqual(r["xyzDias"], 0)
        self.assertEqual(r["estado"], "sin_minimo")

    def test_inventario_con_sugerido(self):
        r = repository.map_inventario_row({
            "id_ingrediente": 2, "nombre": "Z", "unidad": "kg",
            "stock_actual": 3, "stock_minimo": 5, "consumo_diario": 1.5,
            "dias_agotar": 2, "estado": "critico", "lead_time_dias": 2,
            "punto_reorden": 5, "stock_seguridad": 1.5,
            "merma_ventana": 0.75, "sugerido": 9, "proveedor": "Proveedor",
            "xyz_clase": "Z", "xyz_cv": 1.4, "xyz_sigma": 2.5,
            "xyz_media": 1.1, "xyz_dias_con_datos": 18})
        self.assertEqual(r["leadTimeDias"], 2.0)
        self.assertEqual(r["puntoReorden"], 5.0)
        self.assertEqual(r["stockSeguridad"], 1.5)
        self.assertEqual(r["mermaVentana"], 0.75)
        self.assertEqual(r["xyzClase"], "Z")
        self.assertEqual(r["xyzCv"], 1.4)
        self.assertEqual(r["xyzSigma"], 2.5)
        self.assertEqual(r["xyzMedia"], 1.1)
        self.assertEqual(r["xyzDias"], 18)
        self.assertEqual(r["sugerido"], 9)
        self.assertEqual(r["proveedor"], "Proveedor")

    def test_etiqueta_fuente_ejemplo(self):
        self.assertEqual(repository.etiqueta_fuente(), "ejemplo")

    def test_bitacora_mapea_resultado_y_fecha(self):
        import datetime
        r = repository.map_bitacora_row({
            "fecha_hora": datetime.datetime(2026, 10, 19, 8, 30), "usuario": None,
            "correo_intentado": "caja@frutidata.local", "exitoso": 1, "equipo": None})
        self.assertEqual(r["fecha"], "2026-10-19 08:30")
        self.assertEqual(r["usuario"], "—")
        self.assertEqual(r["resultado"], "Correcto")
        self.assertEqual(r["equipo"], "—")


class TestUsuariosDemo(unittest.TestCase):
    def test_user_id_by_email_activo(self):
        with patch.object(repository, "_hay_base"), \
                patch.object(repository.db, "fetchall",
                             return_value=[{"id_usuario": 7}]) as consulta:
            self.assertEqual(repository.user_id_by_email(" caja@x "), 7)
        self.assertEqual(consulta.call_args.args[1], ("caja@x",))

    def test_user_id_by_email_inexistente(self):
        with patch.object(repository, "_hay_base"), \
                patch.object(repository.db, "fetchall", return_value=[]):
            self.assertIsNone(repository.user_id_by_email("nadie@x"))


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


class TestAuthSimulado(unittest.TestCase):
    def setUp(self):
        import bcrypt
        self.hash_valido = bcrypt.hashpw(b"clave-demo", bcrypt.gensalt()).decode()
        self.user = {
            "id_usuario": 3, "nombre": "Caja Demo",
            "correo": "caja@frutidata.local", "password_hash": self.hash_valido,
            "id_rol": 3, "activo": 1, "rol_nombre": "Cajero",
        }
        self.fallos_correo = 0
        self.fallos_equipo = 0
        self.ejecutados = []

    def _fetchall(self, sql, params=()):
        if "correo_intentado" in sql:
            return [{"n": self.fallos_correo}]
        if "equipo = %s" in sql:
            return [{"n": self.fallos_equipo}]
        if "FROM usuarios" in sql:
            return [self.user]
        raise AssertionError(f"consulta inesperada: {sql}")

    def _execute(self, sql, params=()):
        self.ejecutados.append((sql, params))
        return 1

    def _auth(self, correo="caja@frutidata.local", password="clave-demo"):
        with patch.object(repository, "_hay_base"), \
                patch.object(repository, "system_params", return_value={}), \
                patch.object(repository, "_equipo", return_value="PC-PRUEBA"), \
                patch.object(repository.db, "fetchall", side_effect=self._fetchall), \
                patch.object(repository.db, "execute", side_effect=self._execute):
            return repository.auth(correo, password)

    def test_bloqueo_tras_cinco_fallos_por_correo(self):
        self.fallos_correo = 5
        with self.assertRaises(repository.AuthError):
            self._auth()
        self.assertEqual(self.ejecutados, [])

    def test_bloqueo_por_equipo_con_umbral_alto(self):
        self.fallos_equipo = 20
        with self.assertRaises(repository.AuthError) as ctx:
            self._auth()
        self.assertIn("equipo", str(ctx.exception))
        self.assertEqual(self.ejecutados, [])

    def test_credenciales_validas(self):
        user = self._auth()
        self.assertEqual(user["rol"], "Cajero")
        self.assertEqual(user["id"], 3)
        self.assertEqual(len(self.ejecutados), 2)
        self.assertIn("bitacora_accesos", self.ejecutados[0][0])
        self.assertIn("ultimo_acceso", self.ejecutados[1][0])

    def test_password_incorrecta_registra_fallo(self):
        with self.assertRaises(repository.AuthError):
            self._auth(password="otra-clave")
        self.assertEqual(len(self.ejecutados), 1)
        self.assertEqual(self.ejecutados[0][1][2], 0)

    def test_hash_invalido_se_registra_y_rechaza(self):
        self.user["password_hash"] = "esto-no-es-bcrypt"
        with self.assertLogs("cosecha.auth", level="WARNING") as logs:
            with self.assertRaises(repository.AuthError):
                self._auth()
        self.assertIn("ValueError", logs.output[0])
        self.assertEqual(len(self.ejecutados), 1)
        self.assertEqual(self.ejecutados[0][1][2], 0)


class TestAuthReal(unittest.TestCase):
    def test_rechaza_hash_invalido_y_registra_bitacora(self):
        os.environ["CAFE_DATOS"] = "db"
        try:
            if not db.available():
                self.skipTest("sin MySQL a la mano")
            # correo unico: evita que corridas repetidas activen el bloqueo
            correo = f"prueba-{uuid.uuid4().hex}@frutidata.local"
            antes = db.fetchall("SELECT COUNT(*) AS n FROM bitacora_accesos")[0]["n"]
            with self.assertRaises(repository.AuthError):
                repository.auth(correo, "cualquier-clave")
            despues = db.fetchall("SELECT COUNT(*) AS n FROM bitacora_accesos")[0]["n"]
            self.assertEqual(despues, antes + 1)
        finally:
            os.environ["CAFE_DATOS"] = "mock"


if __name__ == "__main__":
    unittest.main()
