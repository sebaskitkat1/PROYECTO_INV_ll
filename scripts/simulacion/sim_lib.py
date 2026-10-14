"""Nucleo de la simulacion con-vs-sin app. Solo stdlib.

Supuestos (declarados, no escondidos):
- compra matutina: el pedido de hoy se vende hoy (lead time 0).
- se vende lo mas viejo primero (FIFO); lo que cumple vida_util se tira.
- sin sustitucion: si no hay fresa, esa venta se pierde completa.
- la merma se valora a costo, la venta perdida a precio lleno.
- el ruido de Monte Carlo sale de residuales reales por dia de semana.
"""
from __future__ import annotations

import datetime as dt
import random
import statistics

from app.data import analytics


# -- walk-forward semanal ------------------------------------------------

def walk_forward_weekly(fechas, valores, min_train=21, horizonte=7, ndigits=-1) -> dict:
    pares = sorted(zip(fechas, valores), key=lambda p: p[0])
    errs = {"modelo": [], "naive": [], "ma7": []}
    residuales: dict[int, list[float]] = {}
    origenes = 0
    k = min_train
    while k + horizonte <= len(pares):
        tramo = pares[:k]
        f_tramo = [d for d, _ in tramo]
        v_tramo = [float(v) for _, v in tramo]
        fut = analytics.forecast_daily(list(zip(f_tramo, v_tramo)), horizonte, ndigits)
        fut_val = [v for _, v in fut]
        for i in range(horizonte):
            meta_fecha, real = pares[k + i][0], float(pares[k + i][1])
            # ingenua estacional: mismo dia de la semana pasada (o ultimo dato)
            ref = None
            for j in range(k - 1, -1, -1):
                if pares[j][0].weekday() == meta_fecha.weekday():
                    ref = float(pares[j][1])
                    break
            naive = ref if ref is not None else v_tramo[-1]
            ma7 = sum(v_tramo[-7:]) / len(v_tramo[-7:])
            errs["modelo"].append(abs(fut_val[i] - real))
            errs["naive"].append(abs(naive - real))
            errs["ma7"].append(abs(ma7 - real))
            residuales.setdefault(meta_fecha.weekday(), []).append(fut_val[i] - real)
        origenes += 1
        k += horizonte
    def _mae(v):
        return sum(v) / len(v) if v else float("inf")
    mae = {n: _mae(v) for n, v in errs.items()}
    media = sum(float(v) for _, v in pares) / len(pares) if pares else 0.0
    return {"mae_modelo": mae["modelo"], "mae_naive": mae["naive"], "mae_ma7": mae["ma7"],
            "mape_modelo": (mae["modelo"] / media * 100.0) if media else 0.0,
            "gana": mae["modelo"] <= min(mae["naive"], mae["ma7"]),
            "residuales": residuales, "origenes": origenes}


def percentil(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0.0
    pos = (len(xs) - 1) * q
    base = int(pos)
    resto = pos - base
    return xs[base] if base + 1 >= len(xs) else xs[base] + resto * (xs[base + 1] - xs[base])


# -- politicas de pedido (un numero por dia, sin ver el futuro) ----------

def pedido_base(fechas_hist, vals_hist):
    # lo que haria el dueno sin app: lo del mismo dia de la semana pasada
    if len(vals_hist) >= 8:
        return max(0.0, float(vals_hist[-8]))
    return max(0.0, sum(vals_hist) / len(vals_hist)) if vals_hist else 0.0


def cuantil_servicio(precio, costo):
    # newsvendor: Cu = margen perdido, Co = costo tirado; pedir el cuantil
    # Cu/(Cu+Co) de la demanda. Caro y perecedero -> se pide conservador.
    if precio <= 0:
        return 0.5
    return max(0.0, min(1.0, (precio - costo) / precio))


def pedido_newsvendor(pron_1dia, residuales, precio, costo):
    todos = [e for v in residuales.values() for e in v]
    ajuste = percentil(todos, cuantil_servicio(precio, costo)) if todos else 0.0
    return max(0.0, pron_1dia + ajuste)


def residuales_rodantes(fechas_hist, vals_hist, ventana=20, ndigits=-1):
    # errores a 1 paso sobre los ultimos dias, todo estrictamente pasado
    pares = sorted(zip(fechas_hist, vals_hist), key=lambda p: p[0])
    out = {}
    inicio = max(1, len(pares) - ventana)
    for k in range(inicio, len(pares)):
        tramo = pares[:k]
        fut = analytics.forecast_daily([(d, float(v)) for d, v in tramo], 1, ndigits)
        err = fut[0][1] - float(pares[k][1])
        out.setdefault(pares[k][0].weekday(), []).append(err)
    return out


def pedido_modelo(fechas_hist, vals_hist, seguridad):
    # pronostico a 1 dia + colchon fijo (solo referencia, no usar en perecederos)
    if not vals_hist:
        return 0.0
    fut = analytics.forecast_daily(list(zip(fechas_hist, vals_hist)), 1, 0)
    return max(0.0, fut[0][1] + seguridad)


# -- inventario FIFO con caducidad ---------------------------------------

def simulate_inventory(demanda, pedido, vida, costo, precio):
    assert len(demanda) == len(pedido)
    lotes = []  # [cantidad, edad], el primero es el mas viejo
    filas, tv, tm, tp, tu = [], 0.0, 0.0, 0.0, 0.0
    inv_antes = 0.0
    for dem, ped in zip(demanda, pedido):
        dem, ped = max(0.0, float(dem)), max(0.0, float(ped))
        if ped > 0:
            lotes.append([ped, 0])
        falta, vendido = dem, 0.0
        for lote in lotes:
            v = min(lote[0], falta)
            lote[0] -= v
            falta -= v
            vendido += v
            if falta <= 0:
                break
        perdidas = dem - vendido
        merma = sum(q for q, e in lotes if e + 1 >= vida)
        lotes = [[q, e + 1] for q, e in lotes if e + 1 < vida and q > 0]
        utilidad = vendido * precio - ped * costo
        inv_val = sum(q for q, _ in lotes) * costo
        eco = utilidad + (inv_val - inv_antes)  # flujo + cambio de inventario
        inv_antes = inv_val
        tv += vendido
        tm += merma
        tp += perdidas
        tu += utilidad
        filas.append({"vendido": vendido, "merma": merma, "perdidas": perdidas,
                      "utilidad": utilidad, "eco": eco, "util_acum": tu})
    inv_final = sum(q for q, _ in lotes)
    return {"filas": filas, "vendido": tv, "merma": tm, "perdidas": tp, "utilidad": tu,
            "inv_final": inv_final, "utilidad_cierre": tu + inv_final * costo}


# -- monte carlo con ruido por dia de semana ------------------------------

def monte_carlo(fechas_fut, pron_fut, residuales, runs, vida, costo, precio,
                pedido_base_fut, pedido_modelo_fut, seed=7):
    rng = random.Random(seed)
    base = list(pedido_base_fut)
    mod = list(pedido_modelo_fut)
    gains_merma, gains_util = [], []
    for _ in range(runs):
        dem = [max(0.0, round(f + rng.choice(residuales.get(d.weekday(), [0.0]))))
               for d, f in zip(fechas_fut, pron_fut)]
        r0 = simulate_inventory(dem, base, vida, costo, precio)
        r1 = simulate_inventory(dem, mod, vida, costo, precio)
        gains_merma.append((r0["merma"] - r1["merma"]) / r0["merma"] * 100.0 if r0["merma"] else 0.0)
        gains_util.append(r1["utilidad_cierre"] - r0["utilidad_cierre"])
    return {"merma_p10": percentil(gains_merma, 0.1), "merma_p90": percentil(gains_merma, 0.9),
            "util_media": statistics.mean(gains_util) if gains_util else 0.0,
            "util_p10": percentil(gains_util, 0.1), "util_p90": percentil(gains_util, 0.9)}
