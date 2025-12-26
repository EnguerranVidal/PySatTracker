import os
from datetime import datetime

import numpy as np
import qdarktheme
import time
import imageio
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, QDateTime, QTimer, QPoint, pyqtSignal, QThread
from PyQt5.QtWidgets import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from src.gui.objects import SimulationClock, AddObjectDialog, OrbitWorker
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

        # CENTRAL VISUALIZATION WIDGET
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

    def setDatabase(self, database):
        self.tleDatabase = database
        self.centralViewWidget.setDatabase(database)
        self.centralViewWidget.setVisibleNoradIndices(self.settings["VISUALIZATION"]["SELECTED_OBJECTS"])
        self.satelliteDock.populate(self.tleDatabase, self.settings["VISUALIZATION"]["SELECTED_OBJECTS"])
        self.centralViewWidget.start()

    def loadSettings(self):
        self.settings = loadSettingsJson(self.settingsPath)

    def saveSettings(self):
        saveSettingsJson(self.settingsPath, self.settings)

    def addSelectedObjects(self, noradIndices):
        for noradIndex in noradIndices:
            self.settings['VISUALIZATION']['SELECTED_OBJECTS'].append(noradIndex)
        self.saveSettings()
        self.satelliteDock.addItems(self.tleDatabase, noradIndices)
        self.centralViewWidget.setVisibleNoradIndices(self.settings["VISUALIZATION"]["SELECTED_OBJECTS"])

    def removeSelectedObjects(self, noradIndices):
        for index in noradIndices:
            self.settings['VISUALIZATION']['SELECTED_OBJECTS'].remove(index)
        self.saveSettings()
        self.centralViewWidget.setVisibleNoradIndices(self.settings["VISUALIZATION"]["SELECTED_OBJECTS"])

    def closeEvent(self, event):
        self.centralViewWidget.close()
        # SAVING SETTINGS
        self.settings["WINDOW"]["MAXIMIZED"] = self.isMaximized()
        if not self.isMaximized():
            g = self.geometry()
            self.settings["WINDOW"]["GEOMETRY"] = {"X": g.x(), "Y": g.y(), "WIDTH": g.width(), "HEIGHT": g.height()}
        self.saveSettings()
        event.accept()


class MapWidget(QWidget):
    def __init__(self, parent=None, mapImagePath="src/assets/world_map.png"):
        super().__init__(parent)
        self.mapImagePath = mapImagePath
        self.objectSpots, self.objectGroundTracks, self.objectFootprints = {}, {}, {}
        self._setupMap()

    def _setupMap(self):
        # LOAD WORLD MAP
        if not os.path.exists(self.mapImagePath):
            raise FileNotFoundError(f"Map image not found at {self.mapImagePath}")
        img = imageio.imread(self.mapImagePath)
        img = np.rot90(img, k=-1)
        self.mapImage = pg.ImageItem(img)
        self.mapWidth, self.mapHeight = self.mapImage.width(), self.mapImage.height()
        # SETUP WORLD MAP VIEW
        self.view = GraphicsLayoutWidget()
        self.plot = self.view.addPlot()
        self.plot.addItem(self.mapImage)
        self.plot.setAspectLocked(True)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)

    def lonlatToCartesian(self, longitude, latitude):
        return (longitude + 180) / 360 * self.mapWidth, (latitude + 90) / 180 * self.mapHeight

    def updatePositions(self, data: dict):
        # DELETING REMOVED OBJECT VISUALIZATION
        for norad in list(self.objectSpots.keys()):
            if norad not in data:
                self.plot.removeItem(self.objectSpots[norad])
                self.plot.removeItem(self.objectGroundTracks[norad])
                self.plot.removeItem(self.objectFootprints[norad])
                del self.objectSpots[norad]
                del self.objectGroundTracks[norad]
                del self.objectFootprints[norad]
        # ADDING / UPDATING OBJECT VISUALIZATION
        for norad, content in data.items():
            x, y = self.lonlatToCartesian(content['POSITION']['LONGITUDE'], content['POSITION']['LATITUDE'])
            if norad not in self.objectSpots:
                spot = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(255, 0, 0))
                self.objectSpots[norad] = spot
                self.plot.addItem(self.objectSpots[norad])
            self.objectSpots[norad].setData([x], [y])
            gx, gy = self.lonlatToCartesian(content['GROUND_TRACK']['LONGITUDE'], content['GROUND_TRACK']['LATITUDE'])
            if norad not in self.objectGroundTracks:
                line = pg.PlotCurveItem(pen=pg.mkPen((0, 180, 255), width=1))
                self.objectGroundTracks[norad] = line
                # self.plot.addItem(self.objectGroundTracks[norad])
            self.objectGroundTracks[norad].setData(gx, gy)
            fx, fy = self.lonlatToCartesian(content['VISIBILITY']['LONGITUDE'], content['VISIBILITY']['LATITUDE'])
            if norad not in self.objectFootprints:
                pen = pg.mkPen((255, 255, 255), width=1)
                self.objectFootprints[norad] = pg.PlotCurveItem(pen=pen)
                self.plot.addItem(self.objectFootprints[norad])
            self.objectFootprints[norad].setData(fx, fy)


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
            self.toggleVisibility.emit([noradId])
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
        # CLOCK & ORBITS CALCULATIONS WORKER
        self.clock = SimulationClock()
        self.workerThread = QThread(self)
        self.orbitWorker = OrbitWorker(None)
        self.orbitWorker.moveToThread(self.workerThread)
        self.clock.timeChanged.connect(self.orbitWorker.compute)
        self.workerThread.start()

        # MAIN TABS
        self.mapWidget = MapWidget()
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(self.mapWidget, "Map")

        # MAP LINKING
        self.orbitWorker.positionsReady.connect(self._onPositionsReady)
        self.tabWidget.currentChanged.connect(self._onTabChanged)
        self.mapVisible = True

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabWidget)

    def _onTabChanged(self, index):
        self.mapVisible = (self.tabWidget.widget(index) is self.mapWidget)

    def _onPositionsReady(self, positions: dict):
        if self.mapVisible:
            self.mapWidget.updatePositions(positions)

    def setDatabase(self, database):
        self.orbitWorker.database = database

    def setVisibleNoradIndices(self, indices):
        self.orbitWorker.visibleNoradIndices = indices

    def start(self):
        self.clock.play()

    def closeEvent(self, event):
        self.orbitWorker.stop()
        self.workerThread.quit()
        self.workerThread.wait()
        super().closeEvent(event)
