"""Puerta a los datos reales: vistas y procedimientos de la base.

Cada funcion devuelve la misma forma que usaban los dicts del mock,
asi las pantallas no cambian de logica. Si no hay base (o CAFE_DATOS=mock),
lanza DBError y la pantalla usa el ejemplo.
"""
from __future__ import annotations

import datetime
import math
import os
import socket
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.data import analytics, db, params, roles
from app.data.db import DBError

CANTIDAD_MAX = Decimal("9999999.999")
CANTIDAD_MIN = Decimal("0.001")

DIAS_CORTO = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


class AuthError(Exception):
    """Credenciales invalidas (mensaje generico a proposito)."""


class AccessError(Exception):
    """El usuario no tiene permiso para la accion solicitada."""


MAX_INTENTOS = 5
VENTANA_BLOQUEO_MIN = 15

ROLES_VENTA = {roles.ROL_ADMIN, roles.ROL_GERENTE, roles.ROL_CAJERO}
ROLES_GESTION = {roles.ROL_ADMIN, roles.ROL_GERENTE}


def _rol_usuario(id_usuario: int | None) -> str:
    if not id_usuario:
        raise AccessError("No hay usuario en sesion.")
    filas = db.fetchall(
        "SELECT id_rol, activo FROM usuarios WHERE id_usuario = %s",
        (int(id_usuario),))
    if not filas or not filas[0].get("activo"):
        raise AccessError("Usuario inactivo o inexistente.")
    return roles.rol_desde_id(filas[0].get("id_rol"))


def _require_role(id_usuario: int | None, permitidos: set[str]) -> str:
    rol = _rol_usuario(id_usuario)
    if rol not in permitidos:
        raise AccessError(f"El rol {rol} no tiene permiso para esta accion.")
    return rol


def _intentos_fallidos(correo: str) -> int:
    filas = db.fetchall(
        "SELECT COUNT(*) AS n FROM bitacora_accesos "
        "WHERE correo_intentado = %s AND exitoso = 0 "
        f"AND fecha_hora >= DATE_SUB(NOW(), INTERVAL {VENTANA_BLOQUEO_MIN} MINUTE)",
        (correo,))
    return int(filas[0]["n"] or 0) if filas else 0


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
            "cantidad": float(r.get("cantidad") or 0),
            "ingresos": float(r.get("ingresos") or 0),
            "margen": float(r.get("margen_pct") or 0),
            "tendencia": str(r.get("tendencia") or "down")}


def map_inventario_row(r: dict) -> dict:
    dias = r.get("dias_agotar")
    consumo = r.get("consumo_diario")
    lead = r.get("lead_time_dias")
    punto = r.get("punto_reorden")
    sugerido = r.get("sugerido")
    return {"id_ingrediente": int(r["id_ingrediente"]),
            "nombre": str(r["nombre"]),
            "unidad": str(r.get("unidad") or "kg"),
            "stockActual": float(r.get("stock_actual") or 0),
            "stockMinimo": float(r.get("stock_minimo") or 0),
            "diasAgotar": None if dias is None else float(dias),
            "estado": str(r.get("estado") or "optimo"),
            "consumoDiario": None if consumo is None else float(consumo),
            "leadTimeDias": None if lead is None else float(lead),
            "puntoReorden": None if punto is None else float(punto),
            "stockSeguridad": float(r.get("stock_seguridad") or 0),
            "mermaVentana": float(r.get("merma_ventana") or 0),
            "sugerido": None if sugerido is None else int(sugerido),
            "proveedor": str(r.get("proveedor") or "")}


def sales_last_7_days() -> list[dict]:
    """Dias con venta dentro de los ultimos 7 dias calendario."""
    _hay_base()
    inicio = datetime.date.today() - datetime.timedelta(days=6)
    filas = db.fetchall(
        "SELECT fecha, ventas FROM v_ventas_diarias WHERE id_sucursal = %s "
        "AND fecha >= %s ORDER BY fecha", (sucursal_id(), inicio))
    return [{"day": dia_corto(r["fecha"]), "ventas": float(r["ventas"] or 0)} for r in filas]


def sales_detail() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT nombre, categoria, cantidad, ingresos, margen_pct, tendencia "
        "FROM v_ventas_por_producto ORDER BY ingresos DESC")
    return [map_venta_row(r) for r in filas]


def sales_detail_last_days(days: int = 30, origen: str | None = None) -> list[dict]:
    """Detalle por producto de los ultimos `days` dias calendario."""
    _hay_base()
    dias = max(1, int(days))
    inicio = datetime.date.today() - datetime.timedelta(days=dias - 1)
    sql = (
        "SELECT p.nombre, c.nombre AS categoria, SUM(d.cantidad) AS cantidad, "
        "SUM(d.subtotal) AS ingresos, "
        "ROUND((SUM(d.subtotal) - SUM(d.cantidad * d.costo_unitario)) "
        "/ NULLIF(SUM(d.subtotal), 0) * 100, 1) AS margen_pct, "
        "COALESCE(tp.tendencia, 'down') AS tendencia "
        "FROM detalle_ventas d "
        "JOIN ventas v ON v.id_venta = d.id_venta AND v.estado = 'completada' "
        "JOIN productos p ON p.id_producto = d.id_producto "
        "JOIN categorias_producto c ON c.id_categoria = p.id_categoria "
        "LEFT JOIN v_tendencia_producto tp ON tp.id_producto = p.id_producto "
        "WHERE v.fecha_hora >= %s")
    parametros: list[object] = [inicio]
    if origen:
        sql += " AND v.origen = %s"
        parametros.append(origen)
    sql += (" GROUP BY p.id_producto, p.nombre, c.nombre, tp.tendencia "
            "ORDER BY ingresos DESC")
    filas = db.fetchall(sql, tuple(parametros))
    return [map_venta_row(r) for r in filas]


def inventory_rows() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT e.id_ingrediente, e.nombre, e.unidad, e.stock_actual, "
        "e.stock_minimo, e.consumo_diario, e.dias_agotar, e.estado, "
        "e.lead_time_dias, e.punto_reorden, e.stock_seguridad, "
        "e.merma_ventana, o.sugerido, o.proveedor "
        "FROM v_estado_inventario e "
        "LEFT JOIN v_orden_compra_sugerida o "
        "  ON o.id_sucursal = e.id_sucursal "
        " AND o.id_ingrediente = e.id_ingrediente "
        "WHERE e.id_sucursal = %s", (sucursal_id(),))
    return [map_inventario_row(r) for r in filas]


def pareto_data() -> list[dict]:
    _hay_base()
    filas = db.fetchall("SELECT nombre, ingresos FROM v_pareto_abc")
    return [{"nombre": str(r["nombre"]), "ingresos": float(r["ingresos"] or 0)} for r in filas]


def product_demand_series(days: int = 90, origen: str | None = None) -> dict[str, list[float]]:
    """Serie diaria de unidades por producto, con 0 en dias sin venta.

    Sirve para la clasificacion XYZ: la ventana es calendario completo, asi
    que la intermitencia (dias en cero) tambien cuenta como variabilidad.
    """
    _hay_base()
    dias = max(1, int(days))
    inicio = datetime.date.today() - datetime.timedelta(days=dias - 1)
    sql = (
        "SELECT p.nombre, DATE(v.fecha_hora) AS fecha, SUM(d.cantidad) AS cantidad "
        "FROM detalle_ventas d "
        "JOIN ventas v ON v.id_venta = d.id_venta AND v.estado = 'completada' "
        "JOIN productos p ON p.id_producto = d.id_producto "
        "WHERE v.fecha_hora >= %s")
    parametros: list[object] = [inicio]
    if origen:
        sql += " AND v.origen = %s"
        parametros.append(origen)
    sql += " GROUP BY p.nombre, DATE(v.fecha_hora)"
    filas = db.fetchall(sql, tuple(parametros))
    fechas = [inicio + datetime.timedelta(days=k) for k in range(dias)]
    series: dict[str, dict[datetime.date, float]] = {}
    for r in filas:
        fecha = r["fecha"]
        if isinstance(fecha, datetime.datetime):
            fecha = fecha.date()
        series.setdefault(str(r["nombre"]), {})[fecha] = float(r.get("cantidad") or 0)
    return {nombre: [valores.get(f, 0.0) for f in fechas]
            for nombre, valores in series.items()}


def _report_range(desde: datetime.date, hasta: datetime.date,
                  nombres: list[str], origen: str | None) -> dict:
    # rango sobre fecha_hora (no DATE) para que use el indice de ventas
    filtros = ["v.estado = 'completada'",
               "v.fecha_hora >= %s", "v.fecha_hora < %s + INTERVAL 1 DAY"]
    parametros: list[object] = [desde, hasta]
    if origen:
        filtros.append("v.origen = %s")
        parametros.append(origen)
    if nombres:
        marcas = ", ".join(["%s"] * len(nombres))
        filtros.append(f"p.nombre IN ({marcas})")
        parametros.extend(nombres)
    where = " AND ".join(filtros)
    base = (
        "FROM detalle_ventas d "
        "JOIN ventas v ON v.id_venta = d.id_venta "
        "JOIN productos p ON p.id_producto = d.id_producto "
        "JOIN categorias_producto c ON c.id_categoria = p.id_categoria "
        f"WHERE {where} ")
    por_producto = db.fetchall(
        "SELECT p.nombre, c.nombre AS categoria, SUM(d.cantidad) AS cantidad, "
        "SUM(d.subtotal) AS ingresos, "
        "SUM(d.subtotal - d.cantidad * d.costo_unitario) AS utilidad " + base +
        "GROUP BY p.nombre, c.nombre ORDER BY ingresos DESC", tuple(parametros))
    por_dia = db.fetchall(
        "SELECT DATE(v.fecha_hora) AS fecha, SUM(d.cantidad) AS cantidad, "
        "SUM(d.subtotal) AS ingresos " + base +
        "GROUP BY DATE(v.fecha_hora) ORDER BY fecha", tuple(parametros))
    productos_out = []
    for r in por_producto:
        ingresos = float(r.get("ingresos") or 0)
        utilidad = float(r.get("utilidad") or 0)
        productos_out.append({
            "nombre": str(r["nombre"]),
            "categoria": str(r.get("categoria") or "Sin categoria"),
            "cantidad": float(r.get("cantidad") or 0),
            "ingresos": ingresos,
            "margen": (utilidad / ingresos * 100.0) if ingresos else 0.0,
        })
    diario = [{"fecha": str(r["fecha"]),
               "cantidad": float(r.get("cantidad") or 0),
               "ingresos": float(r.get("ingresos") or 0)} for r in por_dia]
    return {"por_producto": productos_out, "por_dia": diario,
            "totales": analytics.sales_totals(productos_out)}


def sales_report(desde: datetime.date, hasta: datetime.date,
                 productos: list[str] | None = None,
                 origen: str | None = None,
                 comparar: bool = False) -> dict:
    """Reporte de ventas por producto y por dia en un rango de fechas.

    Respeta el origen (`real`/`simulado`) y, si se pasan, los productos
    elegidos. Devuelve totales por producto, serie diaria y totales generales.
    Con `comparar=True` agrega el mismo periodo del ano anterior.
    """
    _hay_base()
    if hasta < desde:
        desde, hasta = hasta, desde
    nombres = [str(p) for p in (productos or []) if str(p).strip()]
    actual = _report_range(desde, hasta, nombres, origen)
    actual.update({"desde": desde, "hasta": hasta, "anterior": None})
    if comparar:
        desde_ant, hasta_ant = analytics.previous_period(desde, hasta)
        anterior = _report_range(desde_ant, hasta_ant, nombres, origen)
        anterior.update({"desde": desde_ant, "hasta": hasta_ant})
        actual["anterior"] = anterior
    return actual


def clima_resumen() -> dict:
    """Clima de referencia del mes y productos en riesgo por calor."""
    _hay_base()
    filas = db.fetchall(
        "SELECT MAX(max_mes_actual) AS temp_max, "
        "SUM(riesgo_calor) AS riesgo, COUNT(*) AS total "
        "FROM v_vida_util_clima")
    if not filas:
        return {"temp_max": None, "riesgo": 0, "total": 0}
    r = filas[0]
    return {"temp_max": None if r.get("temp_max") is None else float(r["temp_max"]),
            "riesgo": int(r.get("riesgo") or 0),
            "total": int(r.get("total") or 0)}


def sales_history(days: int = 90, origen: str | None = None) -> list[tuple]:
    """Serie diaria de los ultimos `days` dias calendario.

    Solo devuelve dias con venta: un dia sin fila no se convierte en cero.
    `origen` permite separar ventas reales de simuladas.
    """
    _hay_base()
    dias = max(1, int(days))
    inicio = datetime.date.today() - datetime.timedelta(days=dias - 1)
    parametros: tuple
    if origen:
        sql = ("SELECT fecha, ventas FROM v_ventas_diarias_origen "
               "WHERE id_sucursal = %s AND origen = %s AND fecha >= %s "
               "ORDER BY fecha")
        parametros = (sucursal_id(), origen, inicio)
    else:
        sql = ("SELECT fecha, ventas FROM v_ventas_diarias "
               "WHERE id_sucursal = %s AND fecha >= %s ORDER BY fecha")
        parametros = (sucursal_id(), inicio)
    filas = db.fetchall(sql, parametros)
    return [(r["fecha"], float(r["ventas"] or 0)) for r in filas]


def data_origin() -> dict:
    """Cuenta ventas reales vs simuladas para etiquetar la UI."""
    _hay_base()
    try:
        filas = db.fetchall(
            "SELECT origen, COUNT(*) AS n FROM ventas "
            "WHERE estado = 'completada' GROUP BY origen")
    except Exception:  # noqa: BLE001 - la etiqueta no debe tumbar la pantalla
        return {"real": 0, "simulado": 0, "total": 0, "pct_simulado": 0.0}
    total = sum(int(f.get("n") or 0) for f in filas)
    real = sum(int(f.get("n") or 0) for f in filas if str(f.get("origen")) == "real")
    simulado = total - real
    return {"real": real, "simulado": simulado, "total": total,
            "pct_simulado": (simulado / total * 100.0) if total else 0.0}


def _numero(valor, digitos: int = 2) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numero):
        return None
    return round(numero, digitos)


def save_forecast(historia: list[tuple], diario: list[tuple],
                  productos: list[dict], backtest: dict,
                  id_usuario: int | None) -> int:
    _hay_base()
    _require_role(id_usuario, ROLES_GESTION)
    if not historia or not diario:
        raise ValueError("sin datos para guardar el pronóstico")
    crecimiento = analytics.horizon_growth(
        float(historia[-1][1]), [float(v) for _, v in diario]) * 100.0
    with db.transaction() as cur:
        cur.execute("SELECT id_modelo FROM modelos_pronostico ORDER BY id_modelo LIMIT 1")
        modelo = cur.fetchone()
        if modelo:
            id_modelo = int(modelo["id_modelo"])
        else:
            cur.execute(
                "INSERT INTO modelos_pronostico (nombre, descripcion) VALUES (%s, %s)",
                ("Regresion sobre fecha + reparto por participacion",
                 "Generado desde la app"))
            id_modelo = int(cur.lastrowid)

        cur.execute(
            "INSERT INTO pronosticos (id_modelo, id_sucursal, id_usuario, "
            "horizonte_dias, crecimiento_pct, mae_modelo, mae_naive, mae_ma7, "
            "wape_modelo, sesgo_modelo, es_preliminar) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (id_modelo, sucursal_id(), id_usuario, len(diario),
             _numero(crecimiento), _numero(backtest.get("mae_modelo")),
             _numero(backtest.get("mae_naive")), _numero(backtest.get("mae_ma7")),
             _numero(backtest.get("wape_modelo")),
             _numero(backtest.get("sesgo_modelo")),
             0 if backtest.get("gana") else 1))
        id_pronostico = int(cur.lastrowid)

        cur.executemany(
            "INSERT INTO pronostico_diario (id_pronostico, fecha, ventas_estimadas) "
            "VALUES (%s, %s, %s)",
            [(id_pronostico, fecha, float(valor)) for fecha, valor in diario])

        for producto in productos:
            cur.execute("SELECT id_producto FROM productos WHERE nombre = %s",
                        (str(producto.get("nombre") or ""),))
            fila = cur.fetchone()
            if not fila:
                continue
            cur.execute(
                "INSERT INTO pronostico_producto (id_pronostico, id_producto, "
                "ingresos_actual, ingresos_predicho, crecimiento_pct) "
                "VALUES (%s, %s, %s, %s, %s)",
                (id_pronostico, int(fila["id_producto"]),
                 _numero(producto.get("actual"), 0) or 0,
                 _numero(producto.get("predicho"), 0) or 0,
                 _numero(producto.get("crecimiento")) or 0))
    return id_pronostico


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
        "productos_vendidos": {"valor": analytics.fmt_qty(f.get("unidades_hoy") or 0),
                               "delta": None, "positivo": True},
        "stock_en_riesgo": {"valor": str(int(f.get("stock_en_riesgo") or 0)),
                            "delta": None, "positivo": None},
    }


def save_stock(id_ingrediente: int, nuevo: float, id_usuario: int | None,
               observaciones: str | None = None) -> None:
    _hay_base()
    _require_role(id_usuario, ROLES_GESTION)
    db.callproc("sp_ajustar_stock", (sucursal_id(), int(id_ingrediente),
                                     float(nuevo), id_usuario, observaciones))


def update_minimo(id_ingrediente: int, nuevo: float,
                  id_usuario: int | None = None) -> None:
    _hay_base()
    _require_role(id_usuario, ROLES_GESTION)
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
    if _intentos_fallidos(correo) >= MAX_INTENTOS:
        raise AuthError(
            f"Demasiados intentos fallidos. Espera {VENTANA_BLOQUEO_MIN} minutos.")
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
    _require_role(id_usuario, ROLES_GESTION)
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
    _require_role(id_usuario, ROLES_GESTION)
    salidas = db.callproc("sp_generar_ordenes_compra", (sucursal_id(), id_usuario))
    return len(salidas)


def receive_purchase_order(id_orden: int, id_usuario: int | None) -> None:
    _hay_base()
    _require_role(id_usuario, ROLES_GESTION)
    db.callproc("sp_recibir_orden_compra", (int(id_orden), id_usuario))


# -- punto de venta ------------------------------------------------------

def pos_categories() -> list[str]:
    """Categorias en el orden en que conviene mostrarlas en la caja."""
    _hay_base()
    filas = db.fetchall(
        "SELECT nombre FROM categorias_producto "
        "ORDER BY FIELD(nombre, 'Frutas', 'Verduras', 'Jugos', 'Bebidas', 'Snacks', 'Abarrotes'), "
        "nombre")
    return [str(f["nombre"]) for f in filas]


def pos_products(search: str = "", categoria: str | None = None) -> list[dict]:
    """Productos activos para el catalogo de la caja."""
    _hay_base()
    sql = (
        "SELECT p.id_producto, p.nombre, c.nombre AS categoria, "
        "p.precio_venta, p.costo_unitario, u.clave AS unidad, "
        "u.solo_enteros "
        "FROM productos p "
        "JOIN categorias_producto c ON c.id_categoria = p.id_categoria "
        "JOIN unidades_medida u ON u.id_unidad = p.id_unidad "
        "WHERE p.activo = 1")
    parametros: list[object] = []
    texto = (search or "").strip()
    if texto:
        sql += " AND p.nombre LIKE %s"
        parametros.append(f"%{texto}%")
    if categoria:
        sql += " AND c.nombre = %s"
        parametros.append(categoria)
    sql += (" ORDER BY FIELD(c.nombre, 'Frutas', 'Verduras', 'Jugos', "
            "'Bebidas', 'Snacks', 'Abarrotes'), p.nombre")
    filas = db.fetchall(sql, tuple(parametros))
    return [{"id_producto": int(f["id_producto"]),
             "nombre": str(f["nombre"]),
             "categoria": str(f["categoria"]),
             "precio": float(f["precio_venta"]),
             "costo": float(f["costo_unitario"]),
             "unidad": str(f["unidad"]),
             "solo_enteros": bool(f.get("solo_enteros"))} for f in filas]


def pos_payment_methods() -> list[dict]:
    _hay_base()
    filas = db.fetchall(
        "SELECT id_metodo_pago, nombre FROM metodos_pago ORDER BY id_metodo_pago")
    return [{"id": int(f["id_metodo_pago"]), "nombre": str(f["nombre"])} for f in filas]


def _cantidad_decimal(valor: object) -> Decimal:
    """Convierte una cantidad de la caja a DECIMAL(10,3)."""
    try:
        cantidad = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Producto o cantidad inválidos.") from exc
    if not cantidad.is_finite():
        raise ValueError("La cantidad debe ser un número válido.")
    cantidad = cantidad.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if cantidad < CANTIDAD_MIN:
        raise ValueError("La cantidad debe ser mayor a cero.")
    if cantidad > CANTIDAD_MAX:
        raise ValueError("La cantidad es demasiado grande.")
    return cantidad


def register_sale(items: list[dict], id_metodo_pago: int,
                  id_usuario: int | None, descuento: float = 0.0,
                  origen: str = "real") -> dict:
    """Registra una venta completa (cabecera + renglones) en una transaccion.

    El precio y el costo se releen de la base al momento de cobrar: la caja no
    confia en los valores que trae la pantalla. Los totales los calculan los
    triggers de detalle_ventas, no Python. Las cantidades aceptan hasta tres
    decimales (0.500 kg, 0.250 L). `origen` separa ventas reales de simuladas.
    """
    if not items:
        raise ValueError("El ticket está vacío.")
    if not id_usuario:
        raise ValueError("No hay usuario en sesión.")
    if origen not in ("real", "simulado"):
        raise ValueError("Origen de venta inválido.")

    pedidos: dict[int, Decimal] = {}
    for item in items:
        try:
            id_producto = int(item.get("id_producto") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("Producto o cantidad inválidos.") from exc
        if id_producto <= 0:
            raise ValueError("Producto o cantidad inválidos.")
        cantidad = _cantidad_decimal(item.get("cantidad"))
        pedidos[id_producto] = pedidos.get(id_producto, Decimal("0")) + cantidad

    if any(cantidad > CANTIDAD_MAX for cantidad in pedidos.values()):
        raise ValueError("La cantidad es demasiado grande.")

    try:
        descuento_dec = Decimal(str(descuento or 0))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Descuento inválido.") from exc
    if not descuento_dec.is_finite():
        raise ValueError("Descuento inválido.")
    descuento_dec = max(Decimal("0"), descuento_dec).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)

    _hay_base()
    _require_role(id_usuario, ROLES_VENTA)
    sucursal = sucursal_id()

    with db.transaction() as cur:
        ids = tuple(pedidos)
        marcadores = ",".join(["%s"] * len(ids))
        cur.execute(
            f"SELECT id_producto, nombre, precio_venta, costo_unitario "
            f"FROM productos WHERE activo = 1 AND id_producto IN ({marcadores})",
            ids)
        productos = {int(f["id_producto"]): f for f in cur.fetchall()}
        faltantes = [str(i) for i in ids if i not in productos]
        if faltantes:
            raise ValueError(
                "Producto no disponible: " + ", ".join(faltantes) + ".")

        cur.execute("SELECT id_metodo_pago FROM metodos_pago WHERE id_metodo_pago = %s",
                    (int(id_metodo_pago),))
        if not cur.fetchone():
            raise ValueError("Método de pago inválido.")

        # Verifica existencias antes de insertar. Bloquea las filas de inventario
        # para que dos cajas no puedan vender el mismo stock a la vez.
        cur.execute(
            f"SELECT id_producto, id_ingrediente, cantidad FROM recetas "
            f"WHERE id_producto IN ({marcadores})", ids)
        requeridos: dict[int, Decimal] = {}
        for receta in cur.fetchall():
            id_ingrediente = int(receta["id_ingrediente"])
            id_producto = int(receta["id_producto"])
            requeridos[id_ingrediente] = (
                requeridos.get(id_ingrediente, Decimal("0"))
                + Decimal(str(receta["cantidad"])) * pedidos[id_producto]
            )
        if requeridos:
            ids_ingredientes = tuple(requeridos)
            marcadores_ing = ",".join(["%s"] * len(ids_ingredientes))
            cur.execute(
                f"SELECT inv.id_ingrediente, i.nombre, inv.stock_actual "
                f"FROM inventario inv "
                f"JOIN ingredientes i ON i.id_ingrediente = inv.id_ingrediente "
                f"WHERE inv.id_sucursal = %s "
                f"AND inv.id_ingrediente IN ({marcadores_ing}) FOR UPDATE",
                (sucursal, *ids_ingredientes))
            existencias = {
                int(f["id_ingrediente"]): (str(f["nombre"]),
                                           Decimal(str(f["stock_actual"])))
                for f in cur.fetchall()
            }
            faltantes = []
            for id_ingrediente, requerido in requeridos.items():
                nombre, disponible = existencias.get(
                    id_ingrediente, (f"ingrediente {id_ingrediente}", Decimal("0")))
                if disponible < requerido:
                    faltantes.append(
                        f"{nombre}: disponible {disponible:.3f}, "
                        f"requerido {requerido:.3f}")
            if faltantes:
                raise ValueError("Stock insuficiente — " + "; ".join(faltantes) + ".")

        subtotal = sum(
            (Decimal(str(productos[i]["precio_venta"])) * cantidad
             for i, cantidad in pedidos.items()),
            Decimal("0"),
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if descuento_dec > subtotal:
            raise ValueError("El descuento no puede ser mayor al subtotal.")

        cur.execute(
            "INSERT INTO ventas (id_sucursal, id_usuario, id_metodo_pago, "
            "subtotal, descuento, total, estado, origen) "
            "VALUES (%s, %s, %s, 0, %s, 0, 'completada', %s)",
            (sucursal, int(id_usuario), int(id_metodo_pago), descuento_dec, origen))
        id_venta = int(cur.lastrowid)

        renglones = [
            (id_venta, id_producto, cantidad,
             Decimal(str(productos[id_producto]["precio_venta"])),
             Decimal(str(productos[id_producto]["costo_unitario"])))
            for id_producto, cantidad in pedidos.items()
        ]
        cur.executemany(
            "INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, "
            "precio_unitario, costo_unitario) VALUES (%s, %s, %s, %s, %s)",
            renglones)

        cur.execute(
            "SELECT subtotal, descuento, total FROM ventas WHERE id_venta = %s",
            (id_venta,))
        totales = cur.fetchone()

    return {"id_venta": id_venta,
            "subtotal": float(totales["subtotal"]),
            "descuento": float(totales["descuento"]),
            "total": float(totales["total"]),
            "unidades": float(sum(pedidos.values(), Decimal("0")))}
