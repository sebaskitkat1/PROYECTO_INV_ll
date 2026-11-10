"""Carga de datos en segundo plano para no congelar la interfaz.

Las pantallas construyen su parte visual en el hilo de UI y piden los datos
a la base con `run_async`. El resultado vuelve por una senal al hilo
principal. En modo ejemplo (`CAFE_DATOS=mock`) o sin MySQL se usa el mismo
camino sincrono de siempre para que las pruebas y el arranque sean
deterministas.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable

from PySide6.QtCore import QCoreApplication, QObject, QRunnable, QThreadPool, Signal

from app.data import db

logger = logging.getLogger("cosecha.async")


class _Signals(QObject):
    done = Signal(object)
    error = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any], signals: _Signals) -> None:
        super().__init__()
        self._fn = fn
        self._signals = signals

    def run(self) -> None:
        try:
            resultado = self._fn()
        except Exception as exc:  # DBError, red, etc.
            logger.warning("Carga en segundo plano fallo: %s", exc)
            self._signals.error.emit(str(exc))
        else:
            self._signals.done.emit(resultado)
        finally:
            self._signals.deleteLater()


def async_disponible() -> bool:
    """True si hay MySQL real; en modo ejemplo se mantiene sincrono."""
    if os.getenv("CAFE_DATOS", "").lower() == "mock":
        return False
    try:
        return db.available()
    except Exception:
        return False


def run_async(owner: QObject, fn: Callable[[], Any],
              on_done: Callable[[Any], None],
              on_error: Callable[[str], None] | None = None) -> None:
    """Ejecuta `fn` en el pool y entrega el resultado en el hilo de UI."""
    app = QCoreApplication.instance()
    signals = _Signals(app if app is not None else owner)
    signals.done.connect(on_done)
    if on_error is not None:
        signals.error.connect(on_error)
    QThreadPool.globalInstance().start(_Task(fn, signals))
