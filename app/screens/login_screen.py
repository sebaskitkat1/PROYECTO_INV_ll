"""Acceso simple."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data.app_state import AppState


class LoginScreen(QWidget):
    def __init__(self, on_login: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.on_login = on_login

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)
        outer.setContentsMargins(24, 32, 24, 32)

        card = QFrame()
        card.setProperty("role", "loginCard")
        card.setFixedWidth(360)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        brand = QLabel("frutidata.")
        brand.setAlignment(Qt.AlignCenter)
        brand.setStyleSheet("font-size: 26px; font-weight: 700; color: #2A1E17; letter-spacing: -0.6px;")
        layout.addWidget(brand)
        layout.addSpacing(4)

        layout.addWidget(self._field_label("Usuario o correo"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tufruta@ejemplo.com")
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
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self._handle_login)
        layout.addWidget(self.login_button)

        outer.addWidget(card, alignment=Qt.AlignCenter)

        # enter en cualquier campo entra directo
        self.email_input.returnPressed.connect(self._handle_login)
        self.password_input.returnPressed.connect(self._handle_login)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {styles.MUTED}; font-size: 12px; font-weight: 600;")
        return label

    def _clear_error(self) -> None:
        self.error_label.setVisible(False)

    def _handle_login(self) -> None:
        email = self.email_input.text().strip()
        password = self.password_input.text()
        if "@" not in email or "." not in email.split("@")[-1]:
            self.error_label.setText("Ese correo no parece valido. Revisalo.")
            self.error_label.setVisible(True)
            return
        if len(password) < 4:
            self.error_label.setText("La contraseña debe tener al menos 4 caracteres.")
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
