"""Canvas matplotlib en tono papel, sin rejilla agresiva."""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from app import styles


def fmt_miles(v: float) -> str:
    # $4k si es multiplo de 1000, $4.5k si no (evita etiquetas repetidas)
    miles = float(v) / 1000.0
    if miles.is_integer():
        return f"${miles:.0f}k"
    return f"${miles:.1f}k"


def _miles_fmt(v, _) -> str:
    return fmt_miles(v)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, width: float = 5, height: float = 3, dpi: int = 100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=styles.SURFACE)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self._style_axes(self.axes)

    def _style_axes(self, ax) -> None:
        ax.set_facecolor(styles.SURFACE)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(styles.LINE)
        ax.spines["bottom"].set_linewidth(1)
        ax.tick_params(colors=styles.MUTED, labelsize=8, length=0, pad=6)
        # solo guia horizontal muy tenue
        ax.grid(True, axis="y", linestyle="-", linewidth=0.7, color=styles.CHART_GRID, alpha=0.9)
        ax.set_axisbelow(True)

    def clear(self) -> None:
        self.axes.clear()
        self._style_axes(self.axes)

    def redraw(self) -> None:
        self.fig.tight_layout(pad=1.2)
        self.draw()

    @staticmethod
    def miles_formatter() -> FuncFormatter:
        return FuncFormatter(_miles_fmt)
