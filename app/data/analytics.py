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


def _slope(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if not den:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


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
# nivel = promedio de los ultimos 3, tendencia = pendiente de la recta.
# pronostico_k = nivel + pendiente * k. Simple y honesto con pocos datos.

def forecast_values(history: list[float], steps: int) -> list[float]:
    if not history:
        return [0.0] * steps
    nivel = _mean(history[-3:])
    pendiente = _slope([float(i) for i in range(len(history))], [float(v) for v in history])
    return [max(0.0, round(nivel + pendiente * (k + 1), -1)) for k in range(steps)]


def overall_growth(history: list[float], steps: int) -> float:
    if not history or not history[-1]:
        return 0.0
    fut = forecast_values(history, steps)
    return (fut[-1] - history[-1]) / abs(history[-1])


def product_forecast(detail: list[dict], growth_30: float, n: int = 5) -> list[dict]:
    # reparte el crecimiento global segun margen: mas margen, mas empuje.
    # supuesto de negocio, no magia: esta a la vista en el codigo.
    tot = sales_totals(detail)
    base = tot["margen_pond"] or 1.0
    top = sorted(detail, key=lambda d: float(d.get("ingresos") or 0), reverse=True)[:n]
    out = []
    for d in top:
        actual = float(d.get("ingresos") or 0)
        g = growth_30 * (float(d.get("margen") or 0) / base)
        out.append({"nombre": d["nombre"], "actual": int(round(actual)),
                    "predicho": int(round(actual * (1 + g))), "crecimiento": round(g * 100, 1)})
    return out
