"""Tarjeta de grafica con vista previa y ventana ampliada.

El dashboard muestra una version compacta de cada grafica. Al hacer clic en
la tarjeta (o en "Ampliar") se abre la misma grafica en grande, con todos los
datos y etiquetas legibles.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.widgets.mpl_canvas import MplCanvas

DrawFn = Callable[[MplCanvas], None]


class PreviewChartCard(QFrame):
    """Tarjeta con una grafica pequena que se amplia al hacer clic."""

    activated = Signal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        draw: DrawFn | None = None,
        expanded_draw: DrawFn | None = None,
        canvas_height: float = 2.3,
        expanded_height: float = 5.2,
        expanded_scrollable: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setProperty("role", "card")
        self._expanded_draw = expanded_draw or draw
        self._expanded_height = expanded_height
        self._expanded_scrollable = expanded_scrollable

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(8)
        texts = QVBoxLayout()
        texts.setSpacing(1)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {styles.INK};"
        )
        # las etiquetas no imponen ancho: la tarjeta se adapta al dashboard
        self.title_label.setWordWrap(True)
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        texts.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(
            f"font-size: 11px; color: {styles.MUTED};"
        )
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.subtitle_label.setVisible(bool(subtitle))
        texts.addWidget(self.subtitle_label)
        header.addLayout(texts, 1)

        self.expand_btn = QPushButton("Ampliar")
        self.expand_btn.setProperty("role", "ghost")
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.setToolTip("Ver la gráfica completa")
        self.expand_btn.clicked.connect(self.activated.emit)
        header.addWidget(self.expand_btn, 0, Qt.AlignTop)
        layout.addLayout(header)

        self.canvas = MplCanvas(width=2.8, height=canvas_height)
        # el layout puede reducir el ancho, pero no la altura legible
        self.canvas.setMinimumWidth(0)
        self.canvas.setMinimumHeight(int(canvas_height * 100))
        layout.addWidget(self.canvas, 1)
        if draw is not None:
            draw(self.canvas)

        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Clic para ampliar la gráfica")
        self.setStyleSheet(
            "QFrame[role='card']:hover { border: 1px solid #A9C7A2; }"
        )
        self.setFocusPolicy(Qt.StrongFocus)
        self._install_click_filter()

    # -- clic en cualquier parte de la tarjeta --------------------------

    def _install_click_filter(self) -> None:
        for widget in [self, *self.findChildren(QWidget)]:
            if isinstance(widget, QPushButton):
                continue
            widget.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (API de Qt)
        if (
            event.type() == QEvent.MouseButtonRelease
            and event.button() == Qt.LeftButton
        ):
            self.activated.emit()
            return True
        return super().eventFilter(obj, event)

    def mouseReleaseEvent(self, event):  # noqa: N802 (API de Qt)
        if event.button() == Qt.LeftButton:
            self.activated.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):  # noqa: N802 (API de Qt)
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.activated.emit()
            return
        super().keyPressEvent(event)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def open_expanded(self, parent: QWidget | None = None) -> None:
        dialog = ChartDialog(
            parent or self,
            title=self.title_label.text(),
            subtitle=self.subtitle_label.text(),
            draw=self._expanded_draw,
            height=self._expanded_height,
            scrollable=self._expanded_scrollable,
        )
        dialog.exec()


class ChartDialog(QDialog):
    """Ventana grande para leer una grafica completa."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        subtitle: str = "",
        draw: DrawFn | None = None,
        height: float = 5.2,
        scrollable: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(1040, 700)
        self.setMinimumSize(720, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setProperty("role", "sectionTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet(
                f"font-size: 12px; color: {styles.MUTED};"
            )
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        canvas = MplCanvas(width=10, height=height)
        if draw is not None:
            draw(canvas)

        if scrollable:
            canvas.setFixedHeight(max(420, int(height * 100)))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.addWidget(canvas)
            holder_layout.addStretch()
            scroll.setWidget(holder)
            layout.addWidget(scroll, 1)
        else:
            layout.addWidget(canvas, 1)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Cerrar")
        close_btn.setProperty("role", "outline")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
