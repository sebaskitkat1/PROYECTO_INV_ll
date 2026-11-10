"""Registro local de eventos y errores de la aplicacion.

El archivo vive en `%LOCALAPPDATA%\\Cosecha\\cosecha.log` (o `~/.cosecha` fuera
de Windows), nunca dentro del repositorio. No se registran credenciales.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def log_path() -> Path:
    base = os.getenv("LOCALAPPDATA")
    carpeta = Path(base) / "Cosecha" if base else Path.home() / ".cosecha"
    return carpeta / "cosecha.log"


def configurar_logging() -> Path | None:
    """Agrega un handler de archivo al logger raiz. Devuelve la ruta usada."""
    ruta = log_path()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(ruta, encoding="utf-8")
    except OSError:
        return None
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        root.addHandler(handler)
    return ruta


def instalar_excepthook() -> None:
    """Registra los errores no controlados antes de mostrarlos en consola."""
    logger = logging.getLogger("cosecha")

    def _hook(tipo, valor, tb) -> None:
        logger.error("Error no controlado", exc_info=(tipo, valor, tb))
        sys.__excepthook__(tipo, valor, tb)

    sys.excepthook = _hook
