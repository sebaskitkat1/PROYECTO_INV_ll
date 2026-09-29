"""Ventana principal: administra la navegacion entre pantallas."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.data.app_state import AppState
from app.screens.dashboard_screen import DashboardScreen
from app.screens.inventory_screen import InventoryScreen
from app.screens.login_screen import LoginScreen
from app.screens.prediction_screen import PredictionScreen
from app.screens.sales_screen import SalesScreen


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("cafedata")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # login se construye una sola vez. Las demas pantallas se
        # reconstruyen al navegar, asi toman los datos nuevos
        # de la base sin reiniciar la app.
        self.screens: dict[str, object] = {}
        # login tambien se reconstruye: asi vuelve limpio, sin texto anterior
        self._REBUILD_ON_NAVIGATE = {"login", "dashboard", "sales", "inventory", "prediction"}

        self._build_login_screen()
        self.navigate("login")

    # -- construccion de pantallas -----------------------------------

    def _build_login_screen(self) -> None:
        screen = LoginScreen(on_login=self.navigate)
        self._register("login", screen)

    def _build_dashboard_screen(self) -> None:
        screen = DashboardScreen(on_navigate=self.navigate, on_logout=self.logout)
        self._register("dashboard", screen)

    def _build_sales_screen(self) -> None:
        screen = SalesScreen(on_navigate=self.navigate, on_logout=self.logout)
        self._register("sales", screen)

    def _build_inventory_screen(self) -> None:
        screen = InventoryScreen(on_navigate=self.navigate, on_logout=self.logout)
        self._register("inventory", screen)

    def _build_prediction_screen(self) -> None:
        screen = PredictionScreen(on_navigate=self.navigate, on_logout=self.logout)
        self._register("prediction", screen)

    def _register(self, key: str, widget) -> None:
        if key in self.screens:
            old_widget = self.screens[key]
            self.stack.removeWidget(old_widget)
            old_widget.deleteLater()
        self.screens[key] = widget
        self.stack.addWidget(widget)

    # -- navegacion ----------------------------------------------------

    def navigate(self, screen_name: str) -> None:
        builders = {
            "login": self._build_login_screen,
            "dashboard": self._build_dashboard_screen,
            "sales": self._build_sales_screen,
            "inventory": self._build_inventory_screen,
            "prediction": self._build_prediction_screen,
        }
        if screen_name not in builders:
            raise ValueError(f"pantalla desconocida: {screen_name}")
        if screen_name != "login" and not AppState.user_email:
            screen_name = "login"
        needs_build = screen_name not in self.screens or screen_name in self._REBUILD_ON_NAVIGATE
        if needs_build:
            builders[screen_name]()
        self.stack.setCurrentWidget(self.screens[screen_name])

    def logout(self) -> None:
        # salir borra la sesion para que no quede el usuario anterior
        AppState.clear()
        self.navigate("login")
