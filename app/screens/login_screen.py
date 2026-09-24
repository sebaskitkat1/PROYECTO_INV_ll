"""Acceso cálido y simple."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data.app_state import AppState

try:
    import pandas as pd
except ImportError:
    pd = None


class LoginScreen(QWidget):
    def __init__(self, on_login: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.on_login = on_login
        self.loaded_dataframe = None

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)
        outer.setContentsMargins(24, 32, 24, 32)

        card = QFrame()
        card.setProperty("role", "loginCard")
        card.setFixedWidth(380)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        brand = QLabel("cafédata.")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet("font-size: 26px; font-weight: 700; color: #2A1E17; letter-spacing: -0.6px;")
        layout.addWidget(brand)

        subtitle = QLabel("Tus números de café, claros y al día")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setProperty("role", "pageSubtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        layout.addWidget(self._field_label("Usuario o correo"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tucafe@ejemplo.com")
        self.email_input.textChanged.connect(self._clear_error)
        layout.addWidget(self.email_input)

        layout.addWidget(self._field_label("Contraseña"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Tu contraseña")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.textChanged.connect(self._clear_error)
        layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            f"background-color: {styles.DANGER_BG}; color: {styles.DANGER};"
            "padding: 8px 12px; border-radius: 10px; font-size: 12px;"
        )
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        self.login_button = QPushButton("Entrar")
        self.login_button.setProperty("role", "primary")
        self.login_button.setFixedHeight(38)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self._handle_login)
        layout.addWidget(self.login_button)

        sep = QLabel("o continúa con un archivo")
        sep.setAlignment(Qt.AlignCenter)
        sep.setProperty("role", "micro")
        layout.addWidget(sep)

        self.csv_button = QPushButton("Cargar CSV")
        self.csv_button.setProperty("role", "secondary")
        self.csv_button.setFixedHeight(38)
        self.csv_button.setCursor(Qt.PointingHandCursor)
        self.csv_button.clicked.connect(self._handle_csv_upload)
        layout.addWidget(self.csv_button)

        self.csv_status_label = QLabel("")
        self.csv_status_label.setAlignment(Qt.AlignCenter)
        self.csv_status_label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px;")
        self.csv_status_label.setVisible(False)
        layout.addWidget(self.csv_status_label)

        hint = QLabel("CSV con columnas fecha, producto, cantidad y total")
        hint.setAlignment(Qt.AlignCenter)
        hint.setProperty("role", "micro")
        layout.addWidget(hint)

        outer.addWidget(card, alignment=Qt.AlignCenter)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 600;")
        return label

    def _clear_error(self) -> None:
        self.error_label.setVisible(False)

    def _handle_login(self) -> None:
        if not self.email_input.text().strip() or not self.password_input.text().strip():
            self.error_label.setText("Completa usuario y contraseña para entrar.")
            self.error_label.setVisible(True)
            return
        self.error_label.setVisible(False)
        self.login_button.setEnabled(False)
        self.login_button.setText("Entrando…")
        QTimer.singleShot(600, self._finish_login)

    def _finish_login(self) -> None:
        self.login_button.setEnabled(True)
        self.login_button.setText("Entrar")
        AppState.set_user(self.email_input.text())
        self.on_login("dashboard")

    def _handle_csv_upload(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV (*.csv)")
        if not file_path:
            return
        file_name = file_path.split("/")[-1].split("\\")[-1]
        row_count = None
        if pd is not None:
            try:
                self.loaded_dataframe = pd.read_csv(file_path)
                row_count = len(self.loaded_dataframe)
                AppState.set_dataframe(self.loaded_dataframe, file_path)
            except Exception:
                self.loaded_dataframe = None
                self.error_label.setText("No se pudo leer ese CSV. Entrarás con datos de ejemplo.")
                self.error_label.setVisible(True)
        status = f"{file_name}"
        if row_count is not None:
            status += f" · {row_count} filas · abriendo…"
        self.csv_status_label.setText(status)
        self.csv_status_label.setVisible(True)
        QTimer.singleShot(900, self._finish_login)
