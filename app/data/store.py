"""Datos compartidos en memoria. Vive mientras la app esta abierta.

Primero intenta la base (repository); sin conexion usa el ejemplo.
Cuando llegue la base definitiva, aqui solo queda el camino de la base.
"""
from __future__ import annotations

from app.data import analytics, mock_data, repository
from app.data.db import DBError

_inventory: list[dict] | None = None


def _desde_base() -> list[dict] | None:
    try:
        return repository.inventory_rows()
    except DBError:
        return None


def get_inventory() -> list[dict]:
    global _inventory
    if _inventory is None:
        _inventory = _desde_base()
        if _inventory is None:
            _inventory = []
            for r in mock_data.get_inventory():
                d = dict(r)
                d["consumoDiario"] = analytics.daily_use(d)
                _inventory.append(d)
    return _inventory


def reset_inventory() -> list[dict]:
    global _inventory
    _inventory = None
    return get_inventory()
