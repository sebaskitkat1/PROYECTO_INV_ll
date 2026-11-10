"""Pantalla de prediccion de demanda a 30 dias."""
from __future__ import annotations

import datetime
from typing import Callable

from matplotlib import dates as mdates
from matplotlib.ticker import FuncFormatter
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app import styles
from app.data import analytics, mock_data, repository
from app.data.app_state import AppState
from app.data.async_loader import async_disponible, run_async
from app.data.db import DBError
from app.widgets.mpl_canvas import MplCanvas
from app.widgets.nav_bar import NavBar


class PredictionScreen(QWidget):
    """Pantalla de prediccion de demanda basada en datos historicos."""

    def __init__(
        self,
        on_navigate: Callable[[str], None],
        on_logout: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self._online = repository.activa()
        self._hist: list = []
        self._detalle_cache: list[dict] = []
        self._futuro: list = []
        self._bt: dict = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(
            NavBar(
                title="Pronóstico",
                subtitle="",
                active_screen="prediction",
                on_navigate=on_navigate,
                on_logout=on_logout,
                on_back=lambda: on_navigate("dashboard"),
            )
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 24)
        content_layout.setSpacing(14)

        self.chart_layout = QVBoxLayout()
        content_layout.addLayout(self.chart_layout)
        self.table_layout = QVBoxLayout()
        content_layout.addLayout(self.table_layout)
        content_layout.addLayout(self._build_actions_row())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll)
        self._load_data()

    # -- carga de datos -------------------------------------------------

    def _load_data(self) -> None:
        if not async_disponible():
            self._apply_data(self._fetch_data())
            return
        run_async(self, self._fetch_data, self._apply_data,
                  lambda _mensaje: self._apply_data(self._fallback_data()))

    @staticmethod
    def _fetch_data() -> dict:
        origen, fuente_txt = PredictionScreen._fuente_datos()
        hist = PredictionScreen._historia(origen)
        detalle = PredictionScreen._detalle(origen)
        futuro = analytics.forecast_daily(hist, 30)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        return {"hist": hist, "detalle": detalle, "futuro": futuro,
                "bt": bt, "fuente": fuente_txt}

    @staticmethod
    def _fallback_data() -> dict:
        hist = PredictionScreen._historia(None)
        detalle = mock_data.get_sales_detail()
        futuro = analytics.forecast_daily(hist, 30)
        bt = analytics.backtest([d for d, _ in hist], [v for _, v in hist])
        return {"hist": hist, "detalle": detalle, "futuro": futuro,
                "bt": bt, "fuente": "ejemplo"}

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _apply_data(self, data: dict) -> None:
        self._hist = data["hist"]
        self._detalle_cache = data["detalle"]
        self._futuro = data["futuro"]
        self._bt = data["bt"]
        self._clear_layout(self.chart_layout)
        self._clear_layout(self.table_layout)
        self.chart_layout.addWidget(
            self._line_chart_card(data["hist"], data["futuro"], data["fuente"]))
        self.table_layout.addWidget(
            self._table_card(data["hist"], data["futuro"], data["bt"], data["detalle"]))

    # -- grafica historico vs prediccion -----------------------------------

    @staticmethod
    def _fuente_datos() -> tuple[str | None, str]:
        """Devuelve (origen para filtrar, etiqueta visible)."""
        try:
            datos = repository.data_origin()
        except DBError:
            return None, "ejemplo"
        if datos["real"] >= 14:
            return "real", f"datos reales · {datos['real']} ventas"
        if datos["total"]:
            if datos["pct_simulado"] >= 99.9:
                return None, f"datos simulados · {datos['total']} ventas"
            return None, f"datos mixtos · {datos['pct_simulado']:.0f}% simulados"
        return None, "sin ventas registradas"

    @staticmethod
    def _historia(origen: str | None = None) -> list:
        # serie diaria real; ejemplo si no hay conexion
        try:
            return repository.sales_history(90, origen=origen)
        except DBError:
            pass
        except Exception:  # noqa: BLE001 - si falta la vista, usa la serie completa
            try:
                return repository.sales_history(90)
            except DBError:
                pass
        hoy = datetime.date.today()
        hist = []
        for d in mock_data.get_prediction_data():
            f = analytics.parse_dia(d["dia"], hoy)
            if f is not None and d["historico"] is not None:
                hist.append((f, float(d["historico"])))
        hist.sort()
        return hist

    @staticmethod
    def _detalle(origen: str | None = None) -> list:
        try:
            return repository.sales_detail_last_days(30, origen=origen)
        except DBError:
            return mock_data.get_sales_detail()
        except Exception:  # noqa: BLE001
            try:
                return repository.sales_detail_last_days(30)
            except DBError:
                return mock_data.get_sales_detail()

    def _line_chart_card(self, hist: list, futuro: list, fuente_txt: str) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("Histórico y pronóstico · 30 días")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        layout.addWidget(title)

        fechas = [d for d, _ in hist]
        huecos = sum(1 for a, b in zip(fechas, fechas[1:]) if (b - a).days > 1)
        if huecos:
            fuente_txt += f" · {huecos} hueco(s) sin venta"
        fuente = QLabel(fuente_txt)
        fuente.setStyleSheet(f"color: {styles.MUTED}; font-size: 11px;")
        layout.addWidget(fuente)

        canvas = MplCanvas(height=3.2)
        if not hist:
            canvas.axes.text(0.5, 0.5, "Sin datos de ventas", ha="center",
                             va="center", fontsize=10, color=styles.MUTED,
                             transform=canvas.axes.transAxes)
            canvas.redraw()
            layout.addWidget(canvas)
            return card

        # corta la linea en huecos de mas de un dia para no inventar continuidad
        xs, ys = [], []
        for i, (d, v) in enumerate(hist):
            if i and (d - hist[i - 1][0]).days > 1:
                xs.append(d - datetime.timedelta(days=1))
                ys.append(None)
            xs.append(d)
            ys.append(v)
        cada = max(1, len(xs) // 18)
        canvas.axes.plot(
            xs, ys, color=styles.VERDE, linewidth=2.2,
            marker="o", markersize=4, markevery=cada, label="Histórico",
        )
        x_pred = [hist[-1][0]]
        y_pred = [hist[-1][1]]
        if futuro and (futuro[0][0] - hist[-1][0]).days > 1:
            x_pred.append(hist[-1][0] + datetime.timedelta(days=1))
            y_pred.append(None)
        x_pred += [d for d, _ in futuro]
        y_pred += [v for _, v in futuro]
        cada_pred = max(1, len(futuro) // 18) if futuro else 1
        canvas.axes.plot(
            x_pred, y_pred, color=styles.MENTA, linewidth=2, linestyle="--",
            marker="o", markersize=4, markevery=cada_pred, label="Pronóstico",
        )
        canvas.axes.axvline(hist[-1][0], color=styles.FAINT,
                            linestyle=":", linewidth=1)
        canvas.axes.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=10))
        canvas.axes.xaxis.set_major_formatter(
            FuncFormatter(lambda x, _pos: analytics.etiqueta_corta(
                mdates.num2date(x).date())))
        canvas.axes.tick_params(axis="x", labelrotation=30, labelsize=8)
        canvas.axes.yaxis.set_major_formatter(MplCanvas.miles_formatter())
        canvas.axes.margins(x=0.01, y=0.12)
        canvas.axes.legend(fontsize=8, frameon=False, loc="upper left")
        canvas.redraw()
        layout.addWidget(canvas)

        return card

    # -- tabla de productos predichos --------------------------------------

    def _table_card(self, hist: list, futuro: list, bt: dict,
                    detalle: list[dict]) -> QFrame:
        card = QFrame()
        card.setProperty("role", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)

        # backtest: si el modelo no gana a lo simple, se avisa preliminar
        total_30 = sum(v for _, v in futuro)

        header = QFrame()
        header.setStyleSheet(f"background-color: {styles.SURFACE_WARM}; border-bottom: 1px solid {styles.LINE};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("Estimación preliminar" if not bt["gana"] else "Qué esperar el próximo mes")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {styles.INK};")
        header_layout.addWidget(title)
        layout.addWidget(header)

        columns = ["Producto", "Últimos 30 días", "Próximos 30 días", "Cambio esperado"]
        # reparto por participacion de la misma ventana: 30 dias vs 30 dias
        rows = analytics.product_forecast_share(detalle, total_30, 5)

        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setAlternatingRowColors(True)
        table.setFrameShape(QFrame.NoFrame)

        for r, row in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(row["nombre"]))
            table.setItem(r, 1, self._right_aligned(f"${row['actual']:,}"))

            predicho_item = self._right_aligned(f"${row['predicho']:,}")
            predicho_item.setForeground(QColor(styles.VERDE))
            font = predicho_item.font()
            font.setBold(True)
            predicho_item.setFont(font)
            table.setItem(r, 2, predicho_item)

            crecimiento_txt, crecimiento_color = self._crec_texto_color(row["crecimiento"])
            crecimiento_item = self._right_aligned(crecimiento_txt)
            crecimiento_item.setForeground(QColor(crecimiento_color))
            font = crecimiento_item.font()
            font.setBold(True)
            crecimiento_item.setFont(font)
            table.setItem(r, 3, crecimiento_item)

        table.setMinimumHeight(min(40 * len(rows) + 40, 320))
        table.resizeColumnsToContents()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(table)

        inicio_30 = datetime.date.today() - datetime.timedelta(days=29)
        dias_venta = sum(1 for d, _ in hist if d >= inicio_30)
        cobertura = QLabel(
            f"Comparación de 30 días calendario · {dias_venta} día(s) con "
            f"venta en los últimos 30.")
        cobertura.setStyleSheet(
            f"color: {styles.MUTED}; font-size: 11px; padding: 0 18px 4px 18px;")
        layout.addWidget(cobertura)

        detalle_bt = QLabel(self._backtest_texto(bt))
        detalle_bt.setWordWrap(True)
        detalle_bt.setStyleSheet(f"color: {styles.MUTED}; font-size: 11px; padding: 0 18px 14px 18px;")
        layout.addWidget(detalle_bt)

        return card

    @staticmethod
    def _backtest_texto(bt: dict) -> str:
        if not bt.get("suficiente"):
            return (f"Backtest: datos insuficientes ({bt.get('n', 0)} observaciones, "
                    f"{bt.get('n_origenes', 0)} orígenes).")

        def pct(valor):
            return "—" if valor is None else f"{valor:.1f}%"

        return (f"Backtest: WAPE modelo {pct(bt.get('wape_modelo'))} · "
                f"ingenuo {pct(bt.get('wape_naive'))} · "
                f"media móvil 7 {pct(bt.get('wape_ma7'))} · "
                f"sesgo {pct(bt.get('sesgo_modelo'))} · "
                f"horizonte medio {bt.get('horizonte_medio', 0):.1f} días "
                f"(n={bt.get('n_origenes', 0)}).")

    def _build_actions_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        self.save_btn = QPushButton("Guardar pronóstico")
        self.save_btn.setProperty("role", "primary")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setEnabled(self._online)
        self.save_btn.clicked.connect(self._save_forecast)
        row.addWidget(self.save_btn)

        self.status_label = QLabel("base de datos" if self._online else "ejemplo (no se guarda)")
        self.status_label.setProperty("role", "micro")
        row.addStretch()
        row.addWidget(self.status_label)
        return row

    def _save_forecast(self) -> None:
        if not self._online:
            return
        hist = self._hist
        futuro = self._futuro
        if not hist or not futuro:
            QMessageBox.information(self, "Pronóstico", "No hay datos suficientes.")
            return
        detalle = self._detalle_cache
        bt = self._bt
        total_30 = sum(v for _, v in futuro)
        productos = analytics.product_forecast_share(detalle, total_30, len(detalle))
        try:
            id_pronostico = repository.save_forecast(
                hist, futuro, productos, bt, AppState.user_id)
        except DBError:
            self._online = False
            self.save_btn.setEnabled(False)
            self.status_label.setText("sin conexión")
            QMessageBox.warning(self, "Pronóstico", "Sin conexión a la base.")
            return
        except Exception as e:
            QMessageBox.warning(self, "Pronóstico", str(e))
            return
        self.status_label.setText(
            f"Guardado #{id_pronostico} · {len(futuro)} días · {len(productos)} productos")

    @staticmethod
    def _crec_texto_color(crec: float) -> tuple[str, str]:
        # signo siempre visible, color segun el signo (F02)
        return (f"{crec:+.1f}%", styles.SAGE if crec >= 0 else styles.CLAY)

    @staticmethod
    def _right_aligned(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item
