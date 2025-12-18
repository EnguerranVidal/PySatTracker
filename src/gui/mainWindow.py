import os
import qdarktheme
import time

from PyQt5.QtCore import Qt, QDateTime, QTimer, QPoint, pyqtSignal
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QCloseEvent

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from src.core.tleDatabase import TLEDatabase
from src.gui.objects import SimulationClock
from src.gui.utilities import generateDefaultSettingsJson, loadSettingsJson, saveSettingsJson


class MainWindow(QMainWindow):
    def __init__(self, currentDIr: str):
        super().__init__()
        self.settings = {}
        # FOLDER PATHS & SETTINGS
        self.currentDir = currentDIr
        self.settingsPath = os.path.join(self.currentDir, "settings.json")
        self.dataPath = os.path.join(self.currentDir, "data")
        self.noradPath = os.path.join(self.dataPath, "norad")
        self._checkEnvironment()
        self.loadSettings()

        # APPEARANCE
        qdarktheme.setup_theme('dark', additional_qss="QToolTip {color: black;}")

        # CENTRAL MAP WIDGET
        self.centralViewWidget = CentralViewWidget(self)
        self.setCentralWidget(self.centralViewWidget)

        # SATELLITE LIST WIDGET
        self.satelliteDock = SatelliteDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.satelliteDock)

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

        # WINDOW DIMENSIONS / MAXIMIZED
        self.setWindowTitle("Satellite Tracker")
        if self.settings['WINDOW']['MAXIMIZED']:
            self.showMaximized()
        else:
            g = self.settings['WINDOW']['GEOMETRY']
            self.setGeometry(g["X"], g["Y"], g["WIDTH"], g["HEIGHT"])

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
        if not os.path.exists(self.settingsPath):
            generateDefaultSettingsJson(self.settingsPath)
        if not os.path.exists(self.dataPath):
            os.mkdir(self.dataPath)
        if not os.path.exists(self.noradPath):
            os.mkdir(self.noradPath)

    def setDatabase(self, database: TLEDatabase):
        self.tleDatabase = database
        self.satelliteDock.populate(self.tleDatabase, self.settings["VISUALIZATION"]["SELECTED_OBJECTS"])

    def loadSettings(self):
        self.settings = loadSettingsJson(self.settingsPath)

    def saveSettings(self):
        saveSettingsJson(self.settingsPath, self.settings)

    def closeEvent(self, event):
        self.settings["WINDOW"]["MAXIMIZED"] = self.isMaximized()
        if not self.isMaximized():
            g = self.geometry()
            self.settings["WINDOW"]["GEOMETRY"] = {"X": g.x(), "Y": g.y(), "WIDTH": g.width(), "HEIGHT": g.height()}
        self.saveSettings()
        event.accept()


class MapWidget(QWidget):
    def __init__(self, clock, parent=None):
        super().__init__(parent)
        self.clock = clock
        self.clock.timeChanged.connect(self.updateMap)

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
        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)

    def updateMap(self, simulationTime: float):
        pass


class SatelliteDockWidget(QDockWidget):
    toggleVisibilityRequested = pyqtSignal(int)
    removeRequested = pyqtSignal(int)

    def __init__(self, mainWindow, title="Selected Satellites"):
        super().__init__(title, mainWindow)
        self.mainWindow = mainWindow
        container = QWidget()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())
        self.setWidget(container)
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search selected satellites…")
        self.searchBar.textChanged.connect(self.filterSatelliteList)
        self.listWidget = QListWidget()
        self.listWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.searchBar)
        layout.addWidget(self.listWidget)
        self._items = []

    def populate(self, database, selectedNoradIds):
        self.listWidget.clear()
        self._items.clear()
        categories = {}
        for norad in selectedNoradIds:
            try:
                row = database.dataFrame.loc[
                    database.dataFrame["NORAD_CAT_ID"] == norad
                    ].iloc[0]
            except IndexError:
                continue
            for tag in row["tags"]:
                categories.setdefault(tag, []).append(row)
        for category, rows in sorted(categories.items()):
            header = QListWidgetItem(f"[{category.upper()}]")
            header.setFlags(Qt.ItemIsEnabled)
            self.listWidget.addItem(header)
            self._items.append((header, None))
            for row in rows:
                item = QListWidgetItem(f"  {row['OBJECT_NAME']}")
                item.setData(Qt.UserRole, row["NORAD_CAT_ID"])
                self.listWidget.addItem(item)
                self._items.append((item, category))

    def filterSatelliteList(self, text):
        text = text.lower()
        visibleCategories = set()
        for item, category in self._items:
            if category is None:
                continue
            match = text in item.text().lower()
            item.setHidden(not match)
            if match:
                visibleCategories.add(category)
        for item, category in self._items:
            if category is None:
                catName = item.text()[1:-1].lower()
                item.setHidden(catName not in visibleCategories)

    def showContextMenu(self, position: QPoint):
        item = self.listWidget.itemAt(position)
        if not item:
            return
        noradId = item.data(Qt.UserRole)
        if noradId is None:
            return
        menu = QMenu(self)
        actionToggle = menu.addAction("Toggle Visibility")
        actionRemove = menu.addAction("Remove from Selection")
        selectedAction = menu.exec_(self.listWidget.viewport().mapToGlobal(position))
        if selectedAction == actionToggle:
            self.toggleVisibilityRequested.emit(noradId)
        elif selectedAction == actionRemove:
            self.removeSatellite(noradId)


class CentralViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        self.clock = SimulationClock()
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.mapWidget = MapWidget(self.clock)
        self.tabs.addTab(self.mapWidget, "Map")
        mainLayout.addWidget(self.tabs, stretch=1)
