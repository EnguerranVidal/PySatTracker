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
from src.gui.objects import SimulationClock, AddObjectDialog
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
        self.satelliteDock.addObject.connect(self.addSelectedObjects)
        self.satelliteDock.removeObject.connect(self.removeSelectedObjects)

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

    def addSelectedObjects(self, noradIndices):
        for noradIndex in noradIndices:
            self.settings['VISUALIZATION']['SELECTED_OBJECTS'].append(noradIndex)
        self.saveSettings()
        self.satelliteDock.addItems(self.tleDatabase, noradIndices)

    def removeSelectedObjects(self, noradIndices):
        for index in noradIndices:
            self.settings['VISUALIZATION']['SELECTED_OBJECTS'].remove(index)
        self.saveSettings()

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
    addObject = pyqtSignal(list)
    objectSelected = pyqtSignal(list)
    toggleVisibility = pyqtSignal(list)
    showObjectInfo = pyqtSignal(list)
    removeObject = pyqtSignal(list)

    def __init__(self, mainWindow, title="Selected Satellites"):
        super().__init__(title, mainWindow)
        self.mainWindow = mainWindow
        container = QWidget()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())
        self.setWidget(container)

        topBar = QHBoxLayout()
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search selected satellites…")
        self.searchBar.textChanged.connect(self.filterSatelliteList)
        self.addButton = QPushButton("+")
        self.addButton.setFixedWidth(28)
        self.addButton.setToolTip("Add satellites")
        self.addButton.clicked.connect(self.openAddDialog)
        topBar.addWidget(self.searchBar)
        topBar.addWidget(self.addButton)

        self.listWidget = QListWidget()
        self.listWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addLayout(topBar)
        layout.addWidget(self.listWidget)
        self._items = []
        self.database = None

    def populate(self, database, selectedNoradIds):
        self.database = database
        self.listWidget.clear()
        for norad in selectedNoradIds:
            row = database.dataFrame[database.dataFrame["NORAD_CAT_ID"] == norad]
            if row.empty:
                continue
            row = row.iloc[0]
            item = QListWidgetItem(row["OBJECT_NAME"])
            item.setData(Qt.UserRole, norad)
            self.listWidget.addItem(item)

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
        actionRemove = menu.addAction("Remove Object")
        selectedAction = menu.exec_(self.listWidget.viewport().mapToGlobal(position))
        if selectedAction == actionToggle:
            self.toggleVisibility.emit(noradId)
        elif selectedAction == actionRemove:
            self.removeObject.emit([noradId])
            self.listWidget.takeItem(self.listWidget.row(item))

    def openAddDialog(self):
        if self.database is None:
            return
        dialog = AddObjectDialog(self.database, self)
        if dialog.exec_():
            if dialog.selectedNoradIndices:
                self.addObject.emit(dialog.selectedNoradIndices)

    def addItems(self, database, noradIndices):
        self.database = database
        for norad in noradIndices:
            if any(item.data(Qt.UserRole) == norad for item, _ in self._items):
                continue
            try:
                row = database.dataFrame.loc[database.dataFrame["NORAD_CAT_ID"] == norad].iloc[0]
            except IndexError:
                continue
            item = QListWidgetItem(row["OBJECT_NAME"])
            item.setData(Qt.UserRole, norad)
            self.listWidget.addItem(item)
            self._items.append((item, None))




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
