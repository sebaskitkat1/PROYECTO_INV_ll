"""Guarda tablas en CSV que Excel abre bien: utf-8-sig, sin formulas vivas."""
from __future__ import annotations

import csv


class ExportError(Exception):
    pass


def limpiar_valor(valor):
    # neutraliza inyeccion de formulas (=, +, -, @ al inicio)
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@"):
        return "'" + valor
    return valor


def guardar_csv(ruta: str, columnas: list, filas: list) -> int:
    """Escribe filas (dicts con las claves de columnas, o listas). Devuelve n."""
    try:
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(columnas)
            n = 0
            for fila in filas:
                if isinstance(fila, dict):
                    w.writerow([limpiar_valor(fila.get(c, "")) for c in columnas])
                else:
                    w.writerow([limpiar_valor(v) for v in fila])
                n += 1
            return n
    except OSError as e:
        raise ExportError(f"no se pudo escribir el archivo: {e.strerror or e}") from e
