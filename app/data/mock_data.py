"""
Datos de ejemplo usados mientras se conecta la base.

Reproduce los datos del prototipo web para que las pantallas
se vean bien desde el inicio. Cuando este la base, cambia estas
funciones por consultas que devuelvan lo mismo (listas de dicts).
"""

from __future__ import annotations


def get_sales_last_7_days() -> list[dict]:
    return [
        {"day": "Lun", "ventas": 4200},
        {"day": "Mar", "ventas": 4650},
        {"day": "Mié", "ventas": 3980},
        {"day": "Jue", "ventas": 5320},
        {"day": "Vie", "ventas": 6100},
        {"day": "Sáb", "ventas": 6850},
        {"day": "Dom", "ventas": 4720},
    ]


def get_sales_detail() -> list[dict]:
    return [
        {"nombre": "Mango", "cantidad": 420, "ingresos": 11760.0, "margen": 47, "tendencia": "up"},
        {"nombre": "Manzana Roja", "cantidad": 640, "ingresos": 11520.0, "margen": 45, "tendencia": "up"},
        {"nombre": "Uva", "cantidad": 340, "ingresos": 10880.0, "margen": 36, "tendencia": "up"},
        {"nombre": "Naranja", "cantidad": 750, "ingresos": 10500.0, "margen": 58, "tendencia": "down"},
        {"nombre": "Fresa", "cantidad": 290, "ingresos": 10150.0, "margen": 33, "tendencia": "down"},
        {"nombre": "Plátano", "cantidad": 820, "ingresos": 9840.0, "margen": 52, "tendencia": "up"},
        {"nombre": "Jitomate", "cantidad": 480, "ingresos": 7680.0, "margen": 55, "tendencia": "up"},
        {"nombre": "Jugo de Naranja", "cantidad": 310, "ingresos": 6200.0, "margen": 61, "tendencia": "down"},
        {"nombre": "Sandía", "cantidad": 95, "ingresos": 5700.0, "margen": 44, "tendencia": "up"},
        {"nombre": "Piña", "cantidad": 210, "ingresos": 5250.0, "margen": 49, "tendencia": "down"},
    ]


def get_inventory() -> list[dict]:
    return [
        {"nombre": "Manzana (kg)", "unidad": "kg", "stockActual": 25, "stockMinimo": 20, "diasAgotar": 12, "estado": "optimo"},
        {"nombre": "Plátano (kg)", "unidad": "kg", "stockActual": 30, "stockMinimo": 22, "diasAgotar": 8, "estado": "optimo"},
        {"nombre": "Naranja (kg)", "unidad": "kg", "stockActual": 18, "stockMinimo": 20, "diasAgotar": 3, "estado": "critico"},
        {"nombre": "Mango (kg)", "unidad": "kg", "stockActual": 12, "stockMinimo": 10, "diasAgotar": 5, "estado": "advertencia"},
        {"nombre": "Fresa (kg)", "unidad": "kg", "stockActual": 6, "stockMinimo": 8, "diasAgotar": 2, "estado": "critico"},
        {"nombre": "Uva (kg)", "unidad": "kg", "stockActual": 9, "stockMinimo": 8, "diasAgotar": 4, "estado": "advertencia"},
        {"nombre": "Piña (pzas)", "unidad": "pzas", "stockActual": 40, "stockMinimo": 30, "diasAgotar": 9, "estado": "optimo"},
        {"nombre": "Sandía (pzas)", "unidad": "pzas", "stockActual": 15, "stockMinimo": 12, "diasAgotar": 10, "estado": "optimo"},
        {"nombre": "Jitomate (kg)", "unidad": "kg", "stockActual": 14, "stockMinimo": 16, "diasAgotar": 3, "estado": "critico"},
        {"nombre": "Jugo natural (L)", "unidad": "L", "stockActual": 20, "stockMinimo": 18, "diasAgotar": 6, "estado": "advertencia"},
    ]


def get_rotation_data() -> list[dict]:
    return [
        {"nombre": "Manzana", "dias": 1.4},
        {"nombre": "Plátano", "dias": 0.9},
        {"nombre": "Piña", "dias": 2.3},
        {"nombre": "Naranja", "dias": 3.1},
        {"nombre": "Mango", "dias": 4.2},
    ]


def get_pareto_data() -> list[dict]:
    return [
        {"nombre": "Mango", "ingresos": 11760},
        {"nombre": "Manzana", "ingresos": 11520},
        {"nombre": "Uva", "ingresos": 10880},
        {"nombre": "Naranja", "ingresos": 10500},
        {"nombre": "Fresa", "ingresos": 10150},
    ]


def get_prediction_data() -> list[dict]:
    # serie ordenada cronologicamente: 6 dias historicos + Hoy (pivote)
    # + 6 dias de pronostico. Sin espacios/duplicados en etiquetas.
    return [
        {"dia": "25 Sep", "historico": 5100, "prediccion": None},
        {"dia": "27 Sep", "historico": 4650, "prediccion": None},
        {"dia": "29 Sep", "historico": 5300, "prediccion": None},
        {"dia": "01 Oct", "historico": 5600, "prediccion": None},
        {"dia": "03 Oct", "historico": 5200, "prediccion": None},
        {"dia": "05 Oct", "historico": 5850, "prediccion": None},
        {"dia": "Hoy", "historico": 6100, "prediccion": 6100},
        {"dia": "08 Oct", "historico": None, "prediccion": 6180},
        {"dia": "10 Oct", "historico": None, "prediccion": 6420},
        {"dia": "12 Oct", "historico": None, "prediccion": 6310},
        {"dia": "15 Oct", "historico": None, "prediccion": 6680},
        {"dia": "18 Oct", "historico": None, "prediccion": 6840},
        {"dia": "25 Oct", "historico": None, "prediccion": 6590},
    ]
