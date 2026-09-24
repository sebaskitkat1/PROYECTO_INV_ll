"""Barra superior minimalista: marca, nav segmentada y salida discreta."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

NAV_ITEMS = [
    ("dashboard", "Inicio"),
    ("sales", "Ventas"),
    ("inventory", "Inventario"),
    ("prediction", "Predicción"),
]


class NavBar(QFrame):
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
        self.setProperty("role", "topbar")
        self.setFixedHeight(60)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 0, 20, 0)
        outer.setSpacing(16)

        # Marca pequeña + título
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        brand_col.setContentsMargins(0, 0, 0, 0)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_row.setContentsMargins(0, 0, 0, 0)

        if on_back:
            back_btn = QPushButton("Volver")
            back_btn.setProperty("role", "ghost")
            back_btn.setCursor(Qt.PointingHandCursor)
            back_btn.clicked.connect(on_back)
            brand_row.addWidget(back_btn)

        mark = QLabel("cafédata.")
        mark.setStyleSheet("font-size: 13px; font-weight: 700; color: #2A1E17; letter-spacing: -0.3px;")
        brand_row.addWidget(mark)

        title_label = QLabel(title)
        title_label.setProperty("role", "pageTitle")
        brand_row.addWidget(title_label)
        brand_col.addLayout(brand_row)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setProperty("role", "pageSubtitle")
        brand_col.addWidget(subtitle_label)

        outer.addLayout(brand_col)
        outer.addStretch()

        # Nav segmentada en píldora
        seg = QFrame()
        seg.setProperty("role", "segNav")
        seg_layout = QHBoxLayout(seg)
        seg_layout.setContentsMargins(4, 4, 4, 4)
        seg_layout.setSpacing(2)
        for screen_key, label in NAV_ITEMS:
            btn = QPushButton(label)
            btn.setProperty("role", "navActive" if screen_key == active_screen else "nav")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, s=screen_key: on_navigate(s))
            seg_layout.addWidget(btn)
        outer.addWidget(seg)

        logout_btn = QPushButton("Salir")
        logout_btn.setProperty("role", "ghost")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.clicked.connect(on_logout)
        outer.addWidget(logout_btn)
