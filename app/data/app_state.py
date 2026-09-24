"""Estado global de sesión: guarda el CSV cargado y el usuario actual.

Este módulo evita que el DataFrame leído en LoginScreen se pierda
(antes quedaba en `self.loaded_dataframe` sin que nadie lo usara).
Las pantallas deben leer de aquí y caer a `mock_data` si no hay datos.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional


class AppState:
    """Singleton simple con variables de clase (suficiente para desktop)."""

    df: Any = None
    csv_path: Optional[str] = None
    csv_rows: Optional[int] = None
    user_email: Optional[str] = None
    last_load: Optional[datetime.datetime] = None

    @classmethod
    def set_dataframe(cls, df: Any, path: Optional[str] = None) -> None:
        cls.df = df
        cls.csv_path = path
        try:
            cls.csv_rows = len(df) if df is not None else 0
        except Exception:
            cls.csv_rows = None
        cls.last_load = datetime.datetime.now()

    @classmethod
    def set_user(cls, email: Optional[str]) -> None:
        cls.user_email = email.strip() if email else None

    @classmethod
    def has_data(cls) -> bool:
        return cls.df is not None

    @classmethod
    def describe_source(cls) -> str:
        if cls.has_data():
            name = (cls.csv_path or "CSV").split("/")[-1].split("\\")[-1]
            rows = f" ({cls.csv_rows} filas)" if cls.csv_rows is not None else ""
            return f"{name}{rows}"
        return "datos de ejemplo"

    @classmethod
    def clear(cls) -> None:
        cls.df = None
        cls.csv_path = None
        cls.csv_rows = None
        cls.user_email = None
        cls.last_load = None
