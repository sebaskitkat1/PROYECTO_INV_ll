"""numeros que salen de los dicts, nada a mano.

todas las funciones reciben listas de dicts (las de mock_data o las que
vengan de la base despues) y devuelven cuentas. Sin dependencias nuevas.
"""
from __future__ import annotations

import math


# -- helpers chicos ------------------------------------------------------

def pct_change(nuevo: float, viejo: float) -> float | None:
    if not viejo:
        return None
    return (nuevo - viejo) / abs(viejo) * 100.0


def fmt_money(v: float) -> str:
    return f"${v:,.0f}"


# -- ventas --------------------------------------------------------------

def sales_totals(detail: list[dict]) -> dict:
    ingresos = sum(float(d.get("ingresos") or 0) for d in detail)
    unidades = sum(int(d.get("cantidad") or 0) for d in detail)
    ticket = ingresos / unidades if unidades else 0.0
    margen_pond = 0.0
    if ingresos:
        margen_pond = sum(float(d.get("ingresos") or 0) * float(d.get("margen") or 0) for d in detail) / ingresos
    return {"ingresos": ingresos, "unidades": unidades, "ticket": ticket, "margen_pond": margen_pond}


def top_products(detail: list[dict], n: int = 5) -> list[dict]:
    orden = sorted(detail, key=lambda d: float(d.get("ingresos") or 0), reverse=True)
    return [{"product": d["nombre"], "ingresos": float(d.get("ingresos") or 0)} for d in orden[:n]]


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
        "productos_vendidos": {"valor": f"{tot['unidades']:,}", "delta": None, "positivo": True},
        "stock_en_riesgo": {"valor": str(criticos), "delta": None, "positivo": None},
    }


# -- inventario ----------------------------------------------------------
# una sola funcion pura: estado y dias salen de stock, minimo y consumo.
# no se guardan los derivados. Reglas: stock 0 siempre critico con 0 dias;
# minimo 0 es neutro (sin minimo, fuera de alertas pero visible);
# consumo desconocido o 0 deja dias en None ("—" en la tabla).

SIN_MINIMO = "sin_minimo"

ENTERO_UNIDADES = {"pzas", "bidones"}


def stock_status(stock: float, minimo: float, consumo: float | None) -> tuple[str, float | None]:
    stock = float(stock or 0)
    minimo = float(minimo or 0)
    if stock <= 0:
        return ("critico", 0.0)
    dias = stock / consumo if consumo and consumo > 0 else None
    if minimo <= 0:
        return (SIN_MINIMO, dias)
    if stock < minimo:
        return ("critico", dias)
    if stock < minimo * 1.25:
        return ("advertencia", dias)
    return ("optimo", dias)

def inventory_health(items: list[dict]) -> dict:
    total = len(items)
    crit = [i for i in items if i.get("estado") == "critico"]
    adv = sum(1 for i in items if i.get("estado") == "advertencia")
    opt = sum(1 for i in items if i.get("estado") == "optimo")
    crit_orden = sorted(crit, key=lambda i: int(i.get("diasAgotar") or 0))
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


def reorder_qty(item: dict, objetivo: float = 2.0) -> int:
    falta = float(item.get("stockMinimo") or 0) * objetivo - float(item.get("stockActual") or 0)
    return max(0, math.ceil(falta))


def abc_classes(pareto: list[dict]) -> list[dict]:
    orden = sorted(pareto, key=lambda d: float(d.get("ingresos") or 0), reverse=True)
    total = sum(float(d.get("ingresos") or 0) for d in orden) or 1.0
    acc = 0.0
    out = []
    for d in orden:
        acc += float(d.get("ingresos") or 0)
        pct = acc / total * 100.0
        clase = "A" if len(orden) == 1 or pct <= 80 else ("B" if pct <= 95 else "C")
        out.append({"nombre": d.get("nombre", ""), "ingresos": float(d.get("ingresos") or 0),
                    "acum_pct": pct, "clase": clase})
    return out


# -- pronostico ----------------------------------------------------------
# regresion sobre fecha real (ordinal de la fecha, no posicion).
# nivel = valor ajustado en el ultimo punto: f(1) cae un paso de
# pendiente adelante, sin el sesgo del promedio movil.
# pasos diarios con etiqueta de dias reales. Con 28+ dias se suma
# indice por dia de semana. Backtest rolling-origin contra ingenuo
# y media movil 7: si el modelo no gana, es preliminar.
import datetime as _dt

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
    x0 = xs[0]
    a = nivel - pend * xs[-1]
    por_dia: dict[int, list[float]] = {}
    for f, y in zip(fechas, valores):
        ajustado = a + pend * float(f.toordinal())
        if ajustado > 0 and y is not None:
            por_dia.setdefault(f.weekday(), []).append(float(y) / ajustado)
    factores = {d: (sum(v) / len(v)) for d, v in por_dia.items() if v}
    media = sum(factores.values()) / len(factores) if factores else 1.0
    return {d: f / media for d, f in factores.items()} if media else {}


def forecast_daily(history: list[tuple[_dt.date, float]], steps: int = 30) -> list[tuple[_dt.date, float]]:
    if not history:
        return []
    hist = sorted(history, key=lambda p: p[0])
    fechas = [d for d, _ in hist]
    valores = [float(v) for _, v in hist]
    nivel, pend = fit_trend(fechas, valores)
    dow = dow_factors(fechas, valores)
    ultima = fechas[-1]
    out = []
    for k in range(1, steps + 1):
        f = ultima + _dt.timedelta(days=k)
        v = (nivel + pend * k) * dow.get(f.weekday(), 1.0)
        out.append((f, max(0.0, round(v, -1))))
    return out


def backtest(fechas: list[_dt.date], valores: list[float], min_origen: int = 7) -> dict:
    # rolling-origin a 1 paso: modelo vs ingenuo (ultimo) vs media movil 7
    pares = sorted(zip(fechas, valores), key=lambda p: p[0])
    errs = {"modelo": [], "naive": [], "ma7": []}
    for k in range(min(min_origen, len(pares) - 1), len(pares)):
        tramo = pares[:k]
        real = float(pares[k][1])
        f_tramo = [d for d, _ in tramo]
        v_tramo = [float(v) for _, v in tramo]
        nivel, pend = fit_trend(f_tramo, v_tramo)
        dow = dow_factors(f_tramo, v_tramo)
        meta = pares[k][0]
        errs["modelo"].append(abs((nivel + pend * 1) * dow.get(meta.weekday(), 1.0) - real))
        errs["naive"].append(abs(v_tramo[-1] - real))
        errs["ma7"].append(abs(sum(v_tramo[-7:]) / len(v_tramo[-7:]) - real))
    def _mae(v):
        return sum(v) / len(v) if v else float("inf")
    mae = {k: _mae(v) for k, v in errs.items()}
    media_real = sum(float(v) for _, v in pares) / len(pares) if pares else 0.0
    return {"mae_modelo": mae["modelo"], "mae_naive": mae["naive"], "mae_ma7": mae["ma7"],
            "mape_modelo": (mae["modelo"] / media_real * 100.0) if media_real else 0.0,
            "gana": mae["modelo"] <= min(mae["naive"], mae["ma7"]),
            "n": len(pares)}


def horizon_growth(ultimo: float, futuro: list[float]) -> float:
    if not futuro or not ultimo:
        return 0.0
    return (futuro[-1] - ultimo) / abs(ultimo)


def product_forecast_share(detail: list[dict], total_30: float, n: int = 5) -> list[dict]:
    # reparte el total pronosticado por participacion de ingresos sobre el
    # catalogo completo: la suma cuadra con el total. Se muestran los top n.
    # El margen no reparte nada (sin causalidad).
    # Ojo: "actual" es la cifra base disponible (periodo sin definir en el
    # mock); cuando la base traiga periodo, comparar contra la misma ventana.
    base = sum(float(d.get("ingresos") or 0) for d in detail) or 1.0
    todos = []
    for d in detail:
        actual = float(d.get("ingresos") or 0)
        predicho = max(0, round(total_30 * (actual / base)))
        crec = (predicho - actual) / actual * 100.0 if actual else 0.0
        todos.append({"nombre": d["nombre"], "actual": int(round(actual)),
                      "predicho": int(predicho), "crecimiento": round(crec, 1)})
    todos.sort(key=lambda r: r["actual"], reverse=True)
    return todos[:n]
