import os
import qdarktheme
import time

from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtWidgets import *

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

        # CENTRAL MAP WIDGET
        self.centralViewWidget = CentralViewWidget(self)
        self.setCentralWidget(self.centralViewWidget)

        # SATELLITE LIST WIDGET
        self.satelliteDock = SatelliteDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.satelliteDock)

        # FOLDER PATHS
        self.currentDir = currentDIr
        self.dataPath = os.path.join(self.currentDir, "data")
        self.noradPath = os.path.join(self.dataPath, "norad")
        self._checkEnvironment()

        # TLE DATABASE
        self.tleDatabase = None

        # STATUS BARS
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

    def setDatabase(self, database: TLEDatabase):
        self.tleDatabase = database
        self.satelliteDock.populate(self.tleDatabase)


class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        fig = plt.figure(figsize=(10, 5), facecolor='#1e1e1e')
        ax = fig.add_subplot(111, projection=ccrs.PlateCarree(), facecolor='#1e1e1e')
        ax.add_feature(cfeature.BORDERS.with_scale('50m'), edgecolor='white')
        ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#001122')
        ax.coastlines(color='white', resolution="50m")
        ax.set_global()

        ax.spines['geo'].set_edgecolor('white')
        ax.tick_params(colors='white', which='both')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')

        fig.subplots_adjust(left=0, right=0.5, top=0.5, bottom=0)
        fig.tight_layout(pad=1)

        self.canvas = FigureCanvas(fig)
        layout.addWidget(self.canvas)


class SatelliteDockWidget(QDockWidget):
    def __init__(self, mainWindow, title="Satellites"):
        super().__init__(title, mainWindow)
        self.mainWindow = mainWindow
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())

        # LAYOUT
        container = QWidget()
        self.setWidget(container)
        layout = QVBoxLayout(container)

        # SEARCH BAR
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search satellites...")
        self.searchBar.textChanged.connect(self.filterSatelliteList)
        layout.addWidget(self.searchBar)

        # LIST WIDGET
        self.listWidget = QListWidget()
        layout.addWidget(self.listWidget)
        self.allItemsList = []

    def populate(self, satelliteDatabase):
        self.listWidget.clear()
        self.allItemsList.clear()
        categories = {}
        for _, row in satelliteDatabase.dataFrame.iterrows():
            for tag in row["tags"]:
                if tag not in categories:
                    categories[tag] = []
                categories[tag].append(row["OBJECT_NAME"])

        # POPULATING LIST WIDGET
        for cat, satellites in categories.items():
            catItem = QListWidgetItem(f"[{cat.upper()}]")
            catItem.setFlags(Qt.ItemIsEnabled)
            self.listWidget.addItem(catItem)
            self.allItemsList.append((catItem, None))
            for sat in satellites:
                satelliteItem = QListWidgetItem(f"  {sat}")
                self.listWidget.addItem(satelliteItem)
                self.allItemsList.append((satelliteItem, cat))

    def filterSatelliteList(self, text):
        text = text.lower()
        for item, cat in self.allItemsList:
            if cat is None:
                categoryName = item.text()[1:-1].lower()
                show = any(sat_item.text().lower().find(text) >= 0 for sat_item, sat_cat in self.allItemsList if sat_cat == categoryName)
                item.setHidden(not show)
            else:
                item.setHidden(text not in item.text().lower())


class CentralViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.mapWidget = MapWidget()
        self.tabs.addTab(self.mapWidget, "Map")
        mainLayout.addWidget(self.tabs, stretch=1)
        # mainLayout.addWidget(self.timeline, stretch=0)
