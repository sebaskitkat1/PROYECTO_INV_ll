"""Umbrales del sistema: valores por defecto y lectura de parametros_sistema."""
from __future__ import annotations

DEFAULTS: dict[str, float] = {
    "umbral_advertencia": 1.25,
    "objetivo_reorden": 2.00,
    "alerta_caducidad_dias": 7.0,
    "dias_alerta_agotar": 5.0,
    "abc_corte_a": 80.0,
    "abc_corte_b": 95.0,
}


def defaults() -> dict[str, float]:
    return dict(DEFAULTS)


def parse(rows: list[dict]) -> dict[str, float]:
    out = defaults()
    for row in rows:
        clave = str(row.get("clave") or "")
        if clave not in out:
            continue
        valor = row.get("valor")
        if valor is None:
            continue
        try:
            out[clave] = float(valor)
        except (TypeError, ValueError):
            continue
    return out
