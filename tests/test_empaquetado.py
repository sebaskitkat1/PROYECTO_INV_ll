"""Empaquetado y CI: spec, pin de matplotlib, lock, matriz y Dependabot."""
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class TestEmpaquetado(unittest.TestCase):
    def test_spec_sin_upx_y_sin_herramientas_de_desarrollo(self):
        texto = (RAIZ / "cosecha.spec").read_text(encoding="utf-8")
        self.assertNotIn("upx=True", texto)
        self.assertEqual(texto.count("upx=False"), 2)
        self.assertRegex(texto, r"excludes\s*=\s*\[[^\]]*tkinter")
        # numpy/pyparsing importan unittest: excluirlo rompe el arranque
        self.assertNotIn('"unittest"', texto)
        self.assertIn('"mysql.connector"', texto)
        self.assertIn('"bcrypt"', texto)

    def test_matplotlib_no_salta_a_311(self):
        texto = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
        linea = next(linea for linea in texto.splitlines()
                     if linea.startswith("matplotlib"))
        self.assertIn("<3.11", linea)

    def test_lock_congela_versiones_y_respeta_el_pin(self):
        lineas = (RAIZ / "requirements.lock").read_text(
            encoding="utf-8").splitlines()
        paquetes = [linea for linea in lineas
                    if linea.strip() and not linea.startswith("#")]
        self.assertTrue(paquetes)
        for linea in paquetes:
            self.assertIn("==", linea, linea)
        matplotlib = next(linea for linea in paquetes
                          if linea.lower().startswith("matplotlib=="))
        self.assertRegex(matplotlib, r"^matplotlib==3\.10\.")

    def test_ci_prueba_python_310_y_312(self):
        texto = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8")
        self.assertIn('"3.10"', texto)
        self.assertIn('"3.12"', texto)
        self.assertIn("matrix.python-version", texto)

    def test_dependabot_vigila_pip_y_actions(self):
        texto = (RAIZ / ".github" / "dependabot.yml").read_text(
            encoding="utf-8")
        self.assertIn('package-ecosystem: "pip"', texto)
        self.assertIn('package-ecosystem: "github-actions"', texto)

    def test_instalador_publica_cosecha(self):
        texto = (RAIZ / "installer" / "cosecha.iss").read_text(
            encoding="utf-8")
        self.assertIn("AppPublisher=Cosecha", texto)
        self.assertNotIn("AppPublisher=CafeData", texto)

    def test_readme_empieza_con_el_nombre_visible(self):
        texto = (RAIZ / "README.md").read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("# Cosecha"))
        self.assertIn("# 164 pruebas", texto)


if __name__ == "__main__":
    unittest.main()
