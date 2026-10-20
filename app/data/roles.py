"""Roles y permisos de navegacion. La base manda: usuarios.id_rol."""
from __future__ import annotations

ROL_ADMIN = "Administrador"
ROL_GERENTE = "Gerente"
ROL_CAJERO = "Cajero"

ROLES_POR_ID = {1: ROL_ADMIN, 2: ROL_GERENTE, 3: ROL_CAJERO}

PANTALLA_COMPRAS = "compras"
PANTALLA_PREDICCION = "prediction"
PANTALLA_BITACORA = "bitacora"


def rol_desde_id(id_rol: int | str | None) -> str:
    try:
        return ROLES_POR_ID.get(int(id_rol or 0), ROL_CAJERO)
    except (TypeError, ValueError):
        return ROL_CAJERO


def puede_ver(rol: str | None, pantalla: str) -> bool:
    if pantalla in (PANTALLA_COMPRAS, PANTALLA_PREDICCION):
        return rol in (ROL_ADMIN, ROL_GERENTE)
    if pantalla == PANTALLA_BITACORA:
        return rol == ROL_ADMIN
    return True


def puede_comprar(rol: str | None) -> bool:
    return rol in (ROL_ADMIN, ROL_GERENTE)


def rol_ui(rol: str | None) -> str:
    # sin sesion (p. ej. pruebas de pantalla) se muestra la vista completa
    return rol or ROL_ADMIN
