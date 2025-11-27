import qdarktheme

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QLabel, QWidget, QVBoxLayout

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        qdarktheme.setup_theme('dark', additional_qss="QToolTip {color: black;}")
        self.setWindowTitle("Satellite Tracker")
        self.setGeometry(300, 150, 1200, 700)
        self.mapWidget = MapWidget(self)
        self.setCentralWidget(self.mapWidget)



class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        fig = plt.figure(figsize=(10, 5), facecolor='#1e1e1e')
        ax = fig.add_subplot(111, projection=ccrs.PlateCarree(), facecolor='#1e1e1e')
        ax.coastlines(color='white', resolution="50m")
        ax.add_feature(cfeature.BORDERS.with_scale('50m'), edgecolor='white')
        ax.set_global()
        ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#001122')

        ax.spines['geo'].set_edgecolor('white')
        ax.tick_params(colors='white', which='both')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')

        fig.subplots_adjust(left=0, right=0.5, top=0.5, bottom=0)
        fig.tight_layout(pad=1)

        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)