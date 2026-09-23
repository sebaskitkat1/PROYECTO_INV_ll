"""Barra superior reutilizable: título, navegación entre pantallas y salir."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app import styles

# Pantallas disponibles y su etiqueta visible en la barra de navegación.
NAV_ITEMS = [
    ("dashboard", "Inicio"),
    ("sales", "Ventas"),
    ("inventory", "Inventario"),
    ("prediction", "Predicción"),
]


class NavBar(QFrame):
    """
    Encabezado superior común a Dashboard, Ventas, Inventario y
    Predicción. Muestra el título de la pantalla actual, un menú de
    navegación y el botón de salir (logout).
    """

    def __init__(
        self,
        title: str,
        subtitle: str,
        active_screen: str,
        on_navigate: Callable[[str], None],
        on_logout: Callable[[], None],
        on_back: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.BG_WHITE}; border-bottom: 1px solid {styles.BORDER};")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 10, 20, 10)

        # --- Título (+ botón "volver" opcional) ---
        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        if on_back:
            back_btn = QPushButton("\u2190")
            back_btn.setProperty("role", "link")
            back_btn.setFixedWidth(28)
            back_btn.clicked.connect(on_back)
            title_row.addWidget(back_btn)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_label = QLabel(title)
        title_label.setProperty("role", "pageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setProperty("role", "pageSubtitle")
        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)
        title_row.addLayout(title_col)

        outer.addLayout(title_row)
        outer.addStretch()

        # --- Navegación entre pantallas ---
        nav_row = QHBoxLayout()
        nav_row.setSpacing(4)
        for screen_key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setProperty("role", "navActive" if screen_key == active_screen else "nav")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, s=screen_key: on_navigate(s))
            nav_row.addWidget(btn)
        outer.addLayout(nav_row)

        outer.addSpacing(12)

        # --- Salir ---
        logout_btn = QPushButton("SALIR")
        logout_btn.setProperty("role", "link")
        logout_btn.clicked.connect(on_logout)
        outer.addWidget(logout_btn)
