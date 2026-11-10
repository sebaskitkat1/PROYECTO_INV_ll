#!/usr/bin/env python3
"""
Cosecha — Sistema de Analisis de Datos (version de escritorio)

Punto de entrada de la aplicacion. Ejecutar con:

    python main.py

Ver README.md para instrucciones de instalacion de dependencias.
"""
import logging
import sys

from PySide6.QtWidgets import QApplication

from app.logging_setup import configurar_logging, instalar_excepthook
from app.main_window import MainWindow
from app.styles import GLOBAL_STYLESHEET


def main() -> int:
    ruta_log = configurar_logging()
    instalar_excepthook()
    logger = logging.getLogger("cosecha")
    logger.info("Inicio de Cosecha%s",
                f" · log en {ruta_log}" if ruta_log else " · sin archivo de log")

    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLESHEET)
    app.setApplicationName("Cosecha")

    window = MainWindow()
    window.show()

    codigo = app.exec()
    logger.info("Fin de Cosecha (codigo %s)", codigo)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
