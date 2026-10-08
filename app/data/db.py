"""Conexion MySQL leida del .env. Sin credenciales en codigo ni en logs."""
from __future__ import annotations

import os
from pathlib import Path


class DBError(Exception):
    """No hay base disponible (caida, credenciales o red)."""


def load_env(path: str | Path | None = None) -> dict:
    datos: dict = {}
    archivo = Path(path) if path else Path(__file__).resolve().parent.parent.parent / ".env"
    if not archivo.exists():
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
    get = lambda k, d: os.getenv(k, _ENV.get(k, d))
    return {
        "host": get("DB_HOST", "localhost"),
        "port": int(get("DB_PORT", "3306")),
        "user": get("DB_USER", "root"),
        "password": get("DB_PASSWORD", ""),
        "database": get("DB_NAME", "frutidata"),
    }


_disponible: bool | None = None


def available() -> bool:
    global _disponible
    if _disponible is None:
        try:
            conn = connect()
            conn.close()
            _disponible = True
        except DBError:
            _disponible = False
    return _disponible


def connect():
    try:
        import mysql.connector
    except ImportError as e:
        raise DBError("falta mysql-connector-python (pip install -r requirements.txt)") from e
    cfg = config()
    try:
        return mysql.connector.connect(connection_timeout=5, **cfg)
    except Exception as e:
        raise DBError("sin conexion a la base") from e


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    conn = connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return list(cur.fetchall())
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> int:
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def callproc(nombre: str, args: tuple = ()) -> list:
    conn = connect()
    try:
        cur = conn.cursor(dictionary=True)
        cur.callproc(nombre, args)
        salidas = []
        for r in cur.stored_results():
            salidas.extend(r.fetchall())
        conn.commit()
        return salidas
    finally:
        conn.close()
