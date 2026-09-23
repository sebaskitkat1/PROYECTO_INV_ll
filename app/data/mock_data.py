"""
Datos de ejemplo (mock data) usados mientras no se ha cargado un CSV real.

Esta estructura reproduce, con nombres de variables equivalentes, los
datos de ejemplo del prototipo web original (src/data/mockData.ts) para
que las pantallas y gráficas tengan el mismo aspecto desde el inicio.

Cuando integres tus propias fuentes de datos (CSV, base de datos, API),
lo más sencillo es reemplazar estas funciones por otras que devuelvan la
misma forma de datos (listas de dicts / tuplas), sin tocar las pantallas.
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


def get_top5_products() -> list[dict]:
    return [
        {"product": "Café Americano", "ingresos": 8420},
        {"product": "Capuchino", "ingresos": 7350},
        {"product": "Torta de Chocolate", "ingresos": 5180},
        {"product": "Sandwich Club", "ingresos": 4920},
        {"product": "Agua Mineral", "ingresos": 3670},
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
        {"nombre": "Café en Grano (kg)", "stockActual": 12, "stockMinimo": 8, "diasAgotar": 18, "estado": "optimo"},
        {"nombre": "Leche (L)", "stockActual": 45, "stockMinimo": 30, "diasAgotar": 9, "estado": "optimo"},
        {"nombre": "Harina (kg)", "stockActual": 7, "stockMinimo": 10, "diasAgotar": 3, "estado": "critico"},
        {"nombre": "Azúcar (kg)", "stockActual": 18, "stockMinimo": 15, "diasAgotar": 12, "estado": "optimo"},
        {"nombre": "Chocolate (kg)", "stockActual": 3, "stockMinimo": 5, "diasAgotar": 4, "estado": "critico"},
        {"nombre": "Jamón (kg)", "stockActual": 4, "stockMinimo": 6, "diasAgotar": 2, "estado": "critico"},
        {"nombre": "Queso (kg)", "stockActual": 9, "stockMinimo": 8, "diasAgotar": 7, "estado": "advertencia"},
        {"nombre": "Pan de Caja (pzas)", "stockActual": 48, "stockMinimo": 24, "diasAgotar": 8, "estado": "optimo"},
        {"nombre": "Fruta (kg)", "stockActual": 6, "stockMinimo": 10, "diasAgotar": 3, "estado": "critico"},
        {"nombre": "Agua (bidones)", "stockActual": 22, "stockMinimo": 20, "diasAgotar": 11, "estado": "advertencia"},
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
    return [
        {"dia": "01 Oct", "historico": 4200, "prediccion": None},
        {"dia": "05 Oct", "historico": 4850, "prediccion": None},
        {"dia": "10 Oct", "historico": 5100, "prediccion": None},
        {"dia": "15 Oct", "historico": 4700, "prediccion": None},
        {"dia": "20 Oct", "historico": 5300, "prediccion": None},
        {"dia": "25 Sep", "historico": 4600, "prediccion": None},
        {"dia": "Hoy", "historico": 5640, "prediccion": 5640},
        {"dia": "30 Sep", "historico": None, "prediccion": 5720},
        {"dia": "05 Oct ", "historico": None, "prediccion": 6100},
        {"dia": "10 Oct ", "historico": None, "prediccion": 5890},
        {"dia": "15 Oct ", "historico": None, "prediccion": 6340},
        {"dia": "20 Oct ", "historico": None, "prediccion": 6580},
        {"dia": "25 Oct", "historico": None, "prediccion": 6210},
    ]


def get_top_predicted() -> list[dict]:
    return [
        {"nombre": "Café Americano", "actual": 8420, "predicho": 9650, "crecimiento": 14.6},
        {"nombre": "Capuchino", "actual": 7350, "predicho": 8120, "crecimiento": 10.5},
        {"nombre": "Torta de Chocolate", "actual": 5180, "predicho": 5480, "crecimiento": 5.8},
        {"nombre": "Sandwich Club", "actual": 4920, "predicho": 5340, "crecimiento": 8.5},
        {"nombre": "Jugo Natural", "actual": 3270, "predicho": 3920, "crecimiento": 19.9},
    ]


def get_kpis() -> dict:
    """KPIs mostrados en la tarjeta resumen del dashboard."""
    return {
        "ventas_hoy": {"valor": "$5,640", "delta": "8%", "positivo": True},
        "ticket_promedio": {"valor": "$187", "delta": "3%", "positivo": True},
        "productos_vendidos": {"valor": "302", "delta": "5%", "positivo": True},
        "stock_en_riesgo": {"valor": "4", "delta": None, "positivo": None},
    }
