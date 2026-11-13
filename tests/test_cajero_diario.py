"""Cajero automatico: guard de entorno demo y reabasto solo de ordenes propias."""
import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"

from app.data import db, repository
from scripts import cajero_diario


class TestGuardEntorno(unittest.TestCase):
    def test_sin_variable_aborta_sin_registrar_ventas(self):
        with patch.dict(os.environ, {"COSECHA_ENTORNO": ""}), \
                patch.object(db, "load_env", return_value={}), \
                patch.object(cajero_diario, "_configurar_logging"), \
                patch.object(repository, "register_sale") as venta, \
                patch.object(sys, "argv",
                             ["cajero_diario.py", "--tickets", "2"]):
            codigo = cajero_diario.main()
        self.assertNotEqual(codigo, 0)
        venta.assert_not_called()

    def test_dry_run_funciona_sin_variable(self):
        with patch.dict(os.environ, {"COSECHA_ENTORNO": ""}), \
                patch.object(db, "load_env", return_value={}), \
                patch.object(cajero_diario, "_configurar_logging"), \
                patch.object(repository, "register_sale") as venta, \
                patch.object(repository, "generate_purchase_order_ids") as generar, \
                patch.object(sys, "argv",
                             ["cajero_diario.py", "--tickets", "2", "--dry-run"]):
            codigo = cajero_diario.main()
        self.assertEqual(codigo, 0)
        venta.assert_not_called()
        generar.assert_not_called()

    def test_usuario_inexistente_aborta(self):
        with patch.dict(os.environ, {"COSECHA_ENTORNO": "demo"}), \
                patch.object(db, "load_env", return_value={}), \
                patch.object(db, "available", return_value=True), \
                patch.object(cajero_diario, "_configurar_logging"), \
                patch.object(cajero_diario, "_ya_corrio_hoy", return_value=False), \
                patch.object(repository, "user_id_by_email", return_value=None), \
                patch.object(repository, "register_sale") as venta, \
                patch.object(sys, "argv", ["cajero_diario.py"]):
            codigo = cajero_diario.main()
        self.assertEqual(codigo, 3)
        venta.assert_not_called()


class TestReabastoPropio(unittest.TestCase):
    def test_solo_recibe_ordenes_generadas_en_la_corrida(self):
        generadas = [[101, 102], [103]]
        abiertas = [
            {"id_orden": 55, "estado": "borrador"},
            {"id_orden": 101, "estado": "borrador"},
            {"id_orden": 102, "estado": "enviada"},
            {"id_orden": 103, "estado": "borrador"},
        ]
        correos = {"caja@frutidata.local": 3, "admin@frutidata.local": 1}
        with patch.dict(os.environ, {"COSECHA_ENTORNO": "demo"}), \
                patch.object(db, "load_env", return_value={}), \
                patch.object(db, "available", return_value=True), \
                patch.object(cajero_diario, "_configurar_logging"), \
                patch.object(cajero_diario, "_ya_corrio_hoy", return_value=False), \
                patch.object(repository, "user_id_by_email",
                             side_effect=lambda correo: correos[correo]), \
                patch.object(repository, "generate_purchase_order_ids",
                             side_effect=generadas), \
                patch.object(repository, "purchase_orders",
                             return_value=abiertas), \
                patch.object(repository, "receive_purchase_order") as recibir, \
                patch.object(repository, "pos_products",
                             return_value=[{"id_producto": 1, "unidad": "kg"}]), \
                patch.object(repository, "pos_payment_methods",
                             return_value=[{"id": 1}]), \
                patch.object(repository, "register_sale") as venta, \
                patch.object(repository, "purge_expired", return_value=0), \
                patch.object(sys, "argv",
                             ["cajero_diario.py", "--tickets", "2", "--seed", "7"]):
            codigo = cajero_diario.main()

        self.assertEqual(codigo, 0)
        recibidas = [llamada.args[0] for llamada in recibir.call_args_list]
        self.assertEqual(recibidas, [101, 102, 103])
        self.assertNotIn(55, recibidas)
        self.assertEqual(venta.call_count, 2)
        self.assertEqual(venta.call_args.args[2], 3)
        self.assertEqual(venta.call_args.kwargs.get("origen"), "simulado")


if __name__ == "__main__":
    unittest.main()
