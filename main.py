#!/usr/bin/env python3
"""
CaféData — Sistema de Análisis de Datos (versión de escritorio)

Punto de entrada de la aplicación. Ejecutar con:

    python main.py

Ver README.md para instrucciones de instalación de dependencias.
"""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.styles import GLOBAL_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)
    app.setApplicationName("CaféData")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
