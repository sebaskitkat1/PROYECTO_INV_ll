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


def get_purchase_orders() -> list[dict]:
    return [
        {"id_orden": 1048, "proveedor": "Central de Abastos de Torreón",
         "fecha": "2026-10-19 08:40", "estado": "borrador", "total": 723.70},
        {"id_orden": 1047, "proveedor": "Huerta Los Nogales",
         "fecha": "2026-10-18 07:55", "estado": "enviada", "total": 300.00},
        {"id_orden": 1046, "proveedor": "Central de Abastos de Torreón",
         "fecha": "2026-10-16 09:10", "estado": "recibida", "total": 498.30},
    ]


def get_purchase_order_detail(id_orden: int | None = None) -> list[dict]:
    detalles = {
        1048: [
            {"nombre": "Fresa", "unidad": "kg", "cantidad": 10, "recibido": None,
             "precio": 23.45, "importe": 234.50},
            {"nombre": "Naranja", "unidad": "kg", "cantidad": 30, "recibido": None,
             "precio": 5.88, "importe": 176.40},
            {"nombre": "Jitomate", "unidad": "kg", "cantidad": 15, "recibido": None,
             "precio": 7.20, "importe": 108.00},
            {"nombre": "Uva", "unidad": "kg", "cantidad": 10, "recibido": None,
             "precio": 20.48, "importe": 204.80},
        ],
        1047: [
            {"nombre": "Papaya", "unidad": "kg", "cantidad": 12, "recibido": None,
             "precio": 11.00, "importe": 132.00},
            {"nombre": "Sandía", "unidad": "pzas", "cantidad": 5, "recibido": None,
             "precio": 33.60, "importe": 168.00},
        ],
        1046: [
            {"nombre": "Manzana", "unidad": "kg", "cantidad": 20, "recibido": 20,
             "precio": 9.90, "importe": 198.00},
            {"nombre": "Plátano", "unidad": "kg", "cantidad": 30, "recibido": 30,
             "precio": 5.76, "importe": 172.80},
            {"nombre": "Piña", "unidad": "pzas", "cantidad": 10, "recibido": 10,
             "precio": 12.75, "importe": 127.50},
        ],
    }
    if id_orden is None:
        return [dict(fila) for filas in detalles.values() for fila in filas]
    return [dict(fila) for fila in detalles.get(int(id_orden), [])]


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
