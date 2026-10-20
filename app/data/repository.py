"""Puerta a los datos reales: vistas y procedimientos de la base.

Cada funcion devuelve la misma forma que usaban los dicts del mock,
asi las pantallas no cambian de logica. Si no hay base (o CAFE_DATOS=mock),
lanza DBError y la pantalla usa el ejemplo.
"""
from __future__ import annotations

import datetime
import os
import socket

from app.data import analytics, db, params, roles
from app.data.db import DBError

DIAS_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


class AuthError(Exception):
    """Credenciales invalidas (mensaje generico a proposito)."""


def _forzar_mock() -> bool:
    return os.getenv("CAFE_DATOS", "").lower() == "mock"


def _hay_base() -> bool:
    if _forzar_mock():
        raise DBError("modo ejemplo")
    if not db.available():
        raise DBError("sin conexion a la base")
    return True


def activa() -> bool:
    try:
        return _hay_base()
    except DBError:
        return False


def etiqueta_fuente() -> str:
    return "base de datos" if activa() else "ejemplo"


_SUCURSAL: int | None = None


def sucursal_id() -> int:
    global _SUCURSAL
    if _SUCURSAL is None:
        filas = db.fetchall("SELECT id_sucursal FROM sucursales WHERE nombre = %s",
                            ("Sucursal Principal",))
        if filas:
            _SUCURSAL = int(filas[0]["id_sucursal"])
        else:
            _SUCURSAL = int(db.fetchall("SELECT MIN(id_sucursal) AS id FROM sucursales")[0]["id"])
    return _SUCURSAL


_PARAMS: dict[str, float] | None = None


def system_params() -> dict[str, float]:
    global _PARAMS
    if _PARAMS is not None:
        return dict(_PARAMS)
    try:
        _hay_base()
        filas = db.fetchall("SELECT clave, valor FROM parametros_sistema")
    except DBError:
        return params.defaults()
    _PARAMS = params.parse(filas)
    return dict(_PARAMS)


def reset_params_cache() -> None:
    global _PARAMS
    _PARAMS = None


def dia_corto(fecha: datetime.date) -> str:
    return DIAS_CORTO[fecha.weekday()]


def map_venta_row(r: dict) -> dict:
    return {"nombre": str(r["nombre"]),
            "categoria": str(r.get("categoria") or "Sin categoria"),
            "cantidad": int(r.get("cantidad") or 0),
            "ingresos": float(r.get("ingresos") or 0),
            "margen": float(r.get("margen_pct") or 0),
            "tendencia": str(r.get("tendencia") or "down")}


def map_inventario_row(r: dict) -> dict:
    dias = r.get("dias_agotar")
    consumo = r.get("consumo_diario")
    return {"id_ingrediente": int(r["id_ingrediente"]),
            "nombre": str(r["nombre"]),
            "unidad": str(r.get("unidad") or "kg"),
            "stockActual": float(r.get("stock_actual") or 0),
            "stockMinimo": float(r.get("stock_minimo") or 0),
            "diasAgotar": None if dias is None else float(dias),
            "estado": str(r.get("estado") or "optimo"),
            "consumoDiario": None if consumo is None else float(consumo)}


def sales_last_7_days() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT fecha, ventas FROM v_ventas_diarias WHERE id_sucursal = %s "
        "ORDER BY fecha DESC LIMIT 7", (sucursal_id(),))
    filas.sort(key=lambda r: r["fecha"])
    return [{"day": dia_corto(r["fecha"]), "ventas": float(r["ventas"] or 0)} for r in filas]


def sales_detail() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT nombre, categoria, cantidad, ingresos, margen_pct, tendencia "
        "FROM v_ventas_por_producto ORDER BY ingresos DESC")
    return [map_venta_row(r) for r in filas]


def inventory_rows() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT id_ingrediente, nombre, unidad, stock_actual, stock_minimo, "
        "consumo_diario, dias_agotar, estado FROM v_estado_inventario "
        "WHERE id_sucursal = %s", (sucursal_id(),))
    return [map_inventario_row(r) for r in filas]


def pareto_data() -> list[dict]:
    _hay_base()
    filas = db.fetchall("SELECT nombre, ingresos FROM v_pareto_abc")
    return [{"nombre": str(r["nombre"]), "ingresos": float(r["ingresos"] or 0)} for r in filas]


def sales_history(days: int = 90) -> list[tuple]:
    _hay_base()
    filas = db.fetchall(
        "SELECT fecha, ventas FROM v_ventas_diarias WHERE id_sucursal = %s ORDER BY fecha",
        (sucursal_id(),))
    return [(r["fecha"], float(r["ventas"] or 0)) for r in filas[-days:]]


def dashboard_kpis() -> dict:
    _hay_base()
    f = db.fetchall(
        "SELECT ventas_hoy, ventas_ayer, variacion_pct, ticket_promedio, "
        "unidades_hoy, stock_en_riesgo FROM v_kpi_dashboard WHERE id_sucursal = %s",
        (sucursal_id(),))[0]
    var = f.get("variacion_pct")
    var = None if var is None else float(var)
    return {
        "ventas_hoy": {"valor": analytics.fmt_money(float(f.get("ventas_hoy") or 0)),
                       "delta": f"{abs(var):.1f}%" if var is not None else None,
                       "positivo": (var or 0) >= 0},
        "ticket_promedio": {"valor": f"${float(f.get('ticket_promedio') or 0):,.2f}",
                            "delta": None, "positivo": True},
        "productos_vendidos": {"valor": f"{int(f.get('unidades_hoy') or 0):,}",
                               "delta": None, "positivo": True},
        "stock_en_riesgo": {"valor": str(int(f.get("stock_en_riesgo") or 0)),
                            "delta": None, "positivo": None},
    }


def save_stock(id_ingrediente: int, nuevo: float, id_usuario: int | None,
               observaciones: str | None = None) -> None:
    _hay_base()
    db.callproc("sp_ajustar_stock", (sucursal_id(), int(id_ingrediente),
                                     float(nuevo), id_usuario, observaciones))


def update_minimo(id_ingrediente: int, nuevo: float) -> None:
    _hay_base()
    db.execute("UPDATE inventario SET stock_minimo = %s WHERE id_sucursal = %s AND id_ingrediente = %s",
               (float(nuevo), sucursal_id(), int(id_ingrediente)))


def _equipo() -> str | None:
    try:
        return socket.gethostname()
    except Exception:
        return None


def auth(correo: str, password: str) -> dict:
    _hay_base()
    correo = (correo or "").strip()
    filas = db.fetchall(
        "SELECT u.id_usuario, u.nombre, u.correo, u.password_hash, u.id_rol, "
        "u.activo, r.nombre AS rol_nombre "
        "FROM usuarios u LEFT JOIN roles r ON r.id_rol = u.id_rol "
        "WHERE u.correo = %s", (correo,))
    valido = False
    uid = filas[0]["id_usuario"] if filas else None
    if filas and filas[0].get("activo"):
        try:
            import bcrypt
            valido = bcrypt.checkpw(password.encode("utf-8"),
                                    str(filas[0]["password_hash"]).encode("utf-8"))
        except Exception:
            valido = False
    db.execute("INSERT INTO bitacora_accesos (id_usuario, correo_intentado, exitoso, equipo) "
               "VALUES (%s, %s, %s, %s)", (uid, correo, 1 if valido else 0, _equipo()))
    if not valido:
        raise AuthError("Credenciales inválidas.")
    db.execute("UPDATE usuarios SET ultimo_acceso = NOW() WHERE id_usuario = %s", (uid,))
    return {"id": int(uid or 0), "nombre": str(filas[0]["nombre"]),
            "correo": str(filas[0]["correo"]),
            "rol": str(filas[0].get("rol_nombre")
                       or roles.rol_desde_id(filas[0].get("id_rol"))),
            "id_rol": int(filas[0].get("id_rol") or 0)}


def map_bitacora_row(r: dict) -> dict:
    fecha = r.get("fecha_hora")
    if isinstance(fecha, datetime.datetime):
        texto = fecha.strftime("%Y-%m-%d %H:%M")
    else:
        texto = str(fecha or "")
    return {"fecha": texto,
            "usuario": str(r.get("usuario") or "—"),
            "correo": str(r.get("correo_intentado") or ""),
            "resultado": "Correcto" if int(r.get("exitoso") or 0) else "Rechazado",
            "equipo": str(r.get("equipo") or "—")}


def bitacora_rows(limit: int = 200) -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT b.fecha_hora, u.nombre AS usuario, b.correo_intentado, "
        "b.exitoso, b.equipo "
        "FROM bitacora_accesos b LEFT JOIN usuarios u ON u.id_usuario = b.id_usuario "
        "ORDER BY b.fecha_hora DESC, b.id_acceso DESC LIMIT %s", (int(limit),))
    return [map_bitacora_row(r) for r in filas]


def map_lote_row(r: dict) -> dict:
    return {"ingrediente": str(r["ingrediente"]),
            "unidad": str(r.get("unidad") or "kg"),
            "cantidad": float(r.get("cantidad") or 0),
            "caducidad": str(r.get("fecha_caducidad") or ""),
            "dias": int(r.get("dias_restantes") or 0),
            "estado": str(r.get("estado_lote") or "vigente")}


def expiry_rows() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT ingrediente, unidad, cantidad, fecha_caducidad, dias_restantes, estado_lote "
        "FROM v_lotes_por_caducar WHERE id_sucursal = %s", (sucursal_id(),))
    return [map_lote_row(r) for r in filas]


def purge_expired(id_usuario: int | None) -> int:
    _hay_base()
    salidas = db.callproc("sp_purgar_caducados", (sucursal_id(), id_usuario))
    if salidas:
        return int(salidas[0].get("lotes_purgados") or 0)
    return 0


def _fmt_fecha(valor) -> str:
    if isinstance(valor, datetime.datetime):
        return valor.strftime("%Y-%m-%d %H:%M")
    if isinstance(valor, datetime.date):
        return valor.strftime("%Y-%m-%d")
    return str(valor or "")


def map_orden_row(r: dict) -> dict:
    return {"id_orden": int(r["id_orden"]),
            "proveedor": str(r.get("proveedor") or "Sin proveedor"),
            "fecha": _fmt_fecha(r.get("fecha_creacion")),
            "estado": str(r.get("estado") or "borrador"),
            "total": float(r.get("total") or 0)}


def map_orden_detalle_row(r: dict) -> dict:
    cantidad = float(r.get("cantidad_solicitada") or 0)
    precio = float(r.get("precio_unitario") or 0)
    recibido = r.get("cantidad_recibida")
    return {"nombre": str(r.get("nombre") or ""),
            "unidad": str(r.get("unidad") or "kg"),
            "cantidad": cantidad,
            "recibido": None if recibido is None else float(recibido),
            "precio": precio,
            "importe": float(r.get("importe") or cantidad * precio)}


def purchase_orders(limit: int = 100) -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT o.id_orden, p.nombre AS proveedor, o.fecha_creacion, "
        "o.fecha_recepcion, o.estado, o.total "
        "FROM ordenes_compra o JOIN proveedores p ON p.id_proveedor = o.id_proveedor "
        "WHERE o.id_sucursal = %s "
        "ORDER BY o.fecha_creacion DESC, o.id_orden DESC LIMIT %s",
        (sucursal_id(), int(limit)))
    return [map_orden_row(r) for r in filas]


def purchase_order_detail(id_orden: int) -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT i.nombre, um.clave AS unidad, d.cantidad_solicitada, "
        "d.cantidad_recibida, d.precio_unitario, "
        "(d.cantidad_solicitada * d.precio_unitario) AS importe "
        "FROM detalle_ordenes_compra d "
        "JOIN ordenes_compra o ON o.id_orden = d.id_orden "
        "JOIN ingredientes i ON i.id_ingrediente = d.id_ingrediente "
        "JOIN unidades_medida um ON um.id_unidad = i.id_unidad "
        "WHERE d.id_orden = %s AND o.id_sucursal = %s ORDER BY i.nombre",
        (int(id_orden), sucursal_id()))
    return [map_orden_detalle_row(r) for r in filas]


def generate_purchase_orders(id_usuario: int | None) -> int:
    _hay_base()
    salidas = db.callproc("sp_generar_ordenes_compra", (sucursal_id(), id_usuario))
    return len(salidas)


def receive_purchase_order(id_orden: int, id_usuario: int | None) -> None:
    _hay_base()
    db.callproc("sp_recibir_orden_compra", (int(id_orden), id_usuario))
