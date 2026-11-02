import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-gpu-blocklist --enable-webgl --use-angle=swiftshader"
import tempfile
import plotly.graph_objects as go
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QGroupBox, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView

class GuidewirePanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Guidewire Shape", parent)
        lay = QVBoxLayout(self)
        self.view = QWebEngineView()
        lay.addWidget(self.view)
        
        fig = go.Figure(data=go.Streamtube(x=[0, 0, 0], y=[0, 1, 2], z=[0, 0, 0], u=[0, 0, 0], v=[1, 1, 1], w=[0, 0, 0]))
        # fig = go.Figure(data=go.Scatter(x=[0, 1, 2], y=[0, 1, 0]))
        
        path = os.path.join(tempfile.gettempdir(), "guidewire_plot.html")
        fig.write_html(path, include_plotlyjs="https://cdn.plot.ly/plotly-2.35.2.min.js")
        self.view.load(QUrl.fromLocalFile(path))