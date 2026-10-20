"""Estado de sesion: usuario actual. Los datos vienen de la base (repository)."""
from __future__ import annotations

import datetime
from typing import Optional


class AppState:
    user_email: Optional[str] = None
    user_id: Optional[int] = None
    sucursal_id: Optional[int] = None
    user_role: Optional[str] = None
    last_login: Optional[datetime.datetime] = None

    @classmethod
    def set_user(cls, email: Optional[str], user_id: Optional[int] = None,
                 sucursal_id: Optional[int] = None, role: Optional[str] = None) -> None:
        cls.user_email = email.strip() if email else None
        cls.user_id = user_id
        cls.sucursal_id = sucursal_id
        cls.user_role = role
        cls.last_login = datetime.datetime.now()

    @classmethod
    def clear(cls) -> None:
        cls.user_email = None
        cls.user_id = None
        cls.sucursal_id = None
        cls.user_role = None
        cls.last_login = None
