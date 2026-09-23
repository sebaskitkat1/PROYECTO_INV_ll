"""
Lienzo (canvas) de matplotlib reutilizable para embeber gráficas dentro
de las pantallas Qt, con un estilo visual consistente con la paleta de
la aplicación.
"""
from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from app import styles


class MplCanvas(FigureCanvasQTAgg):
    """Canvas base: una figura de matplotlib con un solo eje (Axes)."""

    def __init__(self, width: float = 5, height: float = 3, dpi: int = 100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor=styles.BG_WHITE)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self._style_axes(self.axes)

    def _style_axes(self, ax) -> None:
        ax.set_facecolor(styles.BG_WHITE)
        for spine_name in ("top", "right"):
            ax.spines[spine_name].set_visible(False)
        for spine_name in ("left", "bottom"):
            ax.spines[spine_name].set_color(styles.BORDER)
        ax.tick_params(colors=styles.TEXT_LIGHT_GRAY, labelsize=8, length=0)
        ax.grid(True, linestyle="--", linewidth=0.6, color="#F0F0F0")
        ax.set_axisbelow(True)

    def clear(self) -> None:
        self.axes.clear()
        self._style_axes(self.axes)

    def redraw(self) -> None:
        self.fig.tight_layout()
        self.draw()
