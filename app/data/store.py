"""Datos compartidos en memoria. Vive mientras la app esta abierta.

Asi lo que editas en inventario no se pierde al cambiar de pantalla.
Cuando llegue la base, estas funciones leen de ahi en vez del mock.
"""
from __future__ import annotations

from app.data import mock_data

_inventory: list[dict] | None = None


def get_inventory() -> list[dict]:
    global _inventory
    if _inventory is None:
        _inventory = [dict(r) for r in mock_data.get_inventory()]
    return _inventory


def reset_inventory() -> list[dict]:
    global _inventory
    _inventory = [dict(r) for r in mock_data.get_inventory()]
    return _inventory
