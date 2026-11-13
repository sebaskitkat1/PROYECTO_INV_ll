"""Instalador: cada Source existe y todas las migraciones estan listadas."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INSTALADOR = RAIZ / "installer"
ISS = INSTALADOR / "cosecha.iss"


class TestInstalador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texto = ISS.read_text(encoding="utf-8")

    def test_sources_literales_existen(self):
        fuentes = re.findall(r'Source:\s*"([^"]+)"', self.texto)
        self.assertTrue(fuentes)
        for fuente in fuentes:
            if "*" in fuente:
                # dist\cosecha\* se genera al empaquetar; no vive en el repo.
                continue
            ruta = (INSTALADOR / fuente.replace("\\", "/")).resolve()
            self.assertTrue(ruta.exists(), f"Source inexistente: {fuente}")

    def test_env_example_se_distribuye(self):
        self.assertTrue((RAIZ / ".env.example").exists())
        self.assertIn(r'Source: "..\.env.example"', self.texto)

    def test_schema_y_usuario_app_se_distribuyen(self):
        self.assertIn(r'Source: "..\db\init_schema.sql"', self.texto)
        self.assertIn(r'Source: "..\db\crear_usuario_app.sql"', self.texto)
        self.assertNotIn(r'Source: "..\db\frutidata_schema.sql"', self.texto)
        self.assertNotIn(r'Source: "..\db\dev_reset.sql"', self.texto)

    def test_ningun_archivo_distribuido_borra_la_base(self):
        fuentes = re.findall(r'Source:\s*"([^"]+)"', self.texto)
        for fuente in fuentes:
            if "*" in fuente:
                continue
            ruta = (INSTALADOR / fuente.replace("\\", "/")).resolve()
            texto = ruta.read_text(encoding="utf-8").upper()
            self.assertNotIn("DROP DATABASE", texto,
                             f"archivo distribuido borra la base: {fuente}")

    def test_migraciones_registran_su_version(self):
        migraciones = list((RAIZ / "db").glob("migrate_*.sql"))
        self.assertTrue(migraciones)
        for ruta in migraciones:
            texto = ruta.read_text(encoding="utf-8")
            self.assertIn("schema_migrations", texto, ruta.name)
            self.assertIn(f"'{ruta.stem}'", texto, ruta.name)

    def test_init_schema_crea_schema_migrations(self):
        texto = (RAIZ / "db" / "init_schema.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS schema_migrations", texto)
        self.assertIn("CREATE DATABASE IF NOT EXISTS frutidata", texto)
        self.assertNotIn("DROP DATABASE", texto.upper())

    def test_todas_las_migraciones_estan_listadas(self):
        migraciones = sorted(p.name for p in (RAIZ / "db").glob("migrate_*.sql"))
        self.assertTrue(migraciones)
        for nombre in migraciones:
            self.assertIn(nombre, self.texto, f"migracion sin instalar: {nombre}")

    def test_orden_de_migraciones_igual_al_readme(self):
        readme = (RAIZ / "db" / "README_datos.md").read_text(encoding="utf-8")
        esperadas = re.findall(r"db/(migrate_[a-z0-9_]+\.sql)", readme)
        en_iss = re.findall(r'Source:\s*"\.\.\\db\\(migrate_[a-z0-9_]+\.sql)"',
                            self.texto)
        self.assertEqual(en_iss, esperadas)


if __name__ == "__main__":
    unittest.main()
