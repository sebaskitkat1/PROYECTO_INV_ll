#!/usr/bin/env python3
"""Cajero automatico diario para Cosecha (fruteria).

SOLO PARA ENTORNOS DEMO. Antes de escribir en la base exige
`COSECHA_ENTORNO=demo` (variable de entorno o `.env`). Con `--dry-run`
no escribe y no necesita la variable.

Simula la operacion diaria de la caja para alimentar el modelo de DA:
  1. Reabastece con ordenes generadas por esta misma corrida. Nunca recibe
     ordenes preexistentes, para no tocar compras reales.
  2. Simula ventas (tickets) con productos aleatorios de la caja.
  3. Vuelve a generar y recibir ordenes propias para el dia siguiente.
  4. Purga lotes caducados.

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
import logging
import os
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data import db, repository

logger = logging.getLogger("cosecha.cajero")

# Correos demo; se pueden cambiar con CAJERO_CORREO / CAJERO_ADMIN_CORREO.
CORREO_CAJERO_DEFAULT = "caja@frutidata.local"
CORREO_ADMIN_DEFAULT = "admin@frutidata.local"
# Productos por ticket (min, max).
ITEMS_POR_TICKET = (1, 4)
# Cantidades tipicas por unidad.
CANTIDADES_KG_L = (0.25, 0.5, 0.5, 1.0, 1.0, 1.5, 2.0)
CANTIDADES_PZAS = (1, 1, 2, 2, 3)


def _config(nombre: str, default: str) -> str:
    return (os.getenv(nombre) or db.load_env().get(nombre) or default).strip()


def _entorno_demo() -> bool:
    valor = os.getenv("COSECHA_ENTORNO") or db.load_env().get("COSECHA_ENTORNO")
    return str(valor or "").strip().lower() == "demo"


def _configurar_logging() -> None:
    """El detalle queda en scripts/cajero_diario.log; consola si es manual."""
    log_path = Path(__file__).resolve().parent / "cajero_diario.log"
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    if sys.stdout.isatty():
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def _usuario_id(correo: str, etiqueta: str) -> int:
    uid = repository.user_id_by_email(correo)
    if not uid:
        raise RuntimeError(
            f"No existe un usuario activo con correo {correo} ({etiqueta}).")
    return int(uid)


def _recibir_pendientes(ids: list[int], admin_id: int) -> int:
    """Recibe solo las ordenes generadas por esta corrida."""
    if not ids:
        return 0
    try:
        ordenes = repository.purchase_orders(200)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudieron listar ordenes: %s", exc)
        return 0
    abiertas = {int(o["id_orden"]): o for o in ordenes
                if o.get("estado") in ("borrador", "enviada")}
    recibidas = 0
    for id_orden in ids:
        if id_orden not in abiertas:
            continue
        try:
            repository.receive_purchase_order(int(id_orden), admin_id)
            recibidas += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Orden #%s no recibida: %s", id_orden, exc)
    return recibidas


def _reabastecer(admin_id: int) -> tuple[int, int]:
    """Genera ordenes propias y las recibe; devuelve (generadas, recibidas)."""
    try:
        ids = repository.generate_purchase_order_ids(admin_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Generar ordenes: %s", exc)
        return 0, 0
    return len(ids), _recibir_pendientes(ids, admin_id)


def _simular_ventas(tickets: int, rng: random.Random, dry_run: bool,
                    cajero_id: int) -> tuple[int, int]:
    ok = 0
    fail = 0
    if dry_run:
        return 0, 0
    try:
        productos = repository.pos_products()
        metodos = [m["id"] for m in repository.pos_payment_methods()]
    except Exception as exc:  # noqa: BLE001
        logger.error("No se pudo cargar catalogo: %s", exc)
        return 0, tickets

    if not productos or not metodos:
        logger.error("Catalogo o metodos de pago vacios.")
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
            repository.register_sale(items, int(metodo), cajero_id,
                                     origen="simulado")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            fail += 1
            if fail <= 5:
                logger.warning("Venta %s fallida: %s", i + 1, exc)
    return ok, fail


def _ya_corrio_hoy() -> bool:
    """Evita que el login y la tarea de las 08:00 dupliquen la corrida."""
    try:
        filas = db.fetchall(
            "SELECT COUNT(*) AS n FROM ventas "
            "WHERE DATE(fecha_hora) = CURDATE() AND origen = 'simulado'")
        return bool(filas and int(filas[0]["n"] or 0) > 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo verificar la corrida diaria: %s", exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Cajero automatico diario - Cosecha")
    parser.add_argument("--tickets", type=int, default=30,
                        help="numero de tickets a simular (default 30)")
    parser.add_argument("--seed", type=int, default=None,
                        help="semilla para reproducibilidad")
    parser.add_argument("--dry-run", action="store_true",
                        help="no escribe en la base")
    parser.add_argument("--force", action="store_true",
                        help="repite la corrida aunque ya haya ventas hoy")
    args = parser.parse_args()

    _configurar_logging()
    rng = random.Random(args.seed if args.seed is not None else random.randrange(10**9))

    inicio = datetime.now()
    logger.info("=" * 60)
    logger.info("Cajero diario Cosecha - %s", inicio.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("tickets=%s seed=%s dry_run=%s", args.tickets, args.seed, args.dry_run)
    logger.info("=" * 60)

    cajero_id = 0
    admin_id = 0
    if not args.dry_run:
        if not _entorno_demo():
            logger.error(
                "Entorno no habilitado. Define COSECHA_ENTORNO=demo en el "
                "entorno o en .env para permitir escrituras de demostracion.")
            return 2
        if not db.available():
            logger.error("Sin conexion a la base de datos.")
            return 1
        try:
            cajero_id = _usuario_id(
                _config("CAJERO_CORREO", CORREO_CAJERO_DEFAULT), "cajero")
            admin_id = _usuario_id(
                _config("CAJERO_ADMIN_CORREO", CORREO_ADMIN_DEFAULT),
                "administrador")
        except RuntimeError as exc:
            logger.error("%s", exc)
            return 3
        if not args.force and _ya_corrio_hoy():
            logger.info("Ya hay ventas simuladas hoy. Usa --force para repetir.")
            return 0

    logger.info("[1/4] Reabasteciendo antes de vender (ordenes propias)...")
    gen0, rec0 = _reabastecer(admin_id) if not args.dry_run else (0, 0)
    logger.info("      generadas: %s  recibidas: %s", gen0, rec0)

    logger.info("[2/4] Simulando ventas...")
    if args.dry_run:
        logger.info("      omitido (dry-run)")
    else:
        ok, fail = _simular_ventas(args.tickets, rng, args.dry_run, cajero_id)
        logger.info("      ok=%s  fallidas=%s", ok, fail)

    logger.info("[3/4] Reabasteciendo despues de vender (ordenes propias)...")
    gen1, rec1 = _reabastecer(admin_id) if not args.dry_run else (0, 0)
    logger.info("      generadas: %s  recibidas: %s", gen1, rec1)

    logger.info("[4/4] Purgando lotes caducados...")
    if not args.dry_run:
        try:
            purgados = repository.purge_expired(admin_id)
            logger.info("      lotes purgados: %s", purgados)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Purga: %s", exc)

    logger.info("-" * 60)
    logger.info("Listo. Duracion: %.1fs",
                (datetime.now() - inicio).total_seconds())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
