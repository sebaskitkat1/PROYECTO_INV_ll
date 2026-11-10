"""Punto de venta: catalogo, carrito, validaciones y navegacion."""
import os
import re
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CAFE_DATOS"] = "mock"

from PySide6.QtWidgets import QApplication

from app.data import db, repository
from app.data.app_state import AppState
from app.screens.pos_screen import PosScreen

RAIZ = Path(__file__).resolve().parent.parent


class TestSeedCatalogo(unittest.TestCase):
    def test_schema_tiene_al_menos_50_productos(self):
        texto = (RAIZ / "db" / "frutidata_schema.sql").read_text(encoding="utf-8")
        inicio = texto.index("INSERT INTO productos (id_categoria")
        fin = texto.index("INSERT INTO categorias_ingrediente", inicio)
        nombres = re.findall(r"SELECT '([^']+)' AS nombre", texto[inicio:fin])
        self.assertGreaterEqual(len(nombres), 50)
        self.assertEqual(len(nombres), len(set(nombres)))

    def test_schema_incluye_categorias_no_solo_frutas(self):
        texto = (RAIZ / "db" / "frutidata_schema.sql").read_text(encoding="utf-8")
        for categoria in ("Frutas", "Verduras", "Jugos", "Bebidas", "Snacks", "Abarrotes"):
            self.assertIn(f"('{categoria}')", texto)

    def test_cantidad_de_venta_es_decimal(self):
        texto = (RAIZ / "db" / "frutidata_schema.sql").read_text(encoding="utf-8")
        self.assertRegex(texto, r"cantidad\s+DECIMAL\(10,3\)")
        migracion = (RAIZ / "db" / "migrate_cantidades_decimales.sql").read_text(
            encoding="utf-8")
        self.assertIn("MODIFY COLUMN cantidad DECIMAL(10,3)", migracion)

    def test_migracion_completa_inventario_y_recetas(self):
        migracion = (RAIZ / "db" / "migrate_inventario_recetas.sql").read_text(
            encoding="utf-8")
        self.assertIn("INSERT INTO ingredientes", migracion)
        self.assertIn("INSERT INTO recetas", migracion)
        self.assertIn("INSERT INTO inventario", migracion)
        self.assertIn("INSERT INTO ingrediente_proveedor", migracion)

    def test_kpi_es_precio_promedio_por_unidad(self):
        texto = (RAIZ / "db" / "frutidata_schema.sql").read_text(encoding="utf-8")
        self.assertIn("h.ventas / NULLIF(h.unidades, 0)", texto)
        migracion = (RAIZ / "db" / "migrate_kpi_precio_unidad.sql").read_text(
            encoding="utf-8")
        self.assertIn("h.ventas / NULLIF(h.unidades, 0)", migracion)


class TestCatalogoReal(unittest.TestCase):
    def test_base_tiene_catalogo_amplio(self):
        os.environ["CAFE_DATOS"] = "db"
        try:
            if not db.available():
                self.skipTest("sin MySQL a la mano")
            filas = db.fetchall("SELECT COUNT(*) AS n FROM productos WHERE activo = 1")
            total = int(filas[0]["n"])
            self.assertGreaterEqual(total, 50)

            categorias = [f["nombre"] for f in db.fetchall(
                "SELECT nombre FROM categorias_producto")]
            for esperada in ("Frutas", "Verduras", "Jugos", "Bebidas", "Snacks", "Abarrotes"):
                self.assertIn(esperada, categorias)

            fyq = db.fetchall(
                "SELECT COUNT(*) AS n FROM productos p "
                "JOIN categorias_producto c ON c.id_categoria = p.id_categoria "
                "WHERE p.activo = 1 AND c.nombre IN ('Frutas', 'Verduras')")[0]["n"]
            self.assertGreater(int(fyq), total // 2)
        finally:
            os.environ["CAFE_DATOS"] = "mock"


class TestInventarioRecetasReal(unittest.TestCase):
    def test_todo_producto_tiene_receta_e_inventario(self):
        os.environ["CAFE_DATOS"] = "db"
        try:
            if not db.available():
                self.skipTest("sin MySQL a la mano")
            sin_receta = db.fetchall(
                "SELECT COUNT(*) AS n FROM productos p "
                "WHERE p.activo = 1 AND NOT EXISTS ("
                "  SELECT 1 FROM recetas r WHERE r.id_producto = p.id_producto)")[0]["n"]
            sin_inventario = db.fetchall(
                "SELECT COUNT(*) AS n FROM ingredientes i "
                "WHERE i.activo = 1 AND NOT EXISTS ("
                "  SELECT 1 FROM inventario inv WHERE inv.id_ingrediente = i.id_ingrediente)")[0]["n"]
            sin_proveedor = db.fetchall(
                "SELECT COUNT(*) AS n FROM ingredientes i "
                "WHERE i.activo = 1 AND NOT EXISTS ("
                "  SELECT 1 FROM ingrediente_proveedor ip "
                "  WHERE ip.id_ingrediente = i.id_ingrediente AND ip.es_principal = 1)")[0]["n"]
            self.assertEqual(int(sin_receta), 0)
            self.assertEqual(int(sin_inventario), 0)
            self.assertEqual(int(sin_proveedor), 0)
        finally:
            os.environ["CAFE_DATOS"] = "mock"


class TestRegisterSaleValidaciones(unittest.TestCase):
    def test_ticket_vacio(self):
        with self.assertRaises(ValueError):
            repository.register_sale([], 1, 1)

    def test_cantidad_cero(self):
        with self.assertRaises(ValueError):
            repository.register_sale(
                [{"id_producto": 1, "cantidad": 0}], 1, 1)

    def test_cantidad_demasiado_pequena(self):
        with self.assertRaises(ValueError):
            repository.register_sale(
                [{"id_producto": 1, "cantidad": 0.0001}], 1, 1)

    def test_sin_usuario(self):
        with self.assertRaises(ValueError):
            repository.register_sale(
                [{"id_producto": 1, "cantidad": 1}], 1, None)


class TestPosScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        os.environ["CAFE_DATOS"] = "mock"
        AppState.clear()
        self.screen = PosScreen(on_navigate=lambda _s: None, on_logout=lambda: None)

    def tearDown(self):
        AppState.clear()

    @staticmethod
    def _producto(id_producto=1, nombre="Mango", precio=28.0):
        return {"id_producto": id_producto, "nombre": nombre,
                "categoria": "Frutas", "precio": precio, "costo": 14.0,
                "unidad": "kg"}

    def test_sin_base_muestra_aviso_y_no_cobra(self):
        self.assertFalse(self.screen.db_ok)
        self.assertFalse(self.screen.offline_banner.isHidden())
        self.assertEqual(self.screen.product_table.rowCount(), 0)
        self.assertFalse(self.screen.cobrar_btn.isEnabled())

    def test_carrito_suma_cantidades_y_total(self):
        mango = self._producto(1, "Mango", 28.0)
        jitomate = self._producto(2, "Jitomate", 16.0)
        self.screen._add_product(mango)
        self.screen._add_product(mango)
        self.screen._add_product(jitomate)
        self.assertEqual(self.screen.cart[1]["cantidad"], 2)
        self.assertEqual(self.screen.cart[2]["cantidad"], 1)
        self.assertEqual(self.screen.total_label.text(), "$72.00")

        # el ultimo producto agregado queda seleccionado
        self.screen._change_qty(1)
        self.assertEqual(self.screen.cart[2]["cantidad"], 2)
        self.assertEqual(self.screen.total_label.text(), "$88.00")

        self.screen._change_qty(-1)
        self.assertEqual(self.screen.cart[2]["cantidad"], 1)
        self.screen._remove_selected()
        self.assertNotIn(2, self.screen.cart)
        self.assertEqual(self.screen.total_label.text(), "$56.00")

    def test_bajar_a_cero_quita_el_renglon(self):
        self.screen._add_product(self._producto(1, "Mango", 28.0))
        self.screen._change_qty(-1)
        self.assertEqual(self.screen.cart, {})
        self.assertEqual(self.screen.total_label.text(), "$0.00")
        self.assertFalse(self.screen.cobrar_btn.isEnabled())

    def test_medio_kilo_y_cantidad_editable(self):
        self.screen._add_product(self._producto(1, "Mango", 28.0))
        self.screen._set_qty(1, 0.5)
        self.assertEqual(self.screen.cart[1]["cantidad"], 0.5)
        self.assertEqual(self.screen.total_label.text(), "$14.00")
        self.assertEqual(self.screen.qty_input.decimals(), 3)
        self.assertEqual(self.screen.qty_input.value(), 0.5)

        self.screen._change_qty(0.5)
        self.assertEqual(self.screen.cart[1]["cantidad"], 1.0)
        self.assertEqual(self.screen.total_label.text(), "$28.00")

    def test_piezas_solo_aceptan_enteros(self):
        producto = self._producto(2, "Piña", 25.0)
        producto["solo_enteros"] = True
        self.screen._add_product(producto)
        self.screen._set_qty(2, 1.6)
        self.assertEqual(self.screen.cart[2]["cantidad"], 2.0)
        self.assertEqual(self.screen.qty_input.decimals(), 0)
        self.assertEqual(self.screen.qty_input.singleStep(), 1.0)

    def test_busqueda_filtra_en_memoria_sin_acentos(self):
        # el catalogo se carga una vez; la busqueda solo recorta la lista
        self.screen.db_ok = True
        self.screen.all_products = [
            self._producto(1, "Mango"),
            self._producto(2, "Piña"),
            self._producto(3, "Jitomate"),
        ]
        self.screen.search.setText("pina")
        self.screen._refresh_products()
        self.assertEqual([p["nombre"] for p in self.screen.products], ["Piña"])
        self.assertEqual(self.screen.product_table.rowCount(), 1)

        self.screen.search.setText("tom")
        self.screen._refresh_products()
        self.assertEqual([p["nombre"] for p in self.screen.products], ["Jitomate"])


if __name__ == "__main__":
    unittest.main()
