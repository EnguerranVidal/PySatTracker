import os

import numpy as np
import qdarktheme
import time
import imageio
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, QDateTime, QTimer, QPoint, pyqtSignal, QThread
from PyQt5.QtWidgets import *

from src.gui.objects import SimulationClock, AddObjectDialog, OrbitWorker
from src.gui.utilities import generateDefaultSettingsJson, loadSettingsJson, saveSettingsJson


class MainWindow(QMainWindow):
    def __init__(self, currentDIr: str):
        super().__init__()
        self.settings = {}
        # FOLDER PATHS & SETTINGS
        self.currentDir = currentDIr
        self.settingsPath = os.path.join(self.currentDir, 'settings.json')
        self.dataPath = os.path.join(self.currentDir, 'data')
        self.noradPath = os.path.join(self.dataPath, 'norad')
        self._checkEnvironment()
        self.loadSettings()

        # APPEARANCE
        qdarktheme.setup_theme('dark', additional_qss='QToolTip {color: black;}')

        # CENTRAL VISUALIZATION WIDGET
        self.activeObjects, self.selectedObject = list(self.settings['VISUALIZATION']['SELECTED_OBJECTS']), None
        self.centralViewWidget = CentralViewWidget(self)
        self.setCentralWidget(self.centralViewWidget)

        # SATELLITE LIST WIDGET
        self.objectListDock = ObjectListDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objectListDock)
        self.objectListDock.objectSelected.connect(self.onObjectSelected)
        self.objectListDock.addObject.connect(self.addObjects)
        self.objectListDock.removeObject.connect(self.removeSelectedObjects)
        self.centralViewWidget.mapWidget.objectSelected.connect(self.objectListDock.selectNoradIndex)

        # OBJECT INFO DOCK WIDGET
        self.objectInfoDock = ObjectInfoDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objectInfoDock)

        self.tleDatabase = None
        self._setupStatusBar()
        self._restoreWindow()


    def _center(self):
        frameGeometry = self.frameGeometry()
        screenCenter = QDesktopWidget().availableGeometry().center()
        frameGeometry.moveCenter(screenCenter)
        self.move(frameGeometry.topLeft())

    def _setupStatusBar(self):
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

    def _restoreWindow(self):
        self.setWindowTitle('Satellite Tracker')
        if self.settings['WINDOW']['MAXIMIZED']:
            self.showMaximized()
        else:
            g = self.settings['WINDOW']['GEOMETRY']
            self.setGeometry(g['X'], g['Y'], g['WIDTH'], g['HEIGHT'])

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
        self.centralViewWidget.setDisplayConfiguration(self.settings['MAP']['CONFIG'])
        self.objectListDock.populate(self.tleDatabase, self.activeObjects)
        self.centralViewWidget.setActiveObjects(self.activeObjects)
        self.centralViewWidget.start()

    def loadSettings(self):
        self.settings = loadSettingsJson(self.settingsPath)

    def saveSettings(self):
        saveSettingsJson(self.settingsPath, self.settings)

    def addObjects(self, noradIndices: list[int]):
        for noradIndex in noradIndices:
            if noradIndex in self.activeObjects:
                continue
            self.activeObjects.append(noradIndex)
            if noradIndex not in self.settings['MAP']['CONFIG']:
                self.settings['MAP']['CONFIG'][noradIndex] = {'GROUND_TRACK': {'ENABLED': False, 'COLOR': (255, 0, 0)}, 'FOOTPRINT': {'ENABLED': False, 'COLOR': (0, 180, 255)}, 'SPOT': {'COLOR': (255, 0, 0)}}
        self.settings['VISUALIZATION']['SELECTED_OBJECTS'] = self.activeObjects
        self.saveSettings()
        self.objectListDock.populate(self.tleDatabase, self.activeObjects)
        self.centralViewWidget.setActiveObjects(self.activeObjects)

    def removeSelectedObjects(self, noradIndices: list[int]):
        for noradIndex in noradIndices:
            if noradIndex in self.activeObjects:
                self.activeObjects.remove(noradIndex)
            if self.selectedObject == noradIndex:
                self.selectedObject = None
                self.objectInfoDock.clear()
        self.settings['VISUALIZATION']['SELECTED_OBJECTS'] = self.activeObjects
        self.saveSettings()
        self.objectListDock.populate(self.tleDatabase, self.activeObjects)
        self.centralViewWidget.setActiveObjects(self.activeObjects)
        self.centralViewWidget.setSelectedObject(self.selectedObject)

    def onObjectSelected(self, noradIndex):
        if len(noradIndex) == 0:
            self.objectInfoDock.clear()
            self.centralViewWidget.setSelectedObject(None)
            return
        if isinstance(noradIndex[0], list):
            noradIndex = noradIndex[0]
        row = self.tleDatabase.dataFrame[self.tleDatabase.dataFrame['NORAD_CAT_ID'] == noradIndex[0]].iloc[0]
        self.objectInfoDock.setObject(row)
        self.centralViewWidget.setSelectedObject(noradIndex[0])

    def closeEvent(self, event):
        self.centralViewWidget.close()
        # SAVING SETTINGS
        self.settings['WINDOW']['MAXIMIZED'] = self.isMaximized()
        if not self.isMaximized():
            g = self.geometry()
            self.settings['WINDOW']['GEOMETRY'] = {'X': g.x(), 'Y': g.y(), 'WIDTH': g.width(), 'HEIGHT': g.height()}
        self.settings['VISUALIZATION']['SELECTED_OBJECTS'] = self.activeObjects
        self.saveSettings()
        event.accept()


class MapWidget(QWidget):
    objectSelected = pyqtSignal(list)

    def __init__(self, parent=None, mapImagePath='src/assets/world_map.png'):
        super().__init__(parent)
        self.mapImagePath = mapImagePath
        self.objectSpots, self.objectGroundTracks, self.objectFootprints, self.objectArrows = {}, {}, {}, {}
        self.selectedObject, self.displayConfiguration = None, {}
        self.sunIndicator, self.nightLayer = None, None
        self._setupMap()

    def _setupMap(self):
        # LOAD WORLD MAP
        if not os.path.exists(self.mapImagePath):
            raise FileNotFoundError(f'Map image not found at {self.mapImagePath}')
        img = imageio.imread(self.mapImagePath)
        img = np.rot90(img, k=-1)
        self.mapImage = pg.ImageItem(img)
        self.mapWidth, self.mapHeight = self.mapImage.width(), self.mapImage.height()
        # SETUP WORLD MAP VIEW
        self.view = GraphicsLayoutWidget()
        self.view.setBackground('#202124')
        self.plot = self.view.addPlot()
        self.plot.addItem(self.mapImage)
        self.plot.setAspectLocked(True)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)

    def _lonlatToCartesian(self, longitude, latitude):
        longitude, latitude = np.asarray(longitude), np.asarray(latitude)
        return (longitude + 180) / 360 * self.mapWidth, (latitude + 90) / 180 * self.mapHeight

    @staticmethod
    def _arrowAngle(x0, y0, x1, y1):
        return - np.degrees(np.arctan2(y1 - y0, x1 - x0)) + 180

    @staticmethod
    def _splitWrapSegment(longitudes, latitudes, threshold=180):
        longitudes, latitudes = np.asarray(longitudes), np.asarray(latitudes)
        if longitudes.size < 2:
            return [(longitudes, latitudes)]
        diffLongitudes = np.diff(longitudes)
        jumps = np.abs(diffLongitudes) > threshold
        if not np.any(jumps):
            return [(longitudes, latitudes)]
        splitIndices = np.where(jumps)[0] + 1
        longitudeSegments = np.split(longitudes, splitIndices)
        latitudeSegments = np.split(latitudes, splitIndices)
        for k, index in enumerate(splitIndices):
            # LINEAR INTERPOLATION
            previousLongitude, nextLongitude = longitudes[index - 1], longitudes[index]
            previousLatitude, nextLatitude = latitudes[index - 1], latitudes[index]
            if previousLongitude > nextLongitude:
                longitudeA, longitudeB = previousLongitude, nextLongitude + 360
                latitudeA, latitudeB = previousLatitude, nextLatitude
                borderA, borderB = 180, -180
            else:
                longitudeA, longitudeB = nextLongitude + 360, previousLongitude
                latitudeA, latitudeB = nextLatitude, previousLatitude
                borderA, borderB = -180, 180
            a = (latitudeB - latitudeA) / (longitudeB - longitudeA)
            b = latitudeA - a * longitudeA
            latitudeBorder = a * 180 + b
            # ADDING BORDER POINTS TO SEGMENTS
            longitudeSegments[k] = np.append(longitudeSegments[k], borderA)
            latitudeSegments[k] = np.append(latitudeSegments[k], latitudeBorder)
            longitudeSegments[k + 1] = np.insert(longitudeSegments[k + 1], 0, borderB)
            latitudeSegments[k + 1] = np.insert(latitudeSegments[k + 1], 0, latitudeBorder)
        return list(zip(longitudeSegments, latitudeSegments))

    def _updateSunAndNight(self, mapData):
        subPointLongitude, subPointLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
        longitudes, latitudes = mapData['NIGHT']['LONGITUDE'], mapData['NIGHT']['LATITUDE']
        x, y = self._lonlatToCartesian(longitudes, latitudes)
        xSun, ySun = self._lonlatToCartesian(subPointLongitude, subPointLatitude)
        fillLevel = 0 if subPointLatitude > 0 else self.mapHeight
        if self.nightLayer is None:
            self.nightLayer = pg.PlotCurveItem(x, y, pen=None, fillLevel=fillLevel, brush=pg.mkBrush(0, 0, 0, 120))
            self.plot.addItem(self.nightLayer)
        else:
            self.nightLayer.setData(x, y)
            self.nightLayer.setFillLevel(fillLevel)
        if self.sunIndicator is None:
            self.sunIndicator = pg.ScatterPlotItem(size=14, brush=pg.mkBrush(255, 215, 0), pen=pg.mkPen(255, 200, 0, width=2), symbol="o",)
            self.plot.addItem(self.sunIndicator)
        self.sunIndicator.setData([xSun], [ySun])

    def updateMap(self, positions: dict, visibleNorads: set[int], selectedNorad: int | None, displayConfiguration: dict):
        self.selectedObject, self.displayConfiguration = selectedNorad, displayConfiguration
        # REMOVING EVERYTHING
        for noradIndex in list(self.objectSpots.keys()):
            if noradIndex not in visibleNorads:
                self._removeItems(self.objectSpots.pop(noradIndex))
                self._removeItems(self.objectGroundTracks.pop(noradIndex, None))
                self._removeItems(self.objectFootprints.pop(noradIndex, None))
                self._removeItems(self.objectArrows.pop(noradIndex, None))
        # NIGHT LAYER AND SUN POSITION
        self._updateSunAndNight(positions['MAP'])
        # DRAW VISIBLE NORAD OBJECTS
        for noradIndex in visibleNorads:
            if noradIndex not in positions:
                continue
            self._updateObjectDisplay(noradIndex, positions[noradIndex])

    def _updateObjectDisplay(self, noradIndex, noradPosition):
        isSelected = (noradIndex == self.selectedObject)
        noradObjectConfiguration = self.displayConfiguration[str(noradIndex)]
        # GROUND TRACKS
        if noradObjectConfiguration['GROUND_TRACK']['ENABLED'] is True or isSelected:
            groundLongitudes, groundLatitudes = noradPosition['GROUND_TRACK']['LONGITUDE'], noradPosition['GROUND_TRACK']['LATITUDE']
            groundSegments = self._splitWrapSegment(groundLongitudes, groundLatitudes)
            for item in self.objectGroundTracks.get(noradIndex, []):
                self.plot.removeItem(item)
            self.objectGroundTracks[noradIndex] = []
            for segmentLongitudes, segmentLatitudes in groundSegments:
                gx, gy = self._lonlatToCartesian(segmentLongitudes, segmentLatitudes)
                curve = pg.PlotCurveItem(gx, gy, pen=pg.mkPen((255, 0, 0), width=1))
                self.objectGroundTracks[noradIndex].append(curve)
                self.plot.addItem(self.objectGroundTracks[noradIndex][-1])
            # GROUND TRACK ARROW
            lastLongitude, lastLatitude = groundSegments[-1]
            x0, y0 = self._lonlatToCartesian(lastLongitude[-2], lastLatitude[-2])
            x1, y1 = self._lonlatToCartesian(lastLongitude[-1], lastLatitude[-1])
            angle = self._arrowAngle(x0, y0, x1, y1)
            if noradIndex not in self.objectArrows:
                arrow = pg.ArrowItem(angle=angle, tipAngle=30, headLen=12, tailLen=0, tailWidth=0, pen=pg.mkPen(255, 0, 0), brush=pg.mkBrush(255, 0, 0))
                self.objectArrows[noradIndex] = arrow
                self.plot.addItem(self.objectArrows[noradIndex])
            self.objectArrows[noradIndex].setStyle(angle=angle)
            self.objectArrows[noradIndex].setPos(x1, y1)
        else:
            self._removeItems(self.objectGroundTracks.get(noradIndex))
            self._removeItems(self.objectArrows.get(noradIndex))
            self.objectGroundTracks.pop(noradIndex, None)
            self.objectArrows.pop(noradIndex, None)
        # VISIBILITY FOOTPRINT
        if noradObjectConfiguration['FOOTPRINT']['ENABLED'] is True or isSelected:
            footLongitudes, footLatitudes = noradPosition['VISIBILITY']['LONGITUDE'], noradPosition['VISIBILITY']['LATITUDE']
            footSegments = self._splitWrapSegment(footLongitudes, footLatitudes)
            for item in self.objectFootprints.get(noradIndex, []):
                self.plot.removeItem(item)
            self.objectFootprints[noradIndex] = []
            for segmentLongitudes, segmentLatitudes in footSegments:
                fx, fy = self._lonlatToCartesian(segmentLongitudes, segmentLatitudes)
                curve = pg.PlotCurveItem(fx, fy, pen=pg.mkPen((0, 180, 255), width=1))
                self.objectFootprints[noradIndex].append(curve)
                self.plot.addItem(self.objectFootprints[noradIndex][-1])
        else:
            self._removeItems(self.objectFootprints.get(noradIndex))
            self.objectFootprints.pop(noradIndex, None)
        # OBJECT POSITIONS
        color = (255, 0, 0) if self.selectedObject == noradIndex else (150, 150, 150)
        x, y = self._lonlatToCartesian(noradPosition['POSITION']['LONGITUDE'], noradPosition['POSITION']['LATITUDE'])
        if noradIndex not in self.objectSpots:
            spot = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(*color))
            spot.sigClicked.connect(self._onObjectClicked)
            self.objectSpots[noradIndex] = spot
            self.plot.addItem(self.objectSpots[noradIndex])
        self.objectSpots[noradIndex].setData([{'pos': (x, y), 'data': noradIndex}], brush=pg.mkBrush(*color), pen=None)

    def _onObjectClicked(self, plot, points):
        if not points:
            return
        noradIndex = points[0].data()
        if noradIndex is None:
            return
        self.objectSelected.emit([noradIndex])

    def _removeItems(self, items):
        if not items:
            return
        if isinstance(items, list):
            for item in items:
                self.plot.removeItem(item)
        else:
            self.plot.removeItem(items)



class ObjectListDockWidget(QDockWidget):
    addObject = pyqtSignal(list)
    objectSelected = pyqtSignal(list)
    toggleVisibility = pyqtSignal(list)
    showObjectInfo = pyqtSignal(list)
    removeObject = pyqtSignal(list)

    def __init__(self, mainWindow, title='Selected Satellites'):
        super().__init__(title, mainWindow)
        self.mainWindow = mainWindow
        container = QWidget()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())
        self.setWidget(container)

        topBar = QHBoxLayout()
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText('Search selected satellites…')
        self.searchBar.textChanged.connect(self.filterObjectList)
        self.addButton = QPushButton('+')
        self.addButton.setFixedWidth(28)
        self.addButton.setToolTip('Add satellites')
        self.addButton.clicked.connect(self.openAddDialog)
        topBar.addWidget(self.searchBar)
        topBar.addWidget(self.addButton)

        self.listWidget = QListWidget()
        self.listWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
        self.listWidget.itemSelectionChanged.connect(self.onSelectionChanged)

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
            row = database.dataFrame[database.dataFrame['NORAD_CAT_ID'] == norad]
            if row.empty:
                continue
            row = row.iloc[0]
            item = QListWidgetItem(row['OBJECT_NAME'])
            item.setData(Qt.UserRole, norad)
            self.listWidget.addItem(item)

    def filterObjectList(self, text):
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
        actionToggle = menu.addAction('Toggle Visibility')
        actionRemove = menu.addAction('Remove Object')
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
                row = database.dataFrame.loc[database.dataFrame['NORAD_CAT_ID'] == norad].iloc[0]
            except IndexError:
                continue
            item = QListWidgetItem(row['OBJECT_NAME'])
            item.setData(Qt.UserRole, norad)
            self.listWidget.addItem(item)
            self._items.append((item, None))

    def onSelectionChanged(self):
        items = self.listWidget.selectedItems()
        if not items:
            self.objectSelected.emit([])
            return
        noradId = items[0].data(Qt.UserRole)
        self.objectSelected.emit([noradId])

    def selectNoradIndex(self, noradIndex):
        self.listWidget.blockSignals(True)
        self.listWidget.clearSelection()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.data(Qt.UserRole) == noradIndex:
                item.setSelected(True)
                self.listWidget.setCurrentItem(item)
                self.listWidget.scrollToItem(item)
                break
        self.listWidget.blockSignals(False)
        self.objectSelected.emit([noradIndex])


class ObjectInfoDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__('Object Info', parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self._labels = {}
        self._setupUi()

    def _setupUi(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self._createGroup('Identification', [('Name', 'OBJECT_NAME'), ('NORAD ID', 'NORAD_CAT_ID'), ('COSPAR ID', 'OBJECT_ID'),]))
        layout.addWidget(self._createGroup('Status', [("Object Type", "OBJECT_TYPE"), ('Owner', 'OWNER'), ('Operational Status', 'OPS_STATUS_CODE'),]))
        layout.addWidget(self._createGroup('Orbit (TLE)', [('Inclination (deg)', 'INCLINATION'), ('Eccentricity', 'ECCENTRICITY'), ('Mean Motion (rev/day)', 'MEAN_MOTION'), ('B*', 'BSTAR'),]))
        layout.addStretch()
        self.setWidget(container)

    def _createGroup(self, title, fields):
        groupBox = QGroupBox(title)
        formLayout = QFormLayout()
        for labelText, fieldKey in fields:
            label = QLabel("---")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            formLayout.addRow(QLabel(labelText + ":"), label)
            self._labels[fieldKey] = label
        groupBox.setLayout(formLayout)
        return groupBox

    def clear(self):
        for label in self._labels.values():
            label.setText("---")

    def setObject(self, row):
        if row is None:
            self.clear()
            return
        for key, label in self._labels.items():
            value = row.get(key, None)
            if value is None or value == "":
                label.setText("—")
            else:
                label.setText(str(value))


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

        # VISUALIZATION CONFIGURATION
        self.activeObjects = set()
        self.selectedObject = None
        self.displayConfiguration = {}
        self.lastPositions = {}

        # MAIN TABS
        self.mapWidget = MapWidget()
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(self.mapWidget, 'Map')

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
        self.lastPositions = positions
        self._refreshMap()

    def setDatabase(self, database):
        self.orbitWorker.database = database

    def setSelectedObject(self, noradIndex):
        self.selectedObject = noradIndex
        self._refreshMap()

    def setActiveObjects(self, noradIndices):
        self.activeObjects = set(noradIndices)
        self.orbitWorker.noradIndices = list(self.activeObjects)
        self._refreshMap()

    def setDisplayConfiguration(self, displayConfiguration):
        self.displayConfiguration = displayConfiguration
        self._refreshMap()

    def _refreshMap(self):
        if self.mapVisible and self.lastPositions:
            self.mapWidget.updateMap(self.lastPositions, self.activeObjects, self.selectedObject, self.displayConfiguration)

    def start(self):
        self.clock.play()

    def closeEvent(self, event):
        self.orbitWorker.stop()
        self.workerThread.quit()
        self.workerThread.wait()
        super().closeEvent(event)
