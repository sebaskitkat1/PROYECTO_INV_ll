"""Umbrales del sistema: valores por defecto y lectura de parametros_sistema."""
from __future__ import annotations

DEFAULTS: dict[str, float] = {
    "umbral_advertencia": 1.25,
    "objetivo_reorden": 2.00,
    "alerta_caducidad_dias": 7.0,
    "dias_alerta_agotar": 5.0,
    "abc_corte_a": 80.0,
    "abc_corte_b": 95.0,
    # Fase 2: consumo, lead time y stock de seguridad.
    "ventana_consumo_dias": 30.0,
    "lead_time_default": 2.0,
    "dias_seguridad": 1.0,
    "dias_cobertura": 7.0,
    # Fase 5: clasificacion XYZ y stock de seguridad estadistico.
    "xyz_ventana_dias": 90.0,
    "xyz_min_dias": 7.0,
    "xyz_corte_x": 0.5,
    "xyz_corte_y": 1.0,
    "z_xyz_x": 1.28,
    "z_xyz_y": 1.65,
    "z_xyz_z": 2.33,
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
