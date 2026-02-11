import copy
import os
from datetime import datetime

import numpy as np
import qdarktheme
import time
import imageio
import pyqtgraph as pg
from PyQt5.QtGui import QDesktopServices, QIcon
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, QDateTime, QTimer, QPoint, pyqtSignal, QThread, QSignalBlocker, QUrl
from PyQt5.QtWidgets import *

from gui.earth3D import View3dWidget, Object3dViewConfigDockWidget
from src.gui.objects import SimulationClock, AddObjectDialog, OrbitWorker, TimelineWidget
from src.gui.utilities import generateDefaultSettingsJson, loadSettingsJson, saveSettingsJson, getKeyFromValue


class MainWindow(QMainWindow):
    def __init__(self, currentDIr: str):
        super().__init__()
        self.settings = {}
        self.icons = {}
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
        self.activeObjects, self.selectedObject = list(self.settings['VISUALIZATION']['ACTIVE_OBJECTS']), None
        self.centralViewWidget = CentralViewWidget(parent=self, currentDir=self.currentDir)
        self.setCentralWidget(self.centralViewWidget)

        # SATELLITE LIST WIDGET
        self.objectListDock = ObjectListDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objectListDock)
        self.objectListDock.objectSelected.connect(self.onObjectSelected)
        self.objectListDock.addObject.connect(self.addObjects)
        self.objectListDock.removeObject.connect(self.removeSelectedObjects)
        self.centralViewWidget.map2dWidget.objectSelected.connect(self.objectListDock.selectNoradIndex)
        self.centralViewWidget.view3dWidget.objectSelected.connect(self.objectListDock.selectNoradIndex)

        # OBJECT DOCK WIDGETS
        self.objectInfoDock = ObjectInfoDockWidget(self)
        self.object2dMapConfigDock = Object2dMapConfigDockWidget(self)
        self.object3dViewConfigDock = Object3dViewConfigDockWidget(self)
        self.object2dMapConfigDock.configChanged.connect(self._on2dMapObjectConfigChanged)
        self.object3dViewConfigDock.configChanged.connect(self._on3dViewObjectConfigChanged)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objectInfoDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.object2dMapConfigDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.object3dViewConfigDock)

        self.tleDatabase = None
        self._createIcons()
        self._setupMenuBar()
        self._setupStatusBar()
        self._restoreWindow()
        self._updateActionStates()

    def _updateTabs(self, tabIndex):
        self.settings['VISUALIZATION']['CURRENT_TAB'] = self.centralViewWidget.TABS[tabIndex]
        self.setObjectConfigWidgetsVisibility()

    def _setupMenuBar(self):
        self.menuBar = self.menuBar()
        self._selectionDependentActions = []

        # VIEW MENU
        self.viewMenu = self.menuBar.addMenu('&View')
        self.map2dMenu = self.viewMenu.addMenu('&2D Map')
        self.resetMapConfigAction = QAction('&Reset Configuration', self)
        self.setMapConfigAsDefaultAction = QAction('&Set as Default', self)
        self.showNightLayerAction = QAction('&Show Night Layer', self, checkable=True)
        self.sunIndicatorAction = QAction('&Show Sun Indicator', self, checkable=True)
        self.vernalPointAction = QAction('&Show Vernal Point', self, checkable=True)
        self.showGroundTracksAction = QAction('&Show Ground Tracks', self, checkable=True)
        self.showFootprintsAction = QAction('&Show Footprints', self, checkable=True)
        self.view3dMenu = self.viewMenu.addMenu('&3D View')
        self.showEarthAction = QAction('&Show Earth', self, checkable=True)
        self.showEarthGridAction = QAction('&Show Earth Grid', self, checkable=True)
        self.showAxesAction = QAction('&Show Axes', self, checkable=True)
        self.showOrbitalPathsAction = QAction('&Show Orbital Paths', self, checkable=True)

        self.showNightLayerAction.setChecked(self.settings['2D_MAP']['SHOW_NIGHT'])
        self.sunIndicatorAction.setChecked(self.settings['2D_MAP']['SHOW_SUN'])
        self.vernalPointAction.setChecked(self.settings['2D_MAP']['SHOW_VERNAL'])
        self.showGroundTracksAction.setChecked(self.settings['2D_MAP']['SHOW_GROUND_TRACK'])
        self.showFootprintsAction.setChecked(self.settings['2D_MAP']['SHOW_FOOTPRINT'])

        self.showEarthAction.setChecked(self.settings['3D_VIEW']['SHOW_EARTH'])
        self.showEarthGridAction.setChecked(self.settings['3D_VIEW']['SHOW_EARTH_GRID'])
        self.showAxesAction.setChecked(self.settings['3D_VIEW']['SHOW_AXES'])
        self.showOrbitalPathsAction.setChecked(self.settings['3D_VIEW']['SHOW_ORBITS'])

        self.resetMapConfigAction.triggered.connect(self._resetObject2dMapConfig)
        self.setMapConfigAsDefaultAction.triggered.connect(self._setObject2dMapConfigAsDefault)
        self._selectionDependentActions.append(self.resetMapConfigAction)
        self._selectionDependentActions.append(self.setMapConfigAsDefaultAction)
        self.showNightLayerAction.toggled.connect(self._checkNightLayer)
        self.sunIndicatorAction.toggled.connect(self._checkSunIndicator)
        self.vernalPointAction.toggled.connect(self._checkVernalPoint)
        self.showGroundTracksAction.toggled.connect(self._checkGroundTracks)
        self.showFootprintsAction.toggled.connect(self._checkFootprints)
        self.showEarthAction.toggled.connect(self._checkEarth)
        self.showEarthGridAction.toggled.connect(self._checkEarthGrid)
        self.showAxesAction.toggled.connect(self._checkAxes)
        self.showOrbitalPathsAction.toggled.connect(self._checkOrbitalPaths)

        self.map2dMenu.addAction(self.resetMapConfigAction)
        self.map2dMenu.addAction(self.setMapConfigAsDefaultAction)
        self.map2dMenu.addSeparator()
        self.map2dMenu.addAction(self.showNightLayerAction)
        self.map2dMenu.addAction(self.sunIndicatorAction)
        self.map2dMenu.addAction(self.vernalPointAction)
        self.map2dMenu.addSeparator()
        self.map2dMenu.addAction(self.showGroundTracksAction)
        self.map2dMenu.addAction(self.showFootprintsAction)

        self.view3dMenu.addAction(self.showEarthAction)
        self.view3dMenu.addAction(self.showEarthGridAction)
        self.view3dMenu.addAction(self.showAxesAction)
        self.view3dMenu.addSeparator()
        self.view3dMenu.addAction(self.showOrbitalPathsAction)

        # HELP MENU
        self.helpMenu = self.menuBar.addMenu('&Help')
        self.githubAct = QAction('&Visit GitHub', self)
        self.githubAct.setIcon(self.icons['GITHUB'])
        self.githubAct.triggered.connect(self._openGithub)
        self.reportIssueAct = QAction('&Report Issue', self)
        self.reportIssueAct.setIcon(self.icons['BUG'])
        self.reportIssueAct.triggered.connect(self._reportIssue)
        self.helpMenu.addAction(self.githubAct)
        self.helpMenu.addAction(self.reportIssueAct)

    def _createIcons(self):
        self.iconPath = os.path.join(self.currentDir, f'src/assets/icons')
        self.icons['PLAY'] = QIcon(os.path.join(self.iconPath, 'play.png'))
        self.icons['PAUSE'] = QIcon(os.path.join(self.iconPath, 'pause.png'))
        self.icons['FAST_FORWARD'] = QIcon(os.path.join(self.iconPath, 'fast-forward.png'))
        self.icons['SLOW_DOWN'] = QIcon(os.path.join(self.iconPath, 'slow-down.png'))
        self.icons['RESUME'] = QIcon(os.path.join(self.iconPath, 'resume.png'))
        self.icons['BUG'] = QIcon(os.path.join(self.iconPath, 'bug.png'))
        self.icons['GITHUB'] = QIcon(os.path.join(self.iconPath, 'github.png'))

    def _checkEarth(self, checked):
        self.settings['3D_VIEW']['SHOW_EARTH'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkEarthGrid(self, checked):
        self.settings['3D_VIEW']['SHOW_EARTH_GRID'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkAxes(self, checked):
        self.settings['3D_VIEW']['SHOW_AXES'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkOrbitalPaths(self, checked):
        self.settings['3D_VIEW']['SHOW_ORBITS'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkGroundTracks(self, checked):
        self.settings['2D_MAP']['SHOW_GROUND_TRACK'] = checked
        self.saveSettings()
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))
        self.object2dMapConfigDock.enableGroundTrackConfig(self.settings['2D_MAP']['SHOW_GROUND_TRACK'])

    def _checkFootprints(self, checked):
        self.settings['2D_MAP']['SHOW_FOOTPRINT'] = checked
        self.saveSettings()
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))
        self.object2dMapConfigDock.enableFootprintConfig(self.settings['2D_MAP']['SHOW_FOOTPRINT'])

    @staticmethod
    def _openGithub():
        QDesktopServices.openUrl(QUrl("https://github.com/EnguerranVidal/PySatTracker"))

    @staticmethod
    def _reportIssue():
        QDesktopServices.openUrl(QUrl("https://github.com/EnguerranVidal/PySatTracker/issues/new"))

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

    def _updateActionStates(self):
        hasSelection = self.selectedObject is not None
        for action in self._selectionDependentActions:
            action.setEnabled(hasSelection)

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
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))
        self.objectListDock.populate(self.tleDatabase, self.activeObjects)
        self.centralViewWidget.setActiveObjects(self.activeObjects)
        self.centralViewWidget.start()
        self._updateActionStates()
        self.centralViewWidget.tabWidget.setCurrentIndex(getKeyFromValue(self.centralViewWidget.TABS, self.settings['VISUALIZATION']['CURRENT_TAB']))
        self.centralViewWidget.tabChanged.connect(self._updateTabs)
        self.setObjectConfigWidgetsVisibility()

    def setObjectConfigWidgetsVisibility(self):
        if self.settings['VISUALIZATION']['CURRENT_TAB'] == '2D_MAP':
            self.object2dMapConfigDock.setVisible(True)
            self.object3dViewConfigDock.setVisible(False)
        if self.settings['VISUALIZATION']['CURRENT_TAB'] == '3D_VIEW':
            self.object2dMapConfigDock.setVisible(False)
            self.object3dViewConfigDock.setVisible(True)

    def loadSettings(self):
        self.settings = loadSettingsJson(self.settingsPath)

    def saveSettings(self):
        saveSettingsJson(self.settingsPath, self.settings)

    def addObjects(self, noradIndices: list[int]):
        for noradIndex in noradIndices:
            if noradIndex in self.activeObjects:
                continue
            self.activeObjects.append(noradIndex)
            if str(noradIndex) not in self.settings['2D_MAP']['OBJECTS']:
                self.settings['2D_MAP']['OBJECTS'][str(noradIndex)] = copy.deepcopy(self.settings['2D_MAP']['DEFAULT_CONFIG'])
            if str(noradIndex) not in self.settings['3D_VIEW']['OBJECTS']:
                self.settings['3D_VIEW']['OBJECTS'][str(noradIndex)] = copy.deepcopy(self.settings['3D_VIEW']['DEFAULT_CONFIG'])
        self.settings['VISUALIZATION']['ACTIVE_OBJECTS'] = self.activeObjects
        self.saveSettings()
        self.objectListDock.populate(self.tleDatabase, self.activeObjects)
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))
        self.centralViewWidget.setActiveObjects(self.activeObjects)
        self._updateActionStates()

    def removeSelectedObjects(self, noradIndices: list[int]):
        for noradIndex in noradIndices:
            if noradIndex in self.activeObjects:
                self.activeObjects.remove(noradIndex)
            if self.selectedObject == noradIndex:
                self.selectedObject = None
                self.objectInfoDock.clear()
        self.settings['VISUALIZATION']['ACTIVE_OBJECTS'] = self.activeObjects
        self.saveSettings()
        self.objectListDock.populate(self.tleDatabase, self.activeObjects)
        self.centralViewWidget.setActiveObjects(self.activeObjects)
        self.centralViewWidget.setSelectedObject(self.selectedObject)
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))
        self._updateActionStates()

    def onObjectSelected(self, noradIndex):
        if noradIndex is None:
            noradIndex = []
        if isinstance(noradIndex, list):
            if len(noradIndex) == 0:
                self.selectedObject = None
                self.objectInfoDock.clear()
                self.centralViewWidget.setSelectedObject(None)
                self._updateActionStates()
                return
            noradIndex = noradIndex[0]
        try:
            self.selectedObject = int(noradIndex)
        except (TypeError, ValueError):
            self.selectedObject = None
            self.objectInfoDock.clear()
            self.centralViewWidget.setSelectedObject(None)
            self._updateActionStates()
            return
        row = self.tleDatabase.dataFrame.loc[self.tleDatabase.dataFrame['NORAD_CAT_ID'].astype(int) == self.selectedObject]
        if not row.empty:
            self.objectInfoDock.setObject(row.iloc[0])
        else:
            self.objectInfoDock.clear()
        self.centralViewWidget.setSelectedObject(self.selectedObject)
        self.object2dMapConfigDock.setSelectedObject(self.selectedObject, self.settings['2D_MAP']['OBJECTS'])
        self.object3dViewConfigDock.setSelectedObject(self.selectedObject, self.settings['3D_VIEW']['OBJECTS'])
        self._updateActionStates()

    def _on2dMapObjectConfigChanged(self, noradIndex, newConfiguration):
        self.settings['2D_MAP']['OBJECTS'][str(noradIndex)] = newConfiguration
        self.saveSettings()
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))

    def _on3dViewObjectConfigChanged(self, noradIndex, newConfiguration):
        self.settings['3D_VIEW']['OBJECTS'][str(noradIndex)] = newConfiguration
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _resetObject2dMapConfig(self):
        if self.selectedObject is None:
            return
        self.settings['2D_MAP']['OBJECTS'][str(self.selectedObject)] = copy.deepcopy(self.settings['2D_MAP']['DEFAULT_CONFIG'])
        self.saveSettings()
        self.object2dMapConfigDock.setSelectedObject(self.selectedObject, self.settings['2D_MAP']['OBJECTS'])
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))

    def _setObject2dMapConfigAsDefault(self):
        if self.selectedObject is None:
            return
        self.settings['2D_MAP']['DEFAULT_CONFIG'] = copy.deepcopy(self.settings['2D_MAP']['OBJECTS'][str(self.selectedObject)])
        self.saveSettings()

    def _checkNightLayer(self, checked):
        self.settings['2D_MAP']['SHOW_NIGHT'] = checked
        self.saveSettings()
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))

    def _checkSunIndicator(self, checked):
        self.settings['2D_MAP']['SHOW_SUN'] = checked
        self.saveSettings()
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))

    def _checkVernalPoint(self, checked):
        self.settings['2D_MAP']['SHOW_VERNAL'] = checked
        self.saveSettings()
        self.centralViewWidget.set2dMapConfiguration(copy.deepcopy(self.settings['2D_MAP']))

    def closeEvent(self, event):
        self.centralViewWidget.close()
        # SAVING SETTINGS
        self.settings['WINDOW']['MAXIMIZED'] = self.isMaximized()
        if not self.isMaximized():
            g = self.geometry()
            self.settings['WINDOW']['GEOMETRY'] = {'X': g.x(), 'Y': g.y(), 'WIDTH': g.width(), 'HEIGHT': g.height()}
        self.settings['VISUALIZATION']['ACTIVE_OBJECTS'] = self.activeObjects
        self.saveSettings()
        event.accept()


class Map2dWidget(QWidget):
    objectSelected = pyqtSignal(list)
    ELEMENTS_Z_VALUES = {'SPOT': 30, 'LABEL': 40, 'FOOTPRINT': 20, 'GROUND_TRACK': 10, 'SUN': 50, 'NIGHT': 5, 'VERNAL': 100}

    def __init__(self, parent=None, mapImagePath='src/assets/earth/world_map.png'):
        super().__init__(parent)
        self.mapImagePath = mapImagePath
        self.objectSpots, self.objectGroundTracks, self.objectFootprints, self.objectArrows = {}, {}, {}, {}
        self.objectLabels = {}
        self._lastMouseScenePos = None
        self.selectedObject, self.hoveredObject, self.hoverRadius, self.displayConfiguration = None, None, 15, {}
        self.sunIndicator, self.nightLayer, self.vernalIndicator = None, None, None
        self._setupMap()

    def _setupMap(self):
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
        self.plot.scene().sigMouseMoved.connect(self._onMouseMoved)
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)

    def _lonlatToCartesian(self, longitude, latitude):
        longitude, latitude = np.asarray(longitude), np.asarray(latitude)
        return (longitude + 180) / 360 * self.mapWidth, (latitude + 90) / 180 * self.mapHeight

    @staticmethod
    def _arrowAngle(x0, y0, x1, y1):
        return np.degrees(np.arctan2(y1 - y0, x1 - x0)) + 180

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

    @staticmethod
    def _shouldRender(mode: str, isSelected: bool, isToggled: bool = True):
        if not isToggled:
            return False
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER

    def _updateSunAndNight(self, mapData, showSun=True, showNight=True, showVernal=True):
        if showNight:
            subPointLongitude, subPointLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
            longitudes, latitudes = mapData['NIGHT']['LONGITUDE'], mapData['NIGHT']['LATITUDE']
            x, y = self._lonlatToCartesian(longitudes, latitudes)
            fillLevel = 0 if subPointLatitude > 0 else self.mapHeight
            if self.nightLayer is None:
                self.nightLayer = pg.PlotCurveItem(x, y, pen=None, fillLevel=fillLevel, brush=pg.mkBrush(0, 0, 0, 120))
                self.nightLayer.setZValue(self.ELEMENTS_Z_VALUES['NIGHT'])
                self.plot.addItem(self.nightLayer)
            else:
                self.nightLayer.setData(x, y)
                self.nightLayer.setFillLevel(fillLevel)

        else:
            if self.nightLayer is not None:
                self.plot.removeItem(self.nightLayer)
                self.nightLayer = None
        if showSun:
            subPointLongitude, subPointLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
            xSun, ySun = self._lonlatToCartesian(subPointLongitude, subPointLatitude)
            if self.sunIndicator is None:
                self.sunIndicator = pg.ScatterPlotItem(size=14, brush=pg.mkBrush(255, 215, 0), pen=pg.mkPen(255, 200, 0, width=2), symbol="o",)
                self.sunIndicator.setZValue(self.ELEMENTS_Z_VALUES['SUN'])
                self.plot.addItem(self.sunIndicator)
            self.sunIndicator.setData([xSun], [ySun])
        else:
            if self.sunIndicator is not None:
                self.plot.removeItem(self.sunIndicator)
                self.sunIndicator = None
        if showVernal:
            vernalLongitude, vernalLatitude = mapData['VERNAL']['LONGITUDE'], mapData['VERNAL']['LATITUDE']
            xVernal, yVernal = self._lonlatToCartesian(vernalLongitude, vernalLatitude)
            if self.vernalIndicator is None:
                self.vernalIndicator = pg.ScatterPlotItem(size=15, brush=pg.mkBrush(0, 200, 0), pen=pg.mkPen(0, 255, 0, width=2), symbol="+",)
                self.vernalIndicator.setZValue(self.ELEMENTS_Z_VALUES['VERNAL'])
                self.plot.addItem(self.vernalIndicator)
            self.vernalIndicator.setData([xVernal], [yVernal])
        else:
            if self.vernalIndicator is not None:
                self.plot.removeItem(self.vernalIndicator)
                self.vernalIndicator = None

    def updateMap(self, positions: dict, visibleNorads: set[int], selectedNorad: int | None, displayConfiguration: dict):
        self.selectedObject, self.displayConfiguration = selectedNorad, displayConfiguration
        # REMOVING EVERYTHING NOT VISIBLE
        for noradIndex in list(self.objectSpots.keys()):
            if noradIndex not in visibleNorads:
                self._removeItems(self.objectSpots.pop(noradIndex))
                self._removeItems(self.objectGroundTracks.pop(noradIndex, None))
                self._removeItems(self.objectFootprints.pop(noradIndex, None))
                self._removeItems(self.objectArrows.pop(noradIndex, None))
                self._removeItems(self.objectLabels.pop(noradIndex, None))
        # NIGHT LAYER AND SUN POSITION
        self._updateSunAndNight(positions['2D_MAP'], self.displayConfiguration['SHOW_SUN'], self.displayConfiguration['SHOW_NIGHT'], self.displayConfiguration['SHOW_VERNAL'])
        # UPDATING/ADDING VISIBLE OBJECTS
        for noradIndex in visibleNorads:
            if noradIndex not in positions['2D_MAP']['OBJECTS']:
                continue
            self._updateObjectDisplay(noradIndex, positions['2D_MAP']['OBJECTS'][noradIndex])

    def _updateObjectDisplay(self, noradIndex, noradPosition):
        isSelected = (noradIndex == self.selectedObject)
        isHovered = (noradIndex == self.hoveredObject)
        isActive = isSelected or isHovered
        noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
        # GROUND TRACKS
        groundTrackColor, groundTrackWidth = noradObjectConfiguration['GROUND_TRACK']['COLOR'], noradObjectConfiguration['GROUND_TRACK']['WIDTH']
        if self._shouldRender(noradObjectConfiguration['GROUND_TRACK']['MODE'], isSelected, self.displayConfiguration['SHOW_GROUND_TRACK']):
            groundLongitudes, groundLatitudes = noradPosition['GROUND_TRACK']['LONGITUDE'], noradPosition['GROUND_TRACK']['LATITUDE']
            groundSegments = self._splitWrapSegment(groundLongitudes, groundLatitudes)
            for item in self.objectGroundTracks.get(noradIndex, []):
                self.plot.removeItem(item)
            self.objectGroundTracks[noradIndex] = []
            for segmentLongitudes, segmentLatitudes in groundSegments:
                gx, gy = self._lonlatToCartesian(segmentLongitudes, segmentLatitudes)
                curve = pg.PlotCurveItem(gx, gy, pen=pg.mkPen(groundTrackColor, width=groundTrackWidth))
                curve.setZValue(self.ELEMENTS_Z_VALUES['GROUND_TRACK'])
                self.objectGroundTracks[noradIndex].append(curve)
                self.plot.addItem(self.objectGroundTracks[noradIndex][-1])
            # GROUND TRACK ARROW
            lastLongitude, lastLatitude = groundSegments[-1]
            x0, y0 = self._lonlatToCartesian(lastLongitude[-2], lastLatitude[-2])
            x1, y1 = self._lonlatToCartesian(lastLongitude[-1], lastLatitude[-1])
            length = np.hypot(x1 - x0, y1 - y0)
            angle = self._arrowAngle(x0, y0, x1, y1)
            if noradIndex not in self.objectArrows:
                arrow = pg.ArrowItem(angle=angle, tipAngle=30, headLen=length, tailLen=0, tailWidth=0, pen=pg.mkPen(groundTrackColor), brush=pg.mkBrush(groundTrackColor), pxMode=False)
                arrow.setZValue(self.ELEMENTS_Z_VALUES['GROUND_TRACK'])
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
        footColor, footWidth = noradObjectConfiguration['FOOTPRINT']['COLOR'], noradObjectConfiguration['FOOTPRINT']['WIDTH']
        if self._shouldRender(noradObjectConfiguration['FOOTPRINT']['MODE'], isSelected, self.displayConfiguration['SHOW_FOOTPRINT']):
            footLongitudes, footLatitudes = noradPosition['VISIBILITY']['LONGITUDE'], noradPosition['VISIBILITY']['LATITUDE']
            footSegments = self._splitWrapSegment(footLongitudes, footLatitudes)
            for item in self.objectFootprints.get(noradIndex, []):
                self.plot.removeItem(item)
            self.objectFootprints[noradIndex] = []
            for segmentLongitudes, segmentLatitudes in footSegments:
                fx, fy = self._lonlatToCartesian(segmentLongitudes, segmentLatitudes)
                curve = pg.PlotCurveItem(fx, fy, pen=pg.mkPen(footColor, width=footWidth))
                curve.setZValue(self.ELEMENTS_Z_VALUES['FOOTPRINT'])
                self.objectFootprints[noradIndex].append(curve)
                self.plot.addItem(self.objectFootprints[noradIndex][-1])
        else:
            self._removeItems(self.objectFootprints.get(noradIndex))
            self.objectFootprints.pop(noradIndex, None)
        # OBJECT POSITIONS
        spotColor = tuple(noradObjectConfiguration['SPOT']['COLOR']) if isActive else (150, 150, 150)
        x, y = self._lonlatToCartesian(noradPosition['POSITION']['LONGITUDE'], noradPosition['POSITION']['LATITUDE'])
        if noradIndex not in self.objectSpots:
            spot = pg.ScatterPlotItem(size=noradObjectConfiguration['SPOT']['SIZE'], brush=pg.mkBrush(*spotColor))
            spot.sigClicked.connect(self._onObjectClicked)
            spot.setZValue(self.ELEMENTS_Z_VALUES['SPOT'])
            self.objectSpots[noradIndex] = spot
            self.plot.addItem(self.objectSpots[noradIndex])
        self.objectSpots[noradIndex].setData([{'pos': (x, y), 'data': noradIndex}], brush=pg.mkBrush(*spotColor), pen=None)
        self.objectSpots[noradIndex].setSize(noradObjectConfiguration['SPOT']['SIZE'])
        if noradIndex not in self.objectLabels:
            label = pg.TextItem(text=noradPosition['NAME'], anchor=(0.5, 1.2), color=(255, 255, 255))
            label.setZValue(self.ELEMENTS_Z_VALUES['LABEL'])
            label.hide()
            self.objectLabels[noradIndex] = label
            self.plot.addItem(label)
        self.objectLabels[noradIndex].setPos(x, y)
        if isActive:
            self.objectLabels[noradIndex].show()
        else:
            self.objectLabels[noradIndex].hide()
        if self._lastMouseScenePos is not None:
            self._onMouseMoved(self._lastMouseScenePos)

    def _onObjectClicked(self, plot, points):
        if not points:
            return
        noradIndex = points[0].data()
        if noradIndex is None:
            return
        self.objectSelected.emit([noradIndex])

    def _onMouseMoved(self, scenePos):
        self._lastMouseScenePos = scenePos
        self.hoverRadius = 15 * self.plot.vb.viewPixelSize()[0]
        if not self.objectSpots:
            return
        closestNorad, closestDist = None, float("inf")
        mouseViewPos = self.plot.vb.mapSceneToView(scenePos)
        for noradIndex, spot in self.objectSpots.items():
            pts = spot.points()
            if not pts:
                continue
            spotViewPos = pts[0].pos()
            dist = np.sqrt((spotViewPos.x() - mouseViewPos.x()) ** 2 + (spotViewPos.y() - mouseViewPos.y()) ** 2)
            if dist < self.hoverRadius and dist < closestDist:
                closestNorad, closestDist = noradIndex, dist
        if closestNorad is not None and self.hoveredObject is None:
            self.hoveredObject = closestNorad
            if closestNorad in self.objectLabels:
                self.objectLabels[closestNorad].show()
        elif closestNorad is None and self.hoveredObject is not None:
            if self.hoveredObject in self.objectLabels and self.hoveredObject != self.selectedObject:
                self.objectLabels[self.hoveredObject].hide()
            self.hoveredObject = None
        elif closestNorad is not None and closestNorad != self.hoveredObject:
            if self.hoveredObject in self.objectLabels and self.hoveredObject != self.selectedObject:
                self.objectLabels[self.hoveredObject].hide()
            self.hoveredObject = closestNorad
            if closestNorad in self.objectLabels:
                self.objectLabels[closestNorad].show()

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

    def __init__(self, mainWindow, title='Active Objects'):
        super().__init__(title, mainWindow)
        self.mainWindow = mainWindow
        container = QWidget()
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())
        self.setWidget(container)

        topBar = QHBoxLayout()
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText('Search Active Objects…')
        self.searchBar.textChanged.connect(self.filterObjectList)
        self.addButton = QPushButton('+')
        self.addButton.setFixedWidth(28)
        self.addButton.setToolTip('Add Objects')
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
        noradIndex = item.data(Qt.UserRole)
        if noradIndex is None:
            return
        menu = QMenu(self)
        actionToggle = menu.addAction('Toggle Visibility')
        actionRemove = menu.addAction('Remove Object')
        selectedAction = menu.exec_(self.listWidget.viewport().mapToGlobal(position))
        if selectedAction == actionToggle:
            self.toggleVisibility.emit([noradIndex])
        elif selectedAction == actionRemove:
            self.removeObject.emit([noradIndex])

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
        if isinstance(noradIndex, list):
            self.objectSelected.emit(noradIndex)
        else:
            self.objectSelected.emit([noradIndex])


class ObjectInfoDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__('Object Info', parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
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


class Object2dMapConfigDockWidget(QDockWidget):
    configChanged = pyqtSignal(int, dict)
    MODES = {'Always': "ALWAYS", 'When Selected': "WHEN_SELECTED", 'Never': "NEVER"}

    def __init__(self, parent=None):
        super().__init__("Object Map Configuration", parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.noradIndex = None
        self._currentConfig = None
        self._setupUi()

    def _setupUi(self):
        self.editorWidget = QWidget()
        self.editorWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        mainLayout = QVBoxLayout(self.editorWidget)
        mainLayout.setSpacing(10)
        mainLayout.setContentsMargins(6, 6, 6, 6)

        # SPOT CONFIGURATION
        self.spotGroup = self._groupBox("Spot")
        self.spotColorButton = self._colorButton()
        self.spotSizeSpin = QSpinBox()
        self.spotSizeSpin.setRange(4, 30)
        self.spotSizeSpin.setToolTip("Size")

        self.spotGroup.layout().addWidget(self.spotColorButton, 0, 0)
        self.spotGroup.layout().addWidget(self.spotSizeSpin, 0, 1)
        mainLayout.addWidget(self.spotGroup)

        # GROUND TRACK CONFIGURATION
        self.groundTrackGroup = self._groupBox("Ground Track")
        self.groundTrackModeCombo = QComboBox()
        self.groundTrackModeCombo.addItems(list(self.MODES.keys()))
        self.groundTrackColorButton = self._colorButton()
        self.groundTrackWidthSpin = QSpinBox()
        self.groundTrackWidthSpin.setRange(1, 5)
        self.groundTrackWidthSpin.setToolTip("Width")

        self.groundTrackGroup.layout().addWidget(self.groundTrackModeCombo, 0, 0)
        self.groundTrackGroup.layout().addWidget(self.groundTrackColorButton, 0, 1)
        self.groundTrackGroup.layout().addWidget(self.groundTrackWidthSpin, 0, 2)
        mainLayout.addWidget(self.groundTrackGroup)

        # VISIBILITY CONFIGURATION
        self.footprintGroup = self._groupBox("Visibility Footprint")
        self.footprintModeCombo = QComboBox()
        self.footprintModeCombo.addItems(list(self.MODES.keys()))
        self.footprintColorButton = self._colorButton()
        self.footprintWidthSpin = QSpinBox()
        self.footprintWidthSpin.setRange(1, 5)
        self.footprintWidthSpin.setToolTip("Width")

        self.footprintGroup.layout().addWidget(self.footprintModeCombo, 0, 0)
        self.footprintGroup.layout().addWidget(self.footprintColorButton, 0, 1)
        self.footprintGroup.layout().addWidget(self.footprintWidthSpin, 0, 2)
        mainLayout.addWidget(self.footprintGroup)

        self.editorWidget.setEnabled(False)
        self.setWidget(self.editorWidget)
        self.spotSizeSpin.valueChanged.connect(self._emitConfig)
        self.groundTrackModeCombo.currentIndexChanged.connect(self._emitConfig)
        self.groundTrackWidthSpin.valueChanged.connect(self._emitConfig)
        self.footprintModeCombo.currentIndexChanged.connect(self._emitConfig)
        self.footprintWidthSpin.valueChanged.connect(self._emitConfig)

        self.spotColorButton.clicked.connect(lambda: self._pickColor('SPOT'))
        self.groundTrackColorButton.clicked.connect(lambda: self._pickColor('GROUND_TRACK'))
        self.footprintColorButton.clicked.connect(lambda: self._pickColor('FOOTPRINT'))

    @staticmethod
    def _colorButton():
        btn = QPushButton()
        btn.setFixedSize(24, 24)
        btn.setStyleSheet("border: 1px solid #666;")
        return btn

    @staticmethod
    def _groupBox(title: str):
        box = QGroupBox(title)
        box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QGridLayout(box)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.setContentsMargins(8, 12, 8, 8)
        return box

    @staticmethod
    def _setButtonColor(btn, color):
        btn.setStyleSheet(f"background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;")

    def _modeToLabel(self, mode):
        for label, value in self.MODES.items():
            if value == mode:
                return label
        return "Never"

    def setSelectedObject(self, noradIndex: int | None, config: dict):
        self.noradIndex = noradIndex
        if noradIndex is None:
            self.clear()
            return
        self.editorWidget.setEnabled(True)
        self._currentConfig = config[str(noradIndex)]
        blockers = [
            QSignalBlocker(self.spotSizeSpin),
            QSignalBlocker(self.groundTrackModeCombo),
            QSignalBlocker(self.groundTrackWidthSpin),
            QSignalBlocker(self.footprintModeCombo),
            QSignalBlocker(self.footprintWidthSpin),
        ]
        self.spotSizeSpin.setValue(self._currentConfig['SPOT'].get('SIZE', 10))
        self.groundTrackModeCombo.setCurrentText(self._modeToLabel(self._currentConfig['GROUND_TRACK']['MODE']))
        self.groundTrackWidthSpin.setValue(self._currentConfig['GROUND_TRACK'].get('WIDTH', 1))
        self.footprintModeCombo.setCurrentText(self._modeToLabel(self._currentConfig['FOOTPRINT']['MODE']))
        self.footprintWidthSpin.setValue(self._currentConfig['FOOTPRINT'].get('WIDTH', 1))
        self._setButtonColor(self.spotColorButton, self._currentConfig['SPOT']['COLOR'])
        self._setButtonColor(self.groundTrackColorButton, self._currentConfig['GROUND_TRACK']['COLOR'])
        self._setButtonColor(self.footprintColorButton, self._currentConfig['FOOTPRINT']['COLOR'])
        del blockers

    def enableFootprintConfig(self, enabled: bool):
        self.footprintGroup.setEnabled(enabled)

    def enableGroundTrackConfig(self, enabled: bool):
        self.groundTrackGroup.setEnabled(enabled)

    def clear(self):
        self.noradIndex = None
        self._currentConfig = None
        self.editorWidget.setEnabled(False)

    def _pickColor(self, section):
        if self._currentConfig is None:
            return
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        button = {'SPOT': self.spotColorButton, 'GROUND_TRACK': self.groundTrackColorButton, 'FOOTPRINT': self.footprintColorButton}[section]
        self._currentConfig[section]['COLOR'] = (color.red(), color.green(), color.blue())
        self._setButtonColor(button, self._currentConfig[section]['COLOR'])
        self._emitConfig()

    def _emitConfig(self, *_):
        if not self.editorWidget.isEnabled():
            return
        if self.noradIndex is None or self._currentConfig is None:
            return
        self._currentConfig['SPOT']['SIZE'] = self.spotSizeSpin.value()
        self._currentConfig['GROUND_TRACK']['MODE'] = self.MODES[self.groundTrackModeCombo.currentText()]
        self._currentConfig['GROUND_TRACK']['WIDTH'] = self.groundTrackWidthSpin.value()
        self._currentConfig['FOOTPRINT']['MODE'] = self.MODES[self.footprintModeCombo.currentText()]
        self._currentConfig['FOOTPRINT']['WIDTH'] = self.footprintWidthSpin.value()
        self.configChanged.emit(self.noradIndex, self._currentConfig)


class CentralViewWidget(QWidget):
    tabChanged = pyqtSignal(int)
    TABS = {0: '2D_MAP', 1: '3D_VIEW'}

    def __init__(self, parent=None, icons=None, currentTab='2D_MAP', currentDir=None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.icons = icons if icons is not None else {}
        # CLOCK & ORBITS CALCULATIONS WORKER
        self.clock = SimulationClock()
        self.workerThread = QThread(self)
        self.orbitWorker = OrbitWorker(None)
        self.orbitWorker.moveToThread(self.workerThread)
        self.clock.timeChanged.connect(self.orbitWorker.compute)
        self.workerThread.start()

        # TIMELINE WIDGET
        self.timeline = TimelineWidget(self, self.currentDir)
        self.timeline.playRequested.connect(self.clock.play)
        self.timeline.pauseRequested.connect(self.clock.pause)
        self.timeline.toggleRequested.connect(self.clock.toggle)
        self.timeline.speedRequested.connect(self._onSpeedRequested)
        self.timeline.timeRequested.connect(self.clock.setTime)
        self.timeline.jumpToNowRequested.connect(self._jumpToNow)
        self.clock.timeChanged.connect(self._onClockTimeChanged)
        self.clock.stateChanged.connect(self.timeline.setRunning)

        # VISUALIZATION CONFIGURATION
        self.activeObjects = set()
        self.selectedObject = None
        self.display2dMapConfiguration, self.display3dViewConfiguration = {}, {}
        self.lastPositions = {}

        # MAIN TABS
        self.map2dWidget = Map2dWidget()
        self.view3dWidget = View3dWidget()
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(self.map2dWidget, '2D MAP')
        self.tabWidget.addTab(self.view3dWidget, '3D VIEW')
        self.tabWidget.setCurrentWidget(self.map2dWidget if currentTab == '2D_MAP' else self.view3dWidget)

        self.orbitWorker.positionsReady.connect(self._onPositionsReady)
        self.tabWidget.currentChanged.connect(self._onTabChanged)
        self.map2dVisible = (self.tabWidget.currentWidget() is self.map2dWidget)
        self.view3dVisible = (self.tabWidget.currentWidget() is self.view3dWidget)

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabWidget)
        layout.addWidget(self.timeline)

    def _onTabChanged(self, index):
        self.map2dVisible = (self.tabWidget.currentWidget() is self.map2dWidget)
        self.view3dVisible = (self.tabWidget.currentWidget() is self.view3dWidget)
        if self.map2dVisible:
            self._refresh2dMap()
        if self.view3dVisible:
            self._refresh3dView()
        self.tabChanged.emit(index)

    def _onPositionsReady(self, positions: dict):
        self.lastPositions = positions
        if self.map2dVisible:
            self._refresh2dMap()
        if self.view3dVisible:
            self._refresh3dView()

    def setDatabase(self, database):
        self.orbitWorker.database = database

    def setSelectedObject(self, noradIndex):
        self.selectedObject = noradIndex
        self._refresh2dMap()

    def setActiveObjects(self, noradIndices):
        self.activeObjects = set(noradIndices)
        self.orbitWorker.noradIndices = list(self.activeObjects)
        self._refresh2dMap()
        self._refresh3dView()

    def set2dMapConfiguration(self, displayConfiguration):
        self.display2dMapConfiguration = displayConfiguration
        self._refresh2dMap()

    def set3dViewConfiguration(self, displayConfiguration):
        self.display3dViewConfiguration = displayConfiguration
        self._refresh3dView()

    def _refresh2dMap(self):
        if self.map2dVisible and self.lastPositions:
            self.map2dWidget.updateMap(self.lastPositions, self.activeObjects, self.selectedObject, self.display2dMapConfiguration)

    def _refresh3dView(self):
        if self.view3dVisible and self.lastPositions:
            self.view3dWidget.updateData(self.lastPositions, self.activeObjects, self.selectedObject, self.display3dViewConfiguration)

    def start(self):
        self.clock.play()

    def _onClockTimeChanged(self, simTime: datetime):
        self.timeline.setTime(simTime)

    def _onSpeedRequested(self, speed):
        self.clock.setSpeed(speed)

    def _jumpToNow(self):
        now = datetime.utcnow()
        self.timeline.resetReferenceTime(now)
        self.clock.setTime(now)

    def closeEvent(self, event):
        self.orbitWorker.stop()
        self.workerThread.quit()
        self.workerThread.wait()
        super().closeEvent(event)
