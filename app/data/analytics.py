"""numeros que salen de los dicts, nada a mano.

todas las funciones reciben listas de dicts (las de mock_data o las que
vengan de la base despues) y devuelven cuentas. Sin dependencias nuevas.
"""
from __future__ import annotations

import datetime as _dt
import math

# -- helpers chicos ------------------------------------------------------

def pct_change(nuevo: float, viejo: float) -> float | None:
    if not viejo:
        return None
    return (nuevo - viejo) / abs(viejo) * 100.0


def fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def fmt_qty(v: float) -> str:
    """Cantidad legible: enteros sin decimales, kilos/litros con hasta 3."""
    numero = float(v or 0)
    if abs(numero - round(numero)) < 1e-9:
        return f"{int(round(numero)):,}"
    return f"{numero:,.3f}".rstrip("0").rstrip(".")


# -- ventas --------------------------------------------------------------

def sales_totals(detail: list[dict]) -> dict:
    ingresos = sum(float(d.get("ingresos") or 0) for d in detail)
    unidades = sum(float(d.get("cantidad") or 0) for d in detail)
    ticket = ingresos / unidades if unidades else 0.0
    margen_pond = 0.0
    if ingresos:
        margen_pond = sum(float(d.get("ingresos") or 0) * float(d.get("margen") or 0) for d in detail) / ingresos
    return {"ingresos": ingresos, "unidades": unidades, "ticket": ticket, "margen_pond": margen_pond}


def top_products(detail: list[dict], n: int = 5) -> list[dict]:
    orden = sorted(detail, key=lambda d: float(d.get("ingresos") or 0), reverse=True)
    return [{"product": d["nombre"], "ingresos": float(d.get("ingresos") or 0)} for d in orden[:n]]


def revenue_by_category(detail: list[dict]) -> list[dict]:
    """Ingresos por categoria, de menor a mayor (listo para barh)."""
    acumulado: dict[str, float] = {}
    for d in detail:
        categoria = str(d.get("categoria") or "Sin categoría")
        acumulado[categoria] = acumulado.get(categoria, 0.0) + float(d.get("ingresos") or 0)
    return [
        {"categoria": categoria, "ingresos": ingresos}
        for categoria, ingresos in sorted(acumulado.items(), key=lambda kv: kv[1])
    ]


def trend_counts(detail: list[dict]) -> dict:
    up = sum(1 for d in detail if d.get("tendencia") == "up")
    return {"up": up, "down": len(detail) - up}


def dashboard_kpis(detail: list[dict], last_7: list[dict], inventory: list[dict]) -> dict:
    tot = sales_totals(detail)
    dias = [float(d.get("ventas") or 0) for d in last_7]
    hoy = dias[-1] if dias else 0.0
    ayer = dias[-2] if len(dias) > 1 else 0.0
    var = pct_change(hoy, ayer)
    criticos = sum(1 for i in inventory if i.get("estado") == "critico")
    return {
        "ventas_hoy": {
            "valor": fmt_money(hoy),
            "delta": f"{abs(var):.1f}%" if var is not None else None,
            "positivo": (var or 0) >= 0,
        },
        "ticket_promedio": {"valor": fmt_money(tot["ticket"]), "delta": None, "positivo": True},
        "productos_vendidos": {"valor": fmt_qty(tot["unidades"]), "delta": None, "positivo": True},
        "stock_en_riesgo": {"valor": str(criticos), "delta": None, "positivo": None},
    }


# -- inventario ----------------------------------------------------------
# una sola funcion pura: estado y dias salen de stock, minimo y consumo.
# no se guardan los derivados. Reglas: stock 0 siempre critico con 0 dias;
# minimo 0 es neutro (sin minimo, fuera de alertas pero visible);
# consumo desconocido o 0 deja dias en None ("—" en la tabla).

SIN_MINIMO = "sin_minimo"

ENTERO_UNIDADES = {"pzas", "bidones"}


def stock_status(stock: float, minimo: float, consumo: float | None,
                 umbral_advertencia: float = 1.25) -> tuple[str, float | None]:
    stock = float(stock or 0)
    minimo = float(minimo or 0)
    if stock <= 0:
        return ("critico", 0.0)
    dias = stock / consumo if consumo and consumo > 0 else None
    if minimo <= 0:
        return (SIN_MINIMO, dias)
    if stock < minimo:
        return ("critico", dias)
    if stock < minimo * float(umbral_advertencia or 1.25):
        return ("advertencia", dias)
    return ("optimo", dias)

def inventory_health(items: list[dict]) -> dict:
    total = len(items)
    crit = [i for i in items if i.get("estado") == "critico"]
    adv = sum(1 for i in items if i.get("estado") == "advertencia")
    opt = sum(1 for i in items if i.get("estado") == "optimo")
    crit_orden = sorted(crit, key=lambda i: float(i.get("diasAgotar") or 0))
    return {
        "total": total,
        "optimo": opt,
        "advertencia": adv,
        "critico": len(crit),
        "criticos": [i.get("nombre", "") for i in crit_orden],
    }


def daily_use(item: dict) -> float:
    dias = float(item.get("diasAgotar") or 0)
    if dias <= 0:
        return 0.0
    return float(item.get("stockActual") or 0) / dias


def reorder_point(item: dict, lead_time: float = 2.0,
                  dias_seguridad: float = 1.0,
                  stock_seguridad: float | None = None) -> float:
    """Punto de reorden: minimo manual o demanda de lead time + colchon.

    Si `stock_seguridad` viene de la vista XYZ se usa tal cual; si no, el
    colchon se calcula por dias de consumo. Sin consumo solo aplica el
    minimo (o el colchon, si existe).
    """
    consumo = float(item.get("consumoDiario") or 0)
    minimo = float(item.get("stockMinimo") or 0)
    lead = 2.0 if lead_time is None else float(lead_time)
    if stock_seguridad is None:
        seguro_dias = 1.0 if dias_seguridad is None else float(dias_seguridad)
        seguridad = consumo * seguro_dias
    else:
        seguridad = max(0.0, float(stock_seguridad))
    if consumo <= 0:
        return max(minimo, seguridad)
    return max(minimo, consumo * lead + seguridad)


def reorder_qty(item: dict, objetivo: float = 2.0, *,
                lead_time: float = 2.0, dias_seguridad: float = 1.0,
                dias_cobertura: float = 7.0,
                stock_seguridad: float | None = None) -> int:
    """Cantidad sugerida para cubrir lead time, colchon y cobertura.

    Sin consumo usa la regla historica (minimo x objetivo - stock). Con
    consumo toma el mayor entre esa regla y los dias de cobertura, para no
    pedir de menos cuando el minimo quedo viejo. `stock_seguridad` permite
    usar el colchon estadistico de la vista XYZ en lugar de dias fijos.
    """
    stock = float(item.get("stockActual") or 0)
    minimo = float(item.get("stockMinimo") or 0)
    consumo = float(item.get("consumoDiario") or 0)
    objetivo = 2.0 if objetivo is None else float(objetivo)
    lead = 2.0 if lead_time is None else float(lead_time)
    cobertura = 7.0 if dias_cobertura is None else float(dias_cobertura)
    if stock_seguridad is None:
        seguro_dias = 1.0 if dias_seguridad is None else float(dias_seguridad)
        seguridad = consumo * seguro_dias
    else:
        seguridad = max(0.0, float(stock_seguridad))
    if consumo > 0:
        nivel = max(minimo * objetivo,
                    consumo * (lead + cobertura) + seguridad)
    else:
        nivel = max(minimo * objetivo, seguridad)
    return max(0, math.ceil(nivel - stock))


def abc_classes(pareto: list[dict], corte_a: float = 80.0,
                corte_b: float = 95.0) -> list[dict]:
    orden = sorted(pareto, key=lambda d: float(d.get("ingresos") or 0), reverse=True)
    total = sum(float(d.get("ingresos") or 0) for d in orden) or 1.0
    acc = 0.0
    out = []
    for d in orden:
        acc += float(d.get("ingresos") or 0)
        pct = acc / total * 100.0
        clase = "A" if len(orden) == 1 or pct <= corte_a else (
            "B" if pct <= corte_b else "C")
        out.append({"nombre": d.get("nombre", ""), "ingresos": float(d.get("ingresos") or 0),
                    "acum_pct": pct, "clase": clase})
    return out


def abc_summary(clases: list[dict]) -> list[dict]:
    """Participacion de ingresos y productos por clase A/B/C."""
    total_ingresos = sum(float(d.get("ingresos") or 0) for d in clases) or 1.0
    total_productos = len(clases) or 1
    resumen = []
    for clase in ("A", "B", "C"):
        filas = [d for d in clases if d.get("clase") == clase]
        ingresos = sum(float(d.get("ingresos") or 0) for d in filas)
        resumen.append({
            "clase": clase,
            "productos": len(filas),
            "ingresos": ingresos,
            "pct_ingresos": ingresos / total_ingresos * 100.0,
            "pct_productos": len(filas) / total_productos * 100.0,
        })
    return resumen


# -- XYZ (variabilidad de la demanda) -----------------------------------

XYZ_CORTE_X = 0.5
XYZ_CORTE_Y = 1.0
XYZ_Z_POR_CLASE = {"X": 1.28, "Y": 1.65, "Z": 2.33}


def xyz_class(serie: list[float], corte_x: float = XYZ_CORTE_X,
              corte_y: float = XYZ_CORTE_Y) -> dict:
    """Clasifica la demanda diaria por coeficiente de variacion (CV).

    X: demanda estable (CV <= corte_x), Y: media (CV <= corte_y), Z: erratica.
    La serie debe traer un valor por dia del periodo (0 en dias sin venta):
    los ceros cuentan porque la intermitencia tambien es variabilidad.
    """
    valores = [float(v or 0) for v in serie]
    n = len(valores)
    if n == 0:
        return {"clase": "—", "cv": None, "media": 0.0, "desv": 0.0, "n": 0}
    media = sum(valores) / n
    if media <= 0:
        return {"clase": "—", "cv": None, "media": 0.0, "desv": 0.0, "n": n}
    var = sum((v - media) ** 2 for v in valores) / n
    desv = math.sqrt(var)
    cv = desv / media
    clase = "X" if cv <= corte_x else ("Y" if cv <= corte_y else "Z")
    return {"clase": clase, "cv": cv, "media": media, "desv": desv, "n": n}


def xyz_safety_stock(sigma: float | None, lead_time: float | None,
                     clase: str | None, *,
                     z_por_clase: dict[str, float] | None = None,
                     consumo_diario: float | None = None,
                     dias_seguridad: float | None = 1.0,
                     dias_con_datos: int = 0,
                     min_dias: int = 7) -> float:
    """Colchon estadistico por clase XYZ, con respaldo por dias.

    Formula: z * sigma * sqrt(lead_time). La clase y la desviacion salen de
    la demanda diaria de la ventana XYZ. Si no hay clase valida o no hay
    suficientes dias con venta, se usa consumo_diario * dias_seguridad.
    """
    lead = max(1.0, float(lead_time if lead_time is not None else 2.0))
    if clase in XYZ_Z_POR_CLASE and int(dias_con_datos) >= int(min_dias):
        z = (z_por_clase or XYZ_Z_POR_CLASE).get(str(clase))
        if z is not None:
            return max(0.0, float(z) * max(0.0, float(sigma or 0)) * math.sqrt(lead))
    seguro = 1.0 if dias_seguridad is None else float(dias_seguridad)
    return max(0.0, float(consumo_diario or 0) * seguro)


def abc_xyz_matrix(abc: list[dict], xyz: dict[str, dict]) -> list[dict]:
    """Cruza la clase ABC (ingresos) con XYZ (variabilidad) por producto."""
    celdas: dict[tuple[str, str], dict] = {
        (a, x): {"abc": a, "xyz": x, "productos": [], "ingresos": 0.0}
        for a in ("A", "B", "C") for x in ("X", "Y", "Z")}
    for fila in abc:
        clase_a = str(fila.get("clase") or "C")
        if clase_a not in ("A", "B", "C"):
            continue
        nombre = str(fila.get("nombre") or "")
        clase_x = str((xyz.get(nombre) or {}).get("clase") or "—")
        if clase_x not in ("X", "Y", "Z"):
            continue
        celda = celdas[(clase_a, clase_x)]
        celda["productos"].append(nombre)
        celda["ingresos"] += float(fila.get("ingresos") or 0)
    return [celdas[(a, x)] for a in ("A", "B", "C") for x in ("X", "Y", "Z")]


def report_daily_series(rows: list[dict]) -> list[dict]:
    """Agrega filas {fecha, cantidad, ingresos} por dia, ordenadas."""
    acumulado: dict[str, dict] = {}
    for r in rows:
        fecha = str(r.get("fecha") or "")
        if not fecha:
            continue
        acc = acumulado.setdefault(
            fecha, {"fecha": fecha, "cantidad": 0.0, "ingresos": 0.0})
        acc["cantidad"] += float(r.get("cantidad") or 0)
        acc["ingresos"] += float(r.get("ingresos") or 0)
    return [acumulado[f] for f in sorted(acumulado)]


def _menos_un_ano(fecha: _dt.date) -> _dt.date:
    """Mismo dia del ano anterior; el 29 de febrero cae al 28."""
    try:
        return fecha.replace(year=fecha.year - 1)
    except ValueError:
        return fecha.replace(year=fecha.year - 1, day=28)


def previous_period(desde: _dt.date, hasta: _dt.date) -> tuple[_dt.date, _dt.date]:
    """Periodo equivalente del ano anterior, para comparar reportes."""
    return _menos_un_ano(desde), _menos_un_ano(hasta)


# -- ventana de la grafica de pronostico ---------------------------------

GRAFICA_DIAS = 30
GRAFICA_HUECO_DIAS = 2


def chart_history_window(hist: list[tuple[_dt.date, float]],
                         futuro: list[tuple[_dt.date, float]] | None = None,
                         dias: int = GRAFICA_DIAS) -> list[tuple[_dt.date, float]]:
    """Ultimos `dias` calendario de historia, alineados al pronostico.

    La ventana termina el dia anterior al primer pronostico para que un
    historico viejo no deje meses muertos en el eje X. Si no hay pronostico,
    termina en el ultimo dato.
    """
    pares = sorted(hist, key=lambda p: p[0])
    if not pares:
        return []
    fin = pares[-1][0]
    if futuro:
        fin = max(fin, futuro[0][0] - _dt.timedelta(days=1))
    inicio = fin - _dt.timedelta(days=max(1, int(dias)) - 1)
    return [(d, float(v)) for d, v in pares if d >= inicio]


def _cuantil(ordenados: list[float], p: float) -> float:
    if not ordenados:
        return 0.0
    k = (len(ordenados) - 1) * p
    bajo = int(k)
    alto = min(bajo + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (k - bajo)


def chart_scale(hist: list[tuple[_dt.date, float]],
                futuro: list[tuple[_dt.date, float]],
                factor: float = 2.0) -> dict:
    """Tope robusto del eje Y y puntos historicos que quedan fuera.

    La cerca de Tukey (Q3 + factor * IQR) evita que un pico aislado aplaste
    la escala del resto de la serie. Si no hay picos, devuelve `tope=None`
    para dejar que matplotlib ajuste solo. El tope nunca recorta el pronostico.
    """
    hist_vals = [float(v) for _, v in hist]
    fut_vals = [float(v) for _, v in futuro]
    valores = sorted(hist_vals + fut_vals)
    if not valores:
        return {"tope": None, "fuera": []}
    q1 = _cuantil(valores, 0.25)
    q3 = _cuantil(valores, 0.75)
    iqr = q3 - q1
    if iqr > 0:
        cerca = q3 + max(0.0, float(factor)) * iqr
    else:
        # serie casi plana: separa el pico sin dejar el eje en cero
        cerca = max(q3 * 1.5, max(valores) * 0.5)
    tope = max(cerca, (max(fut_vals) * 1.05) if fut_vals else cerca)
    fuera = [(d, float(v)) for d, v in hist if float(v) > tope]
    return {"tope": tope if fuera else None, "fuera": fuera}


# -- pronostico ----------------------------------------------------------
# regresion sobre fecha real (ordinal de la fecha, no posicion).
# nivel = valor ajustado en el ultimo punto: f(1) cae un paso de
# pendiente adelante, sin el sesgo del promedio movil.
# pasos diarios con etiqueta de dias reales. Con 28+ dias se suma
# indice por dia de semana. Backtest rolling-origin contra ingenuo
# y media movil 7: si el modelo no gana, es preliminar.

MESES_CORTO = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
               "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12}
MES_NOMBRE = {v: k for k, v in MESES_CORTO.items() if k != "sept"}


def parse_dia(etiqueta: str, hoy: _dt.date | None = None) -> _dt.date | None:
    hoy = hoy or _dt.date.today()
    txt = (etiqueta or "").strip().lower()
    if txt == "hoy":
        return hoy
    partes = txt.split()
    if len(partes) != 2:
        return None
    try:
        return _dt.date(hoy.year, MESES_CORTO[partes[1]], int(partes[0]))
    except (KeyError, ValueError):
        return None


def etiqueta_corta(fecha: _dt.date) -> str:
    return f"{fecha.day:02d} {MES_NOMBRE.get(fecha.month, '')}"


def fit_trend(fechas: list[_dt.date], valores: list[float]) -> tuple[float, float]:
    # devuelve (nivel en el ultimo punto, pendiente por dia)
    xs = [float(f.toordinal()) for f in fechas]
    ys = [float(v) for v in valores]
    n = len(xs)
    if n < 2:
        return (ys[0] if ys else 0.0, 0.0)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    pend = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0.0
    a = my - pend * mx
    return (a + pend * xs[-1], pend)


def dow_factors(fechas: list[_dt.date], valores: list[float]) -> dict[int, float]:
    # indice multiplicativo por dia de semana, solo con 28+ dias
    if len(fechas) < 28:
        return {}
    nivel, pend = fit_trend(fechas, valores)
    xs = [float(f.toordinal()) for f in fechas]
    a = nivel - pend * xs[-1]
    por_dia: dict[int, list[float]] = {}
    for f, y in zip(fechas, valores):
        ajustado = a + pend * float(f.toordinal())
        if ajustado > 0 and y is not None:
            por_dia.setdefault(f.weekday(), []).append(float(y) / ajustado)
    factores = {d: (sum(v) / len(v)) for d, v in por_dia.items() if v}
    media = sum(factores.values()) / len(factores) if factores else 1.0
    return {d: f / media for d, f in factores.items()} if media else {}


def forecast_daily(history: list[tuple[_dt.date, float]], steps: int = 30,
                 ndigits: int = -1, start: _dt.date | None = None
                 ) -> list[tuple[_dt.date, float]]:
    """Pronostico diario desde hoy (o desde `start`), no desde el ultimo dato.

    Si el ultimo dato es viejo, el pronostico arranca hoy para no nacer en el
    pasado. `start` existe para pruebas deterministas y para simulaciones.
    """
    # ndigits sigue la escala: -1 en pesos (miles), 0 en unidades
    if not history or steps <= 0:
        return []
    hist = sorted(history, key=lambda p: p[0])
    fechas = [d for d, _ in hist]
    valores = [float(v) for _, v in hist]
    nivel, pend = fit_trend(fechas, valores)
    dow = dow_factors(fechas, valores)
    ultima = fechas[-1]
    inicio = start if start is not None else max(
        ultima + _dt.timedelta(days=1), _dt.date.today())
    if inicio <= ultima:
        inicio = ultima + _dt.timedelta(days=1)
    out = []
    for k in range(steps):
        f = inicio + _dt.timedelta(days=k)
        h = (f - ultima).days
        v = (nivel + pend * h) * dow.get(f.weekday(), 1.0)
        out.append((f, max(0.0, round(v, ndigits))))
    return out


def _wape(predicciones: list[float], reales: list[float]) -> float | None:
    total = sum(abs(r) for r in reales)
    if not reales or total == 0:
        return None
    return sum(abs(p - r) for p, r in zip(predicciones, reales)) / total * 100.0


def _smape(predicciones: list[float], reales: list[float]) -> float | None:
    if not reales:
        return None
    valores = []
    for p, r in zip(predicciones, reales):
        denom = abs(p) + abs(r)
        valores.append(2.0 * abs(p - r) / denom * 100.0 if denom else 0.0)
    return sum(valores) / len(valores) if valores else None


def _sesgo(predicciones: list[float], reales: list[float]) -> float | None:
    total = sum(abs(r) for r in reales)
    if not reales or total == 0:
        return None
    return sum(p - r for p, r in zip(predicciones, reales)) / total * 100.0


def backtest(fechas: list[_dt.date], valores: list[float], min_origen: int = 7) -> dict:
    """Rolling-origin al horizonte real, en dias calendario.

    Cada origen entrena con lo anterior y predice la siguiente observacion a
    `h = fecha_siguiente - ultima_fecha` dias. No asume que la siguiente fila
    sea manana: si hay un hueco de 28 dias, el error se mide a 28 dias.
    """
    pares = sorted(zip(fechas, valores), key=lambda p: p[0])
    n = len(pares)
    vacio = {
        "mae_modelo": None, "mae_naive": None, "mae_ma7": None,
        "mape_modelo": None, "wape_modelo": None, "wape_naive": None,
        "wape_ma7": None, "smape_modelo": None, "sesgo_modelo": None,
        "gana": False, "n": n, "n_origenes": 0,
        "horizonte_medio": 0.0, "horizonte_max": 0, "suficiente": False,
        "motivo": "muy pocos datos",
    }
    if n < 2:
        return vacio

    inicio = min(min_origen, n - 1)
    preds: dict[str, list[float]] = {"modelo": [], "naive": [], "ma7": []}
    reales: list[float] = []
    horizontes: list[int] = []
    for k in range(inicio, n):
        tramo = pares[:k]
        if not tramo:
            continue
        real = float(pares[k][1])
        f_tramo = [d for d, _ in tramo]
        v_tramo = [float(v) for _, v in tramo]
        nivel, pend = fit_trend(f_tramo, v_tramo)
        dow = dow_factors(f_tramo, v_tramo)
        meta = pares[k][0]
        h = max(1, (meta - f_tramo[-1]).days)
        preds["modelo"].append((nivel + pend * h) * dow.get(meta.weekday(), 1.0))
        preds["naive"].append(v_tramo[-1])
        preds["ma7"].append(sum(v_tramo[-7:]) / len(v_tramo[-7:]))
        reales.append(real)
        horizontes.append(h)

    def _mae(v: list[float]) -> float | None:
        return sum(abs(p - r) for p, r in zip(v, reales)) / len(v) if v else None

    mae = {k: _mae(v) for k, v in preds.items()}
    wape = {k: _wape(v, reales) for k, v in preds.items()}
    n_origenes = len(reales)
    suficiente = n_origenes >= min_origen
    umbral = min(wape["naive"] if wape["naive"] is not None else float("inf"),
                 wape["ma7"] if wape["ma7"] is not None else float("inf"))
    gana = bool(suficiente and wape["modelo"] is not None
                and wape["modelo"] <= umbral)
    return {
        "mae_modelo": mae["modelo"], "mae_naive": mae["naive"], "mae_ma7": mae["ma7"],
        "mape_modelo": wape["modelo"],
        "wape_modelo": wape["modelo"], "wape_naive": wape["naive"],
        "wape_ma7": wape["ma7"],
        "smape_modelo": _smape(preds["modelo"], reales),
        "sesgo_modelo": _sesgo(preds["modelo"], reales),
        "gana": gana, "n": n, "n_origenes": n_origenes,
        "horizonte_medio": sum(horizontes) / len(horizontes) if horizontes else 0.0,
        "horizonte_max": max(horizontes) if horizontes else 0,
        "suficiente": suficiente,
        "motivo": "" if suficiente else f"menos de {min_origen} origenes",
    }


def horizon_growth(ultimo: float, futuro: list[float]) -> float:
    if not futuro or not ultimo:
        return 0.0
    return (futuro[-1] - ultimo) / abs(ultimo)


def product_forecast_share(detail: list[dict], total_30: float, n: int = 5) -> list[dict]:
    """Reparte el total de 30 dias por participacion de ingresos de la misma ventana.

    `detail` debe ser el detalle de los ultimos 30 dias (no todo el historico)
    y `total_30` el total pronosticado para los proximos 30 dias. Asi el
    "crecimiento" compara dos ventanas equivalentes. La suma de `predicho`
    cuadra con `total_30` (se ajusta la fila de mayor participacion).
    """
    if not detail:
        return []
    base = sum(float(d.get("ingresos") or 0) for d in detail)
    objetivo = max(0, int(round(float(total_30 or 0))))
    todos = []
    for d in detail:
        actual = float(d.get("ingresos") or 0)
        share = (actual / base) if base else 0.0
        predicho = int(round(objetivo * share))
        crec = (predicho - actual) / actual * 100.0 if actual else 0.0
        todos.append({"nombre": d["nombre"], "actual": int(round(actual)),
                      "predicho": predicho, "crecimiento": round(crec, 1)})
    if todos and objetivo:
        dif = objetivo - sum(r["predicho"] for r in todos)
        if dif:
            idx = max(range(len(todos)), key=lambda i: todos[i]["actual"])
            todos[idx]["predicho"] += dif
            actual = todos[idx]["actual"]
            todos[idx]["crecimiento"] = (
                round((todos[idx]["predicho"] - actual) / actual * 100.0, 1)
                if actual else 0.0)
    todos.sort(key=lambda r: r["actual"], reverse=True)
    return todos[:n]
