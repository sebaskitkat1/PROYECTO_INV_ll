"""
Datos de ejemplo usados mientras se conecta la base.

Reproduce los datos del prototipo web para que las pantallas
se vean bien desde el inicio. Cuando este la base, cambia estas
funciones por consultas que devuelvan lo mismo (listas de dicts).
"""

from __future__ import annotations


def get_sales_last_7_days() -> list[dict]:
    return [
        {"day": "Lun", "ventas": 3850},
        {"day": "Mar", "ventas": 4120},
        {"day": "Mié", "ventas": 3620},
        {"day": "Jue", "ventas": 4890},
        {"day": "Vie", "ventas": 5640},
        {"day": "Sáb", "ventas": 6210},
        {"day": "Dom", "ventas": 4380},
    ]


def get_sales_detail() -> list[dict]:
    return [
        {"nombre": "Café Americano", "cantidad": 842, "ingresos": 8420.0, "margen": 72, "tendencia": "up"},
        {"nombre": "Capuchino", "cantidad": 490, "ingresos": 7350.0, "margen": 68, "tendencia": "up"},
        {"nombre": "Torta de Chocolate", "cantidad": 259, "ingresos": 5180.0, "margen": 61, "tendencia": "down"},
        {"nombre": "Sandwich Club", "cantidad": 328, "ingresos": 4920.0, "margen": 54, "tendencia": "up"},
        {"nombre": "Agua Mineral", "cantidad": 734, "ingresos": 3670.0, "margen": 82, "tendencia": "down"},
        {"nombre": "Jugo Natural", "cantidad": 218, "ingresos": 3270.0, "margen": 58, "tendencia": "up"},
        {"nombre": "Croissant", "cantidad": 387, "ingresos": 2709.0, "margen": 63, "tendencia": "up"},
        {"nombre": "Té Negro", "cantidad": 312, "ingresos": 2184.0, "margen": 79, "tendencia": "down"},
        {"nombre": "Pan Dulce", "cantidad": 521, "ingresos": 1563.0, "margen": 55, "tendencia": "up"},
        {"nombre": "Frappé", "cantidad": 143, "ingresos": 1430.0, "margen": 49, "tendencia": "down"},
    ]


def get_inventory() -> list[dict]:
    return [
        {"nombre": "Café en Grano (kg)", "unidad": "kg", "stockActual": 12, "stockMinimo": 8, "diasAgotar": 18, "estado": "optimo"},
        {"nombre": "Leche (L)", "unidad": "L", "stockActual": 45, "stockMinimo": 30, "diasAgotar": 9, "estado": "optimo"},
        {"nombre": "Harina (kg)", "unidad": "kg", "stockActual": 7, "stockMinimo": 10, "diasAgotar": 3, "estado": "critico"},
        {"nombre": "Azúcar (kg)", "unidad": "kg", "stockActual": 18, "stockMinimo": 15, "diasAgotar": 12, "estado": "advertencia"},
        {"nombre": "Chocolate (kg)", "unidad": "kg", "stockActual": 3, "stockMinimo": 5, "diasAgotar": 4, "estado": "critico"},
        {"nombre": "Jamón (kg)", "unidad": "kg", "stockActual": 4, "stockMinimo": 6, "diasAgotar": 2, "estado": "critico"},
        {"nombre": "Queso (kg)", "unidad": "kg", "stockActual": 9, "stockMinimo": 8, "diasAgotar": 7, "estado": "advertencia"},
        {"nombre": "Pan de Caja (pzas)", "unidad": "pzas", "stockActual": 48, "stockMinimo": 24, "diasAgotar": 8, "estado": "optimo"},
        {"nombre": "Fruta (kg)", "unidad": "kg", "stockActual": 6, "stockMinimo": 10, "diasAgotar": 3, "estado": "critico"},
        {"nombre": "Agua (bidones)", "unidad": "bidones", "stockActual": 22, "stockMinimo": 20, "diasAgotar": 11, "estado": "advertencia"},
    ]


def get_rotation_data() -> list[dict]:
    return [
        {"nombre": "Café en Grano", "dias": 1.2},
        {"nombre": "Leche", "dias": 0.8},
        {"nombre": "Pan de Caja", "dias": 2.1},
        {"nombre": "Azúcar", "dias": 3.4},
        {"nombre": "Harina", "dias": 4.8},
    ]


def get_pareto_data() -> list[dict]:
    return [
        {"nombre": "Café Americano", "ingresos": 8420},
        {"nombre": "Capuchino", "ingresos": 7350},
        {"nombre": "Torta Choc.", "ingresos": 5180},
        {"nombre": "Sandwich", "ingresos": 4920},
        {"nombre": "Agua", "ingresos": 3670},
    ]


def get_prediction_data() -> list[dict]:
    # serie ordenada cronologicamente: 6 dias historicos + Hoy (pivote)
    # + 6 dias de pronostico. Sin espacios/duplicados en etiquetas.
    return [
        {"dia": "25 Sep", "historico": 4600, "prediccion": None},
        {"dia": "27 Sep", "historico": 4200, "prediccion": None},
        {"dia": "29 Sep", "historico": 4850, "prediccion": None},
        {"dia": "01 Oct", "historico": 5100, "prediccion": None},
        {"dia": "03 Oct", "historico": 4700, "prediccion": None},
        {"dia": "05 Oct", "historico": 5300, "prediccion": None},
        {"dia": "Hoy", "historico": 5640, "prediccion": 5640},
        {"dia": "08 Oct", "historico": None, "prediccion": 5720},
        {"dia": "10 Oct", "historico": None, "prediccion": 6100},
        {"dia": "12 Oct", "historico": None, "prediccion": 5890},
        {"dia": "15 Oct", "historico": None, "prediccion": 6340},
        {"dia": "18 Oct", "historico": None, "prediccion": 6580},
        {"dia": "25 Oct", "historico": None, "prediccion": 6210},
    ]
