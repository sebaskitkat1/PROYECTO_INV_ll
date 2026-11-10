#!/usr/bin/env python3
"""Cajero automatico diario para Cosecha (fruteria).

Simula la operacion diaria de la caja para alimentar el modelo de DA:
  1. Reabastece inventario recibiendo ordenes pendientes del dia anterior.
  2. Simula ventas (tickets) con productos aleatorios de la caja.
  3. Genera ordenes de compra para reponer stock bajo (sp_generar_ordenes_compra).
  4. Recibe las ordenes generadas y repone el inventario (sp_recibir_orden_compra).

Uso:
  python scripts/cajero_diario.py                  # un dia, ~30 tickets
  python scripts/cajero_diario.py --tickets 50
  python scripts/cajero_diario.py --seed 42 --tickets 20
  python scripts/cajero_diario.py --dry-run        # no escribe en la base
  python scripts/cajero_diario.py --force          # repite aunque ya haya ventas hoy

Por defecto no corre dos veces el mismo dia: el login y la tarea de las 08:00
no duplican tickets. Las ventas quedan marcadas con origen='simulado'.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db, repository

# Usuario cajero por defecto (Cajero Demo, id_rol=3).
DEFAULT_USER_ID = 2
# Las ordenes de compra y la purga son gestion: usuario Administrador.
ADMIN_USER_ID = 1
# Productos por ticket (min, max).
ITEMS_POR_TICKET = (1, 4)
# Cantidades tipicas por unidad.
CANTIDADES_KG_L = (0.25, 0.5, 0.5, 1.0, 1.0, 1.5, 2.0)
CANTIDADES_PZAS = (1, 1, 2, 2, 3)


def _recibir_pendientes() -> int:
    recibidas = 0
    try:
        ordenes = repository.purchase_orders(200)
    except Exception as exc:  # noqa: BLE001
        print(f"  [aviso] no se pudieron listar ordenes: {exc}")
        return 0
    for o in ordenes:
        if o.get("estado") in ("borrador", "enviada"):
            try:
                repository.receive_purchase_order(int(o["id_orden"]), ADMIN_USER_ID)
                recibidas += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  [aviso] orden #{o['id_orden']} no recibida: {exc}")
    return recibidas


def _simular_ventas(tickets: int, rng: random.Random, dry_run: bool) -> tuple[int, int]:
    ok = 0
    fail = 0
    if dry_run:
        return tickets, 0
    try:
        productos = repository.pos_products()
        metodos = [m["id"] for m in repository.pos_payment_methods()]
    except Exception as exc:  # noqa: BLE001
        print(f"  [error] no se pudo cargar catalogo: {exc}")
        return 0, tickets

    if not productos or not metodos:
        print("  [error] catalogo o metodos de pago vacios.")
        return 0, tickets

    for i in range(tickets):
        n_items = rng.randint(*ITEMS_POR_TICKET)
        elegidos = rng.sample(productos, min(n_items, len(productos)))
        items = []
        for p in elegidos:
            if p.get("unidad") in ("kg", "L"):
                qty = rng.choice(CANTIDADES_KG_L)
            else:
                qty = rng.choice(CANTIDADES_PZAS)
            items.append({"id_producto": int(p["id_producto"]), "cantidad": qty})

        metodo = rng.choice(metodos)
        try:
            repository.register_sale(items, int(metodo), DEFAULT_USER_ID,
                                     origen="simulado")
            ok += 1
        except Exception:  # noqa: BLE001
            # Reintentar una vez tras reponer inventario.
            _recibir_pendientes()
            try:
                repository.register_sale(items, int(metodo), DEFAULT_USER_ID,
                                         origen="simulado")
                ok += 1
            except Exception as exc2:  # noqa: BLE001
                fail += 1
                if fail <= 5:
                    print(f"  [venta {i + 1}] fallida: {exc2}")
    return ok, fail


def _generar_ordenes(dry_run: bool) -> int:
    if dry_run:
        return 0
    try:
        return int(repository.generate_purchase_orders(ADMIN_USER_ID))
    except Exception as exc:  # noqa: BLE001
        print(f"  [aviso] generar ordenes: {exc}")
        return 0


def _ya_corrio_hoy() -> bool:
    """Evita que el login y la tarea de las 08:00 dupliquen la corrida."""
    try:
        filas = db.fetchall(
            "SELECT COUNT(*) AS n FROM ventas "
            "WHERE DATE(fecha_hora) = CURDATE() AND origen = 'simulado'")
        return bool(filas and int(filas[0]["n"] or 0) > 0)
    except Exception as exc:  # noqa: BLE001
        print(f"  [aviso] no se pudo verificar la corrida diaria: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Cajero automatico diario - Cosecha")
    parser.add_argument("--tickets", type=int, default=30, help="numero de tickets a simular (default 30)")
    parser.add_argument("--seed", type=int, default=None, help="semilla para reproducibilidad")
    parser.add_argument("--dry-run", action="store_true", help="no escribe en la base")
    parser.add_argument("--force", action="store_true", help="repite la corrida aunque ya haya ventas hoy")
    args = parser.parse_args()

    rng = random.Random(args.seed if args.seed is not None else random.randrange(10**9))

    inicio = datetime.now()
    print("=" * 60)
    print(f"Cajero diario Cosecha - {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"tickets={args.tickets} seed={args.seed} dry_run={args.dry_run}")
    print("=" * 60)

    if not args.dry_run:
        if not db.available():
            print("[error] sin conexion a la base de datos.")
            return 1
        if not args.force and _ya_corrio_hoy():
            print("Ya hay ventas simuladas hoy. Usa --force para repetir.")
            return 0

    print("[1/4] Reponiendo inventario (ordenes pendientes)...")
    r0 = _recibir_pendientes() if not args.dry_run else 0
    print(f"      recibidas: {r0}")

    print("[2/4] Simulando ventas...")
    ok, fail = _simular_ventas(args.tickets, rng, args.dry_run)
    print(f"      ok={ok}  fallidas={fail}")

    print("[3/4] Generando ordenes de compra...")
    gen = _generar_ordenes(args.dry_run)
    print(f"      ordenes generadas: {gen}")

    print("[4/4] Reabasteciendo (recibiendo ordenes nuevas)...")
    r1 = _recibir_pendientes() if not args.dry_run else 0
    print(f"      recibidas: {r1}")

    # Purga de lotes caducados, si aplica.
    if not args.dry_run:
        try:
            purgados = repository.purge_expired(ADMIN_USER_ID)
            print(f"      lotes purgados: {purgados}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [aviso] purga: {exc}")

    print("-" * 60)
    print(f"Listo. Duracion: {(datetime.now() - inicio).total_seconds():.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
