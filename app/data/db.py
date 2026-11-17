"""Conexion MySQL leida del .env. Sin credenciales en codigo ni en logs."""
from __future__ import annotations

import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class DBError(Exception):
    """No hay base disponible (caida, credenciales o red)."""


def _env_candidates() -> list[Path]:
    rutas = []
    if getattr(sys, "frozen", False):
        rutas.append(Path(sys.executable).resolve().parent / ".env")
    rutas.append(Path(__file__).resolve().parent.parent.parent / ".env")
    rutas.append(Path.cwd() / ".env")
    return rutas


def load_env(path: str | Path | None = None) -> dict:
    datos: dict = {}
    archivo: Path | None = Path(path) if path is not None else None
    if archivo is None:
        archivo = next((r for r in _env_candidates() if r.exists()), None)
    if archivo is None or not archivo.exists():
        return datos
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        datos[clave.strip()] = valor.strip().strip("\"'")
    return datos


_ENV = load_env()


def config() -> dict:
    def get(k, d):
        return os.getenv(k, _ENV.get(k, d))

    return {
        "host": get("DB_HOST", "localhost"),
        "port": int(get("DB_PORT", "3306")),
        "user": get("DB_USER", "root"),
        "password": get("DB_PASSWORD", ""),
        "database": get("DB_NAME", "frutidata"),
    }


# -- disponibilidad ------------------------------------------------------
# Un fallo se recuerda 30 s para no reintentar en cada pantalla; un exito
# queda cacheado hasta que reset_availability() o una operacion fallen.

DISPONIBILIDAD_TTL = 30.0
_disponible: bool | None = None
_disponible_hasta = 0.0


def _reloj() -> float:
    return time.monotonic()


def _marcar_exito() -> None:
    global _disponible, _disponible_hasta
    _disponible = True
    _disponible_hasta = 0.0


def _marcar_fallo() -> None:
    global _disponible, _disponible_hasta
    _disponible = False
    _disponible_hasta = _reloj() + DISPONIBILIDAD_TTL


def reset_availability() -> None:
    """Olvida el estado y el pool; la proxima operacion reconecta."""
    global _disponible, _disponible_hasta, _pool
    _disponible = None
    _disponible_hasta = 0.0
    _pool = None


def available() -> bool:
    if _disponible is True:
        return True
    if _disponible is False and _reloj() < _disponible_hasta:
        return False
    try:
        conn = connect()
    except DBError:
        return False
    try:
        conn.close()
    except Exception:  # el pool ya devolvio la conexion
        pass
    return True


# -- pool ----------------------------------------------------------------

_pool: Any = None
_pool_seq = 0


def _pool_size() -> int:
    valor = os.getenv("DB_POOL_SIZE", _ENV.get("DB_POOL_SIZE", "4"))
    try:
        return max(1, int(valor))
    except (TypeError, ValueError):
        return 4


def _ssl_args() -> dict:
    valor = str(os.getenv("DB_SSL", _ENV.get("DB_SSL", "0"))).strip().lower()
    # DB_SSL=1 exige TLS; si el servidor no lo soporta, la conexion falla.
    return {"ssl_disabled": valor not in ("1", "true", "yes", "si")}


def _crear_pool() -> Any:
    global _pool, _pool_seq
    try:
        from mysql.connector import pooling
    except ImportError as exc:
        raise DBError(
            "falta mysql-connector-python (pip install -r requirements.txt)"
        ) from exc
    args = config()
    args.update(_ssl_args())
    args.update({
        "pool_name": f"cosecha_{_pool_seq}",
        "pool_size": _pool_size(),
        "pool_reset_session": True,
        "connection_timeout": 5,
    })
    _pool_seq += 1
    try:
        _pool = pooling.MySQLConnectionPool(**args)
    except Exception as exc:
        _pool = None
        logging.getLogger("cosecha.db").warning(
            "No se pudo crear el pool de MySQL (%s)", type(exc).__name__)
        raise DBError("sin conexion a la base") from exc
    return _pool


def connect():
    """Toma una conexion del pool (lo crea perezosamente la primera vez)."""
    global _pool
    if _pool is None:
        try:
            _crear_pool()
        except DBError:
            _marcar_fallo()
            raise
    try:
        conn = _pool.get_connection()
    except Exception as exc:
        _pool = None
        _marcar_fallo()
        logging.getLogger("cosecha.db").warning(
            "No se pudo conectar a MySQL (%s)", type(exc).__name__)
        raise DBError("sin conexion a la base") from exc
    _marcar_exito()
    return conn


@contextmanager
def _cursor(conn: Any, dictionary: bool = False) -> Iterator[Any]:
    cur = conn.cursor(dictionary=dictionary)
    try:
        yield cur
    finally:
        cur.close()


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    conn = connect()
    try:
        with _cursor(conn, True) as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    conn = connect()
    try:
        with _cursor(conn) as cur:
            cur.execute(sql, params)
            conn.commit()
            return int(cur.rowcount)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def callproc(nombre: str, args: tuple = ()) -> list:
    conn = connect()
    try:
        with _cursor(conn, True) as cur:
            cur.callproc(nombre, args)
            salidas = []
            for r in cur.stored_results():
                salidas.extend(r.fetchall())
            conn.commit()
            return salidas
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[Any]:
    conn = connect()
    try:
        with _cursor(conn, True) as cur:
            yield cur
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
