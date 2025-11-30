import os

import qdarktheme
import time

from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtWidgets import QMainWindow, QLabel, QWidget, QVBoxLayout, QDesktopWidget

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature

from src.core.tleDatabase import TLEDatabase


class MainWindow(QMainWindow):
    def __init__(self, currentDIr: str):
        super().__init__()
        qdarktheme.setup_theme('dark', additional_qss="QToolTip {color: black;}")
        self.setWindowTitle("Satellite Tracker")
        self.setGeometry(300, 150, 1200, 700)
        self.mapWidget = MapWidget(self)
        self.setCentralWidget(self.mapWidget)

        # FOLDER PATHS
        self.currentDir = currentDIr
        self.dataPath = os.path.join(self.currentDir, "data")
        self.noradPath = os.path.join(self.dataPath, "norad")
        self._checkEnvironment()

        # TLE DATABASE
        self.tleDatabase = TLEDatabase(self.noradPath)

        # STATUS BAR
        self.lastUpdate = time.perf_counter()
        self.avgFps = 0.0
        self.fpsLabel = QLabel('Fps : ---')
        self.fpsLabel.setStyleSheet('border: 0;')
        self.statusBar().addPermanentWidget(self.fpsLabel)
        self.datetime = QDateTime.currentDateTime()
        self.dateLabel = QLabel(self.datetime.toString('dd.MM.yyyy  hh:mm:ss'))
        self.dateLabel.setStyleSheet('border: 0;')
        self.statusBar().addPermanentWidget(self.dateLabel)
        self.statusBar().showMessage('Ready')
        self.statusDateTimer = QTimer()
        self.statusDateTimer.timeout.connect(self._updateStatus)
        self.statusDateTimer.start(1000)

    def _center(self):
        frameGeometry = self.frameGeometry()
        screenCenter = QDesktopWidget().availableGeometry().center()
        frameGeometry.moveCenter(screenCenter)
        self.move(frameGeometry.topLeft())

    def _updateStatus(self):
        self.datetime = QDateTime.currentDateTime()
        self.dateLabel.setText(self.datetime.toString('dd.MM.yyyy  hh:mm:ss'))
        now = time.perf_counter()
        fps = 1000 / (now - self.lastUpdate)
        self.lastUpdate = now
        self.avgFps = self.avgFps * 0.8 + fps * 0.2
        self.fpsLabel.setText('Fps : %0.2f ' % self.avgFps)

    def _checkEnvironment(self):
        if not os.path.exists(self.dataPath):
            os.mkdir(self.dataPath)
        if not os.path.exists(self.noradPath):
            os.mkdir(self.noradPath)


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