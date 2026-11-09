"""Simulacion de un producto en una temporada corta: sin modelo vs con modelo.

La demanda real es la misma en las dos politicas. La unica diferencia es como
se decide el pedido de cada dia:

- sin modelo: se pide lo vendido el mismo dia de la semana pasada;
- con modelo: pronostico a 1 dia + cuantil newsvendor de los residuales.

Ambas politicas ven estrictamente el pasado. El inventario es FIFO y la merma
se valora a costo; la venta perdida se valora a precio de venta.

Uso:
    python scripts/simulacion/run_producto.py
    python scripts/simulacion/run_producto.py --producto "Jugo Verde" --dias 21
    python scripts/simulacion/run_producto.py --producto 15 --dias 28
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from app.data import analytics, db
from app.styles import CHART_GRID, CLAY, INK, MENTA, MUTED, PAPER, VERDE
from scripts.simulacion import sim_lib

SALIDA = ROOT / "scripts" / "simulacion" / "resultados"
GRIS = "#7C8B7A"
DIAS = ["lun", "mar", "mie", "jue", "vie", "sab", "dom"]


def _slug(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", normal.lower()).strip("_") or "producto"


def _producto(ref: str) -> dict:
    sql = ("SELECT id_producto, nombre, precio_venta, costo_unitario, vida_anaquel_dias "
           "FROM productos ")
    if ref.isdigit():
        filas = db.fetchall(sql + "WHERE id_producto = %s", (int(ref),))
    else:
        filas = db.fetchall(sql + "WHERE nombre = %s", (ref,))
        if not filas:
            filas = db.fetchall(sql + "WHERE nombre LIKE %s ORDER BY nombre", (f"%{ref}%",))
    if not filas:
        raise SystemExit(f"no encontre el producto {ref!r}")
    if len(filas) > 1:
        opciones = ", ".join(f"{f['id_producto']}: {f['nombre']}" for f in filas)
        raise SystemExit(f"hay varios productos: {opciones}. Usa el id.")
    p = filas[0]
    return {
        "id": int(p["id_producto"]),
        "nombre": str(p["nombre"]),
        "precio": float(p["precio_venta"]),
        "costo": float(p["costo_unitario"]),
        "vida": int(p["vida_anaquel_dias"] or 7),
    }


def _serie(pid: int) -> list[tuple[dt.date, float]]:
    """Demanda diaria completa: la base solo guarda dias con venta, los
    huecos se completan con 0 para que la semana pasada cuadre."""
    filas = db.fetchall(
        "SELECT DATE(v.fecha_hora) AS f, SUM(d.cantidad) AS c "
        "FROM detalle_ventas d JOIN ventas v ON v.id_venta = d.id_venta "
        "WHERE v.estado = 'completada' AND d.id_producto = %s "
        "GROUP BY DATE(v.fecha_hora) ORDER BY f",
        (pid,))
    if not filas:
        raise SystemExit("el producto no tiene ventas completadas")
    real: dict[dt.date, float] = {}
    for r in filas:
        fecha = r["f"]
        if isinstance(fecha, dt.datetime):
            fecha = fecha.date()
        real[fecha] = float(r["c"] or 0)
    ini, fin = min(real), max(real)
    dias = (fin - ini).days + 1
    return [(ini + dt.timedelta(days=i), real.get(ini + dt.timedelta(days=i), 0.0))
            for i in range(dias)]


def _pedidos(serie: list[tuple[dt.date, float]], inicio: int,
             precio: float, costo: float) -> list[dict]:
    filas = []
    for k in range(inicio, len(serie)):
        hist = serie[:k]
        fechas = [d for d, _ in hist]
        vals = [v for _, v in hist]
        base = sim_lib.pedido_base(fechas, vals)
        pron = analytics.forecast_daily(list(zip(fechas, vals)), 1, 0)[0][1]
        res = sim_lib.residuales_rodantes(fechas, vals, ndigits=0)
        modelo = sim_lib.pedido_newsvendor(pron, res, precio, costo)
        filas.append({
            "fecha": serie[k][0],
            "demanda": serie[k][1],
            "pedido_base": base,
            "pedido_modelo": modelo,
            "pronostico": pron,
        })
    return filas


def _acum(valores) -> list[float]:
    total, out = 0.0, []
    for valor in valores:
        total += float(valor)
        out.append(total)
    return out


def _resumen(pedidos: list[dict], resultado: dict, clave: str,
             precio: float, costo: float) -> dict:
    demanda = sum(f["demanda"] for f in pedidos)
    merma_mxn = resultado["merma"] * costo
    sobrante_mxn = resultado["inv_final"] * costo
    return {
        "demanda": demanda,
        "pedido": sum(f[clave] for f in pedidos),
        "vendido": resultado["vendido"],
        "merma_u": resultado["merma"],
        "merma_mxn": merma_mxn,
        "sobrante_u": resultado["inv_final"],
        "sobrante_mxn": sobrante_mxn,
        "merma_total_mxn": merma_mxn + sobrante_mxn,
        "perdidas_u": resultado["perdidas"],
        "perdidas_mxn": resultado["perdidas"] * precio,
        "utilidad_caja": resultado["utilidad"],
        "utilidad_cierre": resultado["utilidad_cierre"],
        "cumplimiento": (resultado["vendido"] / demanda * 100.0) if demanda else 100.0,
    }


def _money(valor: float, signo: bool = False) -> str:
    texto = f"${abs(valor):,.0f}"
    if signo:
        return ("+" if valor >= 0 else "-") + texto
    return ("-" if valor < 0 else "") + texto


def _pct(delta: float, base: float) -> str:
    if not base:
        return "n/a"
    return f"{delta / abs(base) * 100.0:+.1f}%"


def _imprimir(p: dict, pedidos: list[dict], sin: dict, con: dict) -> None:
    fechas = [f["fecha"] for f in pedidos]
    print(f"\nProducto: {p['nombre']} (id {p['id']})  |  vida de anaquel: {p['vida']} dias  |  "
          f"precio: ${p['precio']:,.2f}  |  costo: ${p['costo']:,.2f}")
    print(f"Temporada: {fechas[0]:%Y-%m-%d} a {fechas[-1]:%Y-%m-%d}  "
          f"({len(fechas)} dias)  |  demanda real: {sin['demanda']:,.1f} u")
    print()
    print(f"{'Concepto':<27}{'Sin modelo':>14}{'Con modelo':>14}  {'Diferencia':>17}")
    print("-" * 74)
    filas = [
        ("Pedido (u)", sin["pedido"], con["pedido"], False),
        ("Vendido (u)", sin["vendido"], con["vendido"], False),
        ("Merma temporada (u)", sin["merma_u"], con["merma_u"], False),
        ("Merma temporada ($)", sin["merma_mxn"], con["merma_mxn"], True),
        ("Sobrante final (u)", sin["sobrante_u"], con["sobrante_u"], False),
        ("Sobrante final ($)", sin["sobrante_mxn"], con["sobrante_mxn"], True),
        ("Merma total ($)", sin["merma_total_mxn"], con["merma_total_mxn"], True),
        ("Venta perdida (u)", sin["perdidas_u"], con["perdidas_u"], False),
        ("Venta perdida ($)", sin["perdidas_mxn"], con["perdidas_mxn"], True),
        ("Utilidad de caja ($)", sin["utilidad_caja"], con["utilidad_caja"], True),
        ("Utilidad con sobrante ($)", sin["utilidad_cierre"], con["utilidad_cierre"], True),
        ("Cumplimiento demanda", sin["cumplimiento"], con["cumplimiento"], False),
    ]
    for nombre, base, modelo, dinero in filas:
        delta = modelo - base
        if nombre == "Cumplimiento demanda":
            txt_base, txt_mod = f"{base:.1f}%", f"{modelo:.1f}%"
            txt_delta = f"{delta:+.1f} pp"
        elif dinero:
            txt_base, txt_mod = _money(base), _money(modelo)
            txt_delta = f"{_money(delta, signo=True)} ({_pct(delta, base)})"
        else:
            txt_base, txt_mod = f"{base:,.1f}", f"{modelo:,.1f}"
            txt_delta = f"{delta:+,.1f} ({_pct(delta, base)})"
        print(f"{nombre:<27}{txt_base:>14}{txt_mod:>14}  {txt_delta:>17}")
    print("-" * 74)
    ahorro_merma = sin["merma_total_mxn"] - con["merma_total_mxn"]
    ahorro_perdida = sin["perdidas_mxn"] - con["perdidas_mxn"]
    delta_util = con["utilidad_caja"] - sin["utilidad_caja"]
    if ahorro_merma >= 0:
        txt_merma = f"Merma total evitada: {_money(ahorro_merma)}."
    else:
        txt_merma = f"Merma total extra: {_money(-ahorro_merma)}."
    if ahorro_perdida >= 0:
        txt_perdida = f"Venta perdida evitada: {_money(ahorro_perdida)}."
    else:
        txt_perdida = f"Venta perdida extra: {_money(-ahorro_perdida)}."
    print(f"Utilidad de caja: {_money(delta_util, signo=True)} "
          f"({_pct(delta_util, sin['utilidad_caja'])}). {txt_merma} {txt_perdida}")
    print(f"Referencia: si el sobrante final se valora a costo, la utilidad sería "
          f"{_money(sin['utilidad_cierre'])} vs {_money(con['utilidad_cierre'])}.")
    if delta_util > 0:
        print("Resultado: en esta temporada el modelo supera a la regla actual "
              "incluso sin acreditar el sobrante final.")
    elif delta_util < 0:
        print("Resultado: en esta temporada el modelo NO supera a la regla actual "
              "si el sobrante final no vale; revisa el producto/ventana antes de presentarlo.")
    else:
        print("Resultado: empate en utilidad de caja; revisa merma y venta perdida.")


def _csv(p: dict, pedidos: list[dict], rb: dict, rm: dict, ruta: Path) -> None:
    columnas = [
        "fecha", "dia", "demanda_u",
        "pedido_sin_modelo_u", "pedido_con_modelo_u",
        "vendido_sin_modelo_u", "vendido_con_modelo_u",
        "merma_sin_modelo_u", "merma_con_modelo_u",
        "merma_sin_modelo_mxn", "merma_con_modelo_mxn",
        "venta_perdida_sin_modelo_u", "venta_perdida_con_modelo_u",
        "venta_perdida_sin_modelo_mxn", "venta_perdida_con_modelo_mxn",
        "utilidad_caja_dia_sin_modelo_mxn", "utilidad_caja_dia_con_modelo_mxn",
        "utilidad_caja_acum_sin_modelo_mxn", "utilidad_caja_acum_con_modelo_mxn",
    ]
    acum_b = acum_m = 0.0
    with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=columnas)
        writer.writeheader()
        for f, fb, fm in zip(pedidos, rb["filas"], rm["filas"]):
            acum_b += fb["utilidad"]
            acum_m += fm["utilidad"]
            writer.writerow({
                "fecha": f["fecha"].isoformat(),
                "dia": DIAS[f["fecha"].weekday()],
                "demanda_u": round(f["demanda"], 2),
                "pedido_sin_modelo_u": round(f["pedido_base"], 2),
                "pedido_con_modelo_u": round(f["pedido_modelo"], 2),
                "vendido_sin_modelo_u": round(fb["vendido"], 2),
                "vendido_con_modelo_u": round(fm["vendido"], 2),
                "merma_sin_modelo_u": round(fb["merma"], 2),
                "merma_con_modelo_u": round(fm["merma"], 2),
                "merma_sin_modelo_mxn": round(fb["merma"] * p["costo"], 2),
                "merma_con_modelo_mxn": round(fm["merma"] * p["costo"], 2),
                "venta_perdida_sin_modelo_u": round(fb["perdidas"], 2),
                "venta_perdida_con_modelo_u": round(fm["perdidas"], 2),
                "venta_perdida_sin_modelo_mxn": round(fb["perdidas"] * p["precio"], 2),
                "venta_perdida_con_modelo_mxn": round(fm["perdidas"] * p["precio"], 2),
                "utilidad_caja_dia_sin_modelo_mxn": round(fb["utilidad"], 2),
                "utilidad_caja_dia_con_modelo_mxn": round(fm["utilidad"], 2),
                "utilidad_caja_acum_sin_modelo_mxn": round(acum_b, 2),
                "utilidad_caja_acum_con_modelo_mxn": round(acum_m, 2),
            })


def _csv_resumen(sin: dict, con: dict, ruta: Path) -> None:
    columnas = [
        "politica", "pedido_u", "vendido_u",
        "merma_temporada_u", "merma_temporada_mxn",
        "sobrante_final_u", "sobrante_final_mxn", "merma_total_mxn",
        "venta_perdida_u", "venta_perdida_mxn",
        "utilidad_caja_mxn", "utilidad_con_sobrante_mxn", "cumplimiento_pct",
    ]
    with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=columnas)
        writer.writeheader()
        for nombre, datos in (("Sin modelo", sin), ("Con modelo", con)):
            writer.writerow({
                "politica": nombre,
                "pedido_u": round(datos["pedido"], 2),
                "vendido_u": round(datos["vendido"], 2),
                "merma_temporada_u": round(datos["merma_u"], 2),
                "merma_temporada_mxn": round(datos["merma_mxn"], 2),
                "sobrante_final_u": round(datos["sobrante_u"], 2),
                "sobrante_final_mxn": round(datos["sobrante_mxn"], 2),
                "merma_total_mxn": round(datos["merma_total_mxn"], 2),
                "venta_perdida_u": round(datos["perdidas_u"], 2),
                "venta_perdida_mxn": round(datos["perdidas_mxn"], 2),
                "utilidad_caja_mxn": round(datos["utilidad_caja"], 2),
                "utilidad_con_sobrante_mxn": round(datos["utilidad_cierre"], 2),
                "cumplimiento_pct": round(datos["cumplimiento"], 2),
            })


def _linea(ax, x, base, modelo, titulo, fechas, menor_es_mejor: bool = False,
           permitir_negativos: bool = False, texto_cero: str = "") -> None:
    ax.plot(x, base, color=GRIS, lw=2.0, ls="--")
    ax.plot(x, modelo, color=VERDE, lw=2.4)
    if len(x) > 1:
        mejor = [m <= b for b, m in zip(base, modelo)] if menor_es_mejor else \
                [m >= b for b, m in zip(base, modelo)]
        ax.fill_between(x, base, modelo, where=mejor, color=MENTA, alpha=0.18, interpolate=True)
        ax.fill_between(x, base, modelo, where=[not v for v in mejor], color=CLAY, alpha=0.10,
                        interpolate=True)
    ax.set_title(titulo, fontsize=11, fontweight="bold", loc="left", color=INK)
    ax.grid(axis="y", color=CHART_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _money(v)))
    maximo_datos = max(max(base), max(modelo))
    minimo_datos = min(min(base), min(modelo))
    if maximo_datos <= 1e-9 and minimo_datos >= -1e-9:
        ax.set_ylim(0, 1)
        ax.set_yticks([0])
        ax.set_yticklabels(["$0"])
        if texto_cero:
            ax.text(0.5, 0.5, texto_cero, transform=ax.transAxes, ha="center",
                    va="center", color=MUTED, fontsize=10)
    elif permitir_negativos:
        minimo = min(0.0, min(base), min(modelo))
        maximo = max(0.0, max(base), max(modelo))
        margen = max((maximo - minimo) * 0.08, 1.0)
        ax.set_ylim(minimo - margen, maximo + margen)
        ax.axhline(0, color=CHART_GRID, lw=0.8, zorder=1)
    else:
        ax.set_ylim(bottom=0)
    # etiquetas finales a la derecha del ultimo punto, con separacion minima
    # en puntos para que no se encimen aunque los valores finales sean iguales.
    if abs(base[-1]) < 1e-9 and abs(modelo[-1]) < 1e-9:
        ax.annotate("$0", xy=(x[-1], 0), xytext=(4, 8), textcoords="offset points",
                    ha="left", color=VERDE, fontsize=8, fontweight="bold")
    else:
        y_base_px = ax.transData.transform((x[-1], base[-1]))[1]
        y_mod_px = ax.transData.transform((x[-1], modelo[-1]))[1]
        separacion = abs(y_base_px - y_mod_px) * 72.0 / ax.figure.dpi
        empuje = max(0.0, (14.0 - separacion) / 2.0)
        if modelo[-1] >= base[-1]:
            offset_base, offset_modelo = (4, -empuje), (4, empuje)
        else:
            offset_base, offset_modelo = (4, empuje), (4, -empuje)
        # si un valor final es cero, su etiqueta va arriba para no pisar el eje
        if abs(base[-1]) < 1e-9:
            offset_base = (4, 4)
        if abs(modelo[-1]) < 1e-9:
            offset_modelo = (4, 4)
        ax.annotate(_money(base[-1]), xy=(x[-1], base[-1]), xytext=offset_base,
                    textcoords="offset points", ha="left", va="center", color=GRIS,
                    fontsize=8, fontweight="bold")
        ax.annotate(_money(modelo[-1]), xy=(x[-1], modelo[-1]), xytext=offset_modelo,
                    textcoords="offset points", ha="left", va="center", color=VERDE,
                    fontsize=8, fontweight="bold")
    paso = max(1, len(x) // 5)
    ticks = list(range(0, len(x), paso))
    if ticks[-1] != len(x) - 1:
        # si la ultima fecha queda pegada al tick anterior, se reemplaza
        # en vez de agregarla, para que las etiquetas no se encimen.
        if len(ticks) > 1 and len(x) - 1 - ticks[-1] < paso * 0.6:
            ticks[-1] = len(x) - 1
        else:
            ticks.append(len(x) - 1)
    ax.set_xticks(ticks)
    ax.set_xticklabels([fechas[i].strftime("%d/%m") for i in ticks], fontsize=8)
    if len(x) > 1:
        # margen derecho para las etiquetas de los valores finales
        ax.set_xlim(0, len(x) - 1 + 2.8)


def _barras(ax, titulo: str, base: float, modelo: float, menor_es_mejor: bool = False) -> None:
    barras = ax.bar([0, 1], [base, modelo], color=[GRIS, VERDE], width=0.55)
    ax.set_title(titulo, fontsize=11, fontweight="bold", loc="left", color=INK)
    ax.set_xticks([0, 1], ["Sin modelo", "Con modelo"], fontsize=9)
    ax.grid(axis="y", color=CHART_GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _money(v)))
    minimo = min(0.0, base, modelo)
    maximo = max(0.0, base, modelo, 1.0)
    rango = max(maximo - minimo, 1.0)
    ax.set_ylim(minimo - (0.05 * rango if minimo < 0 else 0), maximo + 0.35 * rango)
    if minimo < 0:
        ax.axhline(0, color=CHART_GRID, lw=0.8, zorder=1)
    for barra, valor in zip(barras, [base, modelo]):
        offset = 3 if valor >= 0 else -12
        alineacion = "bottom" if valor >= 0 else "top"
        ax.annotate(_money(valor), xy=(barra.get_x() + barra.get_width() / 2, valor),
                    xytext=(0, offset), textcoords="offset points", ha="center",
                    va=alineacion, fontsize=9, fontweight="bold", color=INK)
    delta = modelo - base
    bueno = delta <= 0 if menor_es_mejor else delta >= 0
    color = MENTA if bueno else CLAY
    texto = f"{_money(delta, signo=True)}"
    if base:
        texto += f"  ({_pct(delta, base)})"
    ax.annotate(texto, xy=(0.5, 0.94), xycoords="axes fraction", ha="center", fontsize=9,
                color=color, fontweight="bold")


def _grafica(p: dict, pedidos: list[dict], rb: dict, rm: dict, ruta: Path) -> None:
    fechas = [f["fecha"] for f in pedidos]
    x = list(range(len(fechas)))
    util_b = _acum(f["utilidad"] for f in rb["filas"])
    util_m = _acum(f["utilidad"] for f in rm["filas"])
    merma_b = _acum(f["merma"] * p["costo"] for f in rb["filas"])
    merma_m = _acum(f["merma"] * p["costo"] for f in rm["filas"])
    perd_b = _acum(f["perdidas"] * p["precio"] for f in rb["filas"])
    perd_m = _acum(f["perdidas"] * p["precio"] for f in rm["filas"])

    fig, axes = plt.subplots(2, 3, figsize=(14, 8.4), facecolor=PAPER)
    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.07, right=0.98,
                        hspace=0.45, wspace=0.28)
    fig.suptitle(f"{p['nombre']} · temporada de {len(fechas)} días",
                 fontsize=16, fontweight="bold", color=INK, x=0.07, ha="left", y=0.965)
    fig.text(0.07, 0.915,
             f"{fechas[0]:%d/%m/%Y} a {fechas[-1]:%d/%m/%Y}  ·  vida de anaquel {p['vida']} días  ·  "
             f"precio \\${p['precio']:,.2f}  ·  costo \\${p['costo']:,.2f}",
             fontsize=9.5, color=MUTED, ha="left")
    handles = [Line2D([0], [0], color=GRIS, lw=2, ls="--"),
               Line2D([0], [0], color=VERDE, lw=2.4)]
    fig.legend(handles, ["Sin modelo (misma semana pasada)", "Con modelo (pronóstico + newsvendor)"],
               loc="upper right", bbox_to_anchor=(0.98, 0.955), ncol=2, frameon=False,
               fontsize=9)

    _linea(axes[0, 0], x, util_b, util_m, "Utilidad de caja acumulada", fechas,
           permitir_negativos=True, texto_cero="Sin utilidad en la temporada")
    _linea(axes[0, 1], x, merma_b, merma_m, "Merma de temporada acumulada ($)", fechas,
           menor_es_mejor=True, texto_cero="Sin merma en la temporada")
    _linea(axes[0, 2], x, perd_b, perd_m, "Venta perdida acumulada ($)", fechas,
           menor_es_mejor=True, texto_cero="Sin venta perdida en la temporada")

    sin = _resumen(pedidos, rb, "pedido_base", p["precio"], p["costo"])
    con = _resumen(pedidos, rm, "pedido_modelo", p["precio"], p["costo"])
    _barras(axes[1, 0], "Utilidad de caja", sin["utilidad_caja"], con["utilidad_caja"])
    _barras(axes[1, 1], "Merma total (temporada + sobrante)", sin["merma_total_mxn"],
            con["merma_total_mxn"], menor_es_mejor=True)
    _barras(axes[1, 2], "Venta perdida total ($)", sin["perdidas_mxn"], con["perdidas_mxn"],
            menor_es_mejor=True)

    fig.text(0.07, 0.025,
             "Utilidad de caja = ventas - compras; no acredita el sobrante final. "
             "Merma total = caducado en la temporada + sobrante final a costo.\n"
             "Si el sobrante se vende después, la utilidad sube. Datos demo sintéticos: "
             "validan la metodología, no garantizan superioridad.",
             fontsize=8, color=MUTED, ha="left", linespacing=1.3)
    fig.savefig(ruta, dpi=140, facecolor=PAPER)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulacion con-vs-sin modelo para un producto.")
    parser.add_argument("--producto", default="Jugo Verde",
                        help="nombre o id del producto (default: Jugo Verde)")
    parser.add_argument("--dias", type=int, default=21,
                        help="dias de la temporada a evaluar (default: 21)")
    parser.add_argument("--calentamiento", type=int, default=21,
                        help="dias de historia antes de la temporada (default: 21)")
    args = parser.parse_args()
    if args.dias < 2:
        raise SystemExit("--dias debe ser al menos 2")
    if args.calentamiento < 7:
        raise SystemExit("--calentamiento debe ser al menos 7")

    try:
        p = _producto(args.producto)
        serie = _serie(p["id"])
    except db.DBError as exc:
        raise SystemExit(f"sin base de datos: {exc}") from exc
    if len(serie) < args.calentamiento + args.dias:
        raise SystemExit(
            f"hay {len(serie)} dias de historia y se necesitan al menos "
            f"{args.calentamiento + args.dias} (calentamiento + temporada). "
            "Baja --dias o --calentamiento.")
    inicio = len(serie) - args.dias
    if inicio < args.calentamiento:
        raise SystemExit("no hay suficiente historia antes de la temporada")

    pedidos = _pedidos(serie, inicio, p["precio"], p["costo"])
    rb = sim_lib.simulate_inventory([f["demanda"] for f in pedidos],
                                    [f["pedido_base"] for f in pedidos],
                                    p["vida"], p["costo"], p["precio"])
    rm = sim_lib.simulate_inventory([f["demanda"] for f in pedidos],
                                    [f["pedido_modelo"] for f in pedidos],
                                    p["vida"], p["costo"], p["precio"])
    sin = _resumen(pedidos, rb, "pedido_base", p["precio"], p["costo"])
    con = _resumen(pedidos, rm, "pedido_modelo", p["precio"], p["costo"])
    _imprimir(p, pedidos, sin, con)

    SALIDA.mkdir(parents=True, exist_ok=True)
    base = f"{_slug(p['nombre'])}_{len(pedidos)}d"
    ruta_png = SALIDA / f"{base}.png"
    ruta_csv = SALIDA / f"{base}.csv"
    ruta_resumen = SALIDA / f"{base}_resumen.csv"
    _grafica(p, pedidos, rb, rm, ruta_png)
    _csv(p, pedidos, rb, rm, ruta_csv)
    _csv_resumen(sin, con, ruta_resumen)
    print(f"\nGrafica: {ruta_png}")
    print(f"Detalle diario: {ruta_csv}")
    print(f"Resumen: {ruta_resumen}")


if __name__ == "__main__":
    main()
