"""Estado de sesion: usuario actual. Los datos vendran de la base."""
from __future__ import annotations

import datetime
from typing import Optional


class AppState:
    user_email: Optional[str] = None
    last_login: Optional[datetime.datetime] = None

    @classmethod
    def set_user(cls, email: Optional[str]) -> None:
        cls.user_email = email.strip() if email else None
        cls.last_login = datetime.datetime.now()

    @classmethod
    def clear(cls) -> None:
        cls.user_email = None
        cls.last_login = None
