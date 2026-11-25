import numpy as np
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class GuidewirePanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Guidewire Shape", parent)
        lay = QVBoxLayout(self)
        
        self.fig = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        lay.addWidget(self.canvas)

        # A gently curved wire along +y (replace with real points later)
        y = np.linspace(0, 20, 30)
        x = 3 * np.sin(y * 0.25)
        z = 1.5 * np.cos(y * 0.15)

        ax = self.fig.add_subplot(111, projection="3d")
        ax.plot(x, y, z, lw=3)
        ax.plot([x[0]], [y[0]], [z[0]], "go")     # start
        ax.plot([x[-1]], [y[-1]], [z[-1]], "ro")  # tip
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")
        ax.set_box_aspect((1, 2.2, 1))