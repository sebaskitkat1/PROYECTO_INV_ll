"""Datos compartidos en memoria. Vive mientras la app esta abierta.

Primero intenta la base (repository); sin conexion usa el ejemplo.
Cuando llegue la base definitiva, aqui solo queda el camino de la base.
"""
from __future__ import annotations

from app.data import analytics, mock_data, params, repository
from app.data.db import DBError

_inventory: list[dict] | None = None


def _desde_base() -> list[dict] | None:
    try:
        return repository.inventory_rows()
    except DBError:
        return None


def _inventario_ejemplo() -> list[dict]:
    """Ejemplo con la misma forma que la vista: XYZ, colchon y punto."""
    defaults = params.defaults()
    series = mock_data.get_demand_series()
    filas = []
    for r in mock_data.get_inventory():
        d = dict(r)
        d["consumoDiario"] = analytics.daily_use(d)
        base = str(d.get("nombre", "")).split(" (")[0]
        serie = series.get(base)
        if serie:
            info = analytics.xyz_class(serie)
            clase = info.get("clase")
            d["xyzClase"] = clase if clase in ("X", "Y", "Z") else None
            d["xyzCv"] = info.get("cv")
            d["xyzSigma"] = info.get("desv")
            d["xyzMedia"] = info.get("media")
            d["xyzDias"] = sum(1 for v in serie if float(v) > 0)
            lead = d.get("leadTimeDias")
            if lead is None:
                lead = defaults["lead_time_default"]
                d["leadTimeDias"] = lead
            d["stockSeguridad"] = round(analytics.xyz_safety_stock(
                d["xyzSigma"], lead, d["xyzClase"],
                consumo_diario=d["consumoDiario"],
                dias_seguridad=defaults["dias_seguridad"],
                dias_con_datos=d["xyzDias"],
                min_dias=int(defaults["xyz_min_dias"])), 3)
            d["puntoReorden"] = round(analytics.reorder_point(
                d, lead, defaults["dias_seguridad"],
                stock_seguridad=d["stockSeguridad"]), 3)
        filas.append(d)
    return filas


def get_inventory() -> list[dict]:
    global _inventory
    if _inventory is None:
        _inventory = _desde_base()
        if _inventory is None:
            _inventory = _inventario_ejemplo()
    return _inventory


def invalidate_inventory() -> None:
    """Marca el inventario como viejo; la proxima pantalla lo recarga."""
    global _inventory
    _inventory = None


def reset_inventory() -> list[dict]:
    invalidate_inventory()
    return get_inventory()
