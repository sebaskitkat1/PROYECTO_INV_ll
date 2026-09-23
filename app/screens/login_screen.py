"""Pantalla de inicio de sesión / carga de datos (CSV)."""
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

try:
    import pandas as pd
except ImportError:  # pandas es opcional solo para esta validación ligera
    pd = None


class LoginScreen(QWidget):
    """
    Pantalla inicial: permite iniciar sesión con usuario/contraseña o
    cargar directamente un archivo CSV con los datos del negocio.

    ``on_login`` recibe el nombre de la siguiente pantalla a mostrar
    (por ahora siempre 'dashboard'), igual que en el prototipo web.
    """

    def __init__(self, on_login: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.on_login = on_login
        self.loaded_dataframe = None  # aquí quedará el CSV cargado, si aplica

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        card = QWidget()
        card.setFixedWidth(360)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        # --- Logo / nombre de la app ---
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignCenter)
        logo_icon = QLabel("\u25A6")
        logo_icon.setStyleSheet(
            f"background-color: {styles.PRIMARY}; color: white; font-size: 16px;"
            "border-radius: 8px; padding: 6px 10px;"
        )
        logo_text = QLabel("CaféData")
        logo_text.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {styles.PRIMARY};")
        logo_row.addWidget(logo_icon)
        logo_row.addWidget(logo_text)
        layout.addLayout(logo_row)

        subtitle = QLabel("Sistema de Análisis para tu Negocio")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {styles.TEXT_GRAY}; font-size: 12px;")
        layout.addWidget(subtitle)
        layout.addSpacing(10)

        # --- Formulario ---
        layout.addWidget(self._field_label("Usuario o Email"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("tucafe@ejemplo.com")
        self.email_input.textChanged.connect(self._clear_error)
        layout.addWidget(self.email_input)

        layout.addWidget(self._field_label("Contraseña"))
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.textChanged.connect(self._clear_error)
        layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(
            f"background-color: {styles.DANGER_BG}; color: {styles.TEXT_GRAY};"
            "padding: 6px 10px; border-radius: 6px; font-size: 11px;"
        )
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        self.login_button = QPushButton("ENTRAR")
        self.login_button.setProperty("role", "primary")
        self.login_button.setFixedHeight(44)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self._handle_login)
        layout.addWidget(self.login_button)

        # --- Separador "o" ---
        divider_row = QHBoxLayout()
        line_left = self._divider_line()
        line_right = self._divider_line()
        or_label = QLabel("o")
        or_label.setStyleSheet(f"color: {styles.TEXT_LIGHT_GRAY}; font-size: 11px;")
        divider_row.addWidget(line_left)
        divider_row.addWidget(or_label)
        divider_row.addWidget(line_right)
        layout.addLayout(divider_row)

        # --- Carga de CSV ---
        self.csv_button = QPushButton("CARGAR DATOS (CSV)")
        self.csv_button.setProperty("role", "secondary")
        self.csv_button.setFixedHeight(44)
        self.csv_button.setCursor(Qt.PointingHandCursor)
        self.csv_button.clicked.connect(self._handle_csv_upload)
        layout.addWidget(self.csv_button)

        self.csv_status_label = QLabel("")
        self.csv_status_label.setAlignment(Qt.AlignCenter)
        self.csv_status_label.setStyleSheet(f"color: {styles.SUCCESS}; font-size: 11px;")
        self.csv_status_label.setVisible(False)
        layout.addWidget(self.csv_status_label)

        hint = QLabel("¿Primera vez? Cargue un archivo CSV")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {styles.TEXT_LIGHT_GRAY}; font-size: 11px;")
        layout.addWidget(hint)

        outer.addWidget(card)

    # -- helpers de construcción ------------------------------------

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setStyleSheet(
            f"color: {styles.TEXT_GRAY}; font-size: 10px; font-weight: 700; letter-spacing: 1px;"
        )
        return label

    @staticmethod
    def _divider_line() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {styles.BORDER}; max-height: 1px;")
        return line

    # -- lógica ------------------------------------------------------

    def _clear_error(self) -> None:
        self.error_label.setVisible(False)

    def _handle_login(self) -> None:
        if not self.email_input.text().strip() or not self.password_input.text().strip():
            self.error_label.setText("\u2715  Por favor complete todos los campos.")
            self.error_label.setVisible(True)
            return

        self.error_label.setVisible(False)
        self.login_button.setEnabled(False)
        self.login_button.setText("Ingresando...")
        # Simula una llamada de red breve, igual que el setTimeout del prototipo.
        QTimer.singleShot(600, self._finish_login)

    def _finish_login(self) -> None:
        self.login_button.setEnabled(True)
        self.login_button.setText("ENTRAR")
        self.on_login("dashboard")

    def _handle_csv_upload(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV (*.csv)")
        if not file_path:
            return

        file_name = file_path.split("/")[-1]
        row_count = None
        if pd is not None:
            try:
                self.loaded_dataframe = pd.read_csv(file_path)
                row_count = len(self.loaded_dataframe)
            except Exception:
                # Si el CSV no se puede leer, se continúa igualmente con los
                # datos de ejemplo; aquí es donde luego se puede mostrar un
                # error más específico al usuario.
                self.loaded_dataframe = None

        status = f"\u2713 {file_name}"
        if row_count is not None:
            status += f" ({row_count} filas) — cargando dashboard..."
        else:
            status += " — cargando dashboard..."
        self.csv_status_label.setText(status)
        self.csv_status_label.setVisible(True)

        QTimer.singleShot(900, self._finish_login)
