"""Ventana principal: administra la navegación entre pantallas."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app.screens.dashboard_screen import DashboardScreen
from app.screens.inventory_screen import InventoryScreen
from app.screens.login_screen import LoginScreen
from app.screens.prediction_screen import PredictionScreen
from app.screens.sales_screen import SalesScreen


class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.

    Usa un QStackedWidget para alternar entre pantallas, de forma
    equivalente al estado `screen` que controlaba la navegación en la
    versión web (src/App.tsx).
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CaféData — Sistema de Análisis")
        self.resize(1180, 780)
        self.setMinimumSize(900, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Login se construye una sola vez. Las demás pantallas se
        # reconstruyen cada vez que se navega a ellas, para que en el
        # futuro puedan reflejar datos recién cargados (por ejemplo, un
        # CSV nuevo) sin necesidad de reiniciar la aplicación.
        self.screens: dict[str, object] = {}
        self._REBUILD_ON_NAVIGATE = {"dashboard", "sales", "inventory", "prediction"}

        self._build_login_screen()
        self.navigate("login")

    # -- construcción de pantallas -----------------------------------

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

    # -- navegación ----------------------------------------------------

    def navigate(self, screen_name: str) -> None:
        builders = {
            "login": self._build_login_screen,
            "dashboard": self._build_dashboard_screen,
            "sales": self._build_sales_screen,
            "inventory": self._build_inventory_screen,
            "prediction": self._build_prediction_screen,
        }
        needs_build = screen_name not in self.screens or screen_name in self._REBUILD_ON_NAVIGATE
        if needs_build:
            builders[screen_name]()
        self.stack.setCurrentWidget(self.screens[screen_name])

    def logout(self) -> None:
        self.navigate("login")
