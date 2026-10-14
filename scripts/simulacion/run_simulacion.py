"""Corre la simulacion con-vs-sin app contra la base real.

Uso desde la raiz del repo:  python scripts/simulacion/run_simulacion.py
Guarda graficas en scripts/simulacion/resultados/.
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from app.data import db
from app.data import analytics
from scripts.simulacion import sim_lib

SALIDA = os.path.join(ROOT, "scripts", "simulacion", "resultados")
os.makedirs(SALIDA, exist_ok=True)
RUNS = 200


def demanda_diaria(id_producto, dias=90):
    filas = db.fetchall(
        "SELECT DATE(v.fecha_hora) AS f, SUM(d.cantidad) AS c "
        "FROM detalle_ventas d JOIN ventas v ON v.id_venta = d.id_venta "
        "WHERE v.estado = 'completada' AND d.id_producto = %s "
        "GROUP BY DATE(v.fecha_hora) ORDER BY f DESC LIMIT %s",
        (id_producto, dias))
    filas.sort(key=lambda r: r["f"])
    return [(r["f"], float(r["c"] or 0)) for r in filas]


def main():
    prods = db.fetchall(
        "SELECT p.id_producto, p.nombre, p.precio_venta, p.costo_unitario, "
        "p.vida_anaquel_dias, SUM(d.subtotal) AS ing "
        "FROM detalle_ventas d JOIN ventas v ON v.id_venta = d.id_venta "
        "JOIN productos p ON p.id_producto = d.id_producto "
        "WHERE v.estado = 'completada' GROUP BY p.id_producto ORDER BY ing DESC")
    print(f"{'producto':<18}{'pol':>7}{'MAE mod':>9}{'MAE base':>9}{'merma s/app':>11}{'merma c/app':>11}{'util +':>9}")
    por_fecha: dict = {}
    mc_hecho = False
    for p in prods:
        serie = demanda_diaria(p["id_producto"])
        fechas = [d for d, _ in serie]
        vals = [v for _, v in serie]
        if len(vals) < 28:
            print(f"{p['nombre']:<18} sin historia suficiente ({len(vals)} dias)")
            continue
        wf = sim_lib.walk_forward_weekly(fechas, vals, ndigits=0)
        precio, costo = float(p["precio_venta"]), float(p["costo_unitario"])
        vida = int(p["vida_anaquel_dias"] or 7)
        # pedidos dia a dia sin ver el futuro (calentamiento 21 dias;
        # residuales solo con datos anteriores al dia del pedido)
        dem, pb, pm, fsim = [], [], [], []
        for k in range(21, len(vals)):
            dem.append(vals[k])
            fsim.append(fechas[k])
            pb.append(sim_lib.pedido_base(fechas[:k], vals[:k]))
            h = list(zip(fechas[:k], vals[:k]))
            fut1 = analytics.forecast_daily(h, 1, 0)[0][1]
            res = sim_lib.residuales_rodantes(fechas[:k], vals[:k], ndigits=0)
            pm.append(sim_lib.pedido_newsvendor(fut1, res, precio, costo))
        # seleccion por dinero en la primera mitad; se evalua en la segunda (no vista)
        mid = len(dem) // 2
        c0 = sim_lib.simulate_inventory(dem[:mid], pb[:mid], vida, costo, precio)
        c1 = sim_lib.simulate_inventory(dem[:mid], pm[:mid], vida, costo, precio)
        usa_modelo = c1["utilidad_cierre"] > c0["utilidad_cierre"]
        ev0 = sim_lib.simulate_inventory(dem[mid:], pb[mid:], vida, costo, precio)
        ev1 = sim_lib.simulate_inventory(dem[mid:], pm[mid:] if usa_modelo else pb[mid:],
                                         vida, costo, precio)
        r0 = sim_lib.simulate_inventory(dem, pb, vida, costo, precio)
        r1 = sim_lib.simulate_inventory(dem, pm if usa_modelo else pb, vida, costo, precio)
        print(f"{p['nombre']:<18}{'modelo' if usa_modelo else 'base  ':>7}"
              f"{wf['mae_modelo']:>9.1f}{wf['mae_naive']:>9.1f}"
              f"{ev0['merma']:>11.0f}{ev1['merma']:>11.0f}"
              f"{ev1['utilidad_cierre'] - ev0['utilidad_cierre']:>9.0f}")
        for f, a, b in zip(fsim, r0["filas"], r1["filas"]):
            if f not in por_fecha:
                por_fecha[f] = [0.0, 0.0]
            por_fecha[f][0] += a["eco"]
            por_fecha[f][1] += b["eco"]
        # monte carlo a 30 dias para el primer producto donde el modelo entra
        if usa_modelo and not mc_hecho:
            mc_hecho = True
            fut = analytics.forecast_daily(list(zip(fechas, vals)), 30, 0)
            res_hist = sim_lib.residuales_rodantes(fechas, vals, ndigits=0)
            base_fut = [sim_lib.pedido_base(fechas, vals)] * 30
            if usa_modelo:
                mod_fut = [sim_lib.pedido_newsvendor(f, res_hist, precio, costo)
                           for _, f in fut]
            else:
                mod_fut = list(base_fut)
            mc = sim_lib.monte_carlo(
                [d for d, _ in fut], [v for _, v in fut], res_hist, RUNS,
                vida, float(p["costo_unitario"]), float(p["precio_venta"]),
                base_fut, mod_fut)
            print(f"  MC 30 dias {p['nombre']}: merma -[{mc['merma_p10']:.0f}%, {mc['merma_p90']:.0f}%], "
                  f"util +[${mc['util_media']:.0f} | P10 ${mc['util_p10']:.0f}, P90 ${mc['util_p90']:.0f}]")

    def _acum(xs):
        t, out = 0.0, []
        for x in xs:
            t += x
            out.append(t)
        return out

    orden = sorted(por_fecha)
    base_diaria = [por_fecha[f][0] for f in orden]
    modelo_diaria = [por_fecha[f][1] for f in orden]
    print(f"ventana: {orden[0]} a {orden[-1]} ({len(orden)} dias), "
          f"util sin app ${sum(base_diaria):,.0f}, con app ${sum(modelo_diaria):,.0f}")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(_acum(base_diaria), label="Sin app (misma semana pasada)", linewidth=2)
    ax.plot(_acum(modelo_diaria), label="Con app (pronóstico + colchón)", linewidth=2)
    ax.set_title("Utilidad acumulada: con app vs sin app (top 5, ventana simulada)")
    ax.set_xlabel("día")
    ax.set_ylabel("utilidad acumulada ($)")
    ax.legend(frameon=False)
    fig.tight_layout()
    ruta = os.path.join(SALIDA, "utilidad_acumulada.png")
    fig.savefig(ruta, dpi=110)
    print("grafica:", ruta)


if __name__ == "__main__":
    main()
