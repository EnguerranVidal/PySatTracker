import copy
import os
from datetime import datetime

import qdarktheme
import time
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtCore import Qt, QDateTime, QTimer, QPoint, pyqtSignal, QThread, QUrl
from PyQt5.QtWidgets import *

from gui.map2d import Map2dWidget, Object2dMapConfigDockWidget
from gui.widgets import TimelineWidget
from src.gui.view3d import View3dWidget, Object3dViewConfigDockWidget
from src.gui.objects import SimulationClock, AddObjectDialog, OrbitWorker
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
        self._createActions()
        self._createMenuBar()
        self._setupStatusBar()
        self._restoreWindow()
        self._updateActionStates()

    def _updateTabs(self, tabIndex):
        self.settings['VISUALIZATION']['CURRENT_TAB'] = self.centralViewWidget.TABS[tabIndex]
        self.setObjectConfigWidgetsVisibility()

    def _createActions(self):
        self._selectionDependentActions = []
        # RESET 2D MAP CONFIGURATION
        self.set2dMapConfigAsDefaultAction = QAction('&Set as Default', self)
        self.set2dMapConfigAsDefaultAction.setStatusTip('Set Current Object\'s 2D Map Configuration as Default')
        self.set2dMapConfigAsDefaultAction.triggered.connect(self._setObject2dMapConfigAsDefault)
        self._selectionDependentActions.append(self.set2dMapConfigAsDefaultAction)
        # RESET 2D MAP CONFIGURATION
        self.reset2dMapConfigAction = QAction('&Reset Configuration', self)
        self.reset2dMapConfigAction.setStatusTip('Reset Object\'s 2D Map Configuration to Default')
        self.reset2dMapConfigAction.triggered.connect(self._resetObject2dMapConfig)
        self._selectionDependentActions.append(self.reset2dMapConfigAction)
        # SHOW 2D MAP NIGHT LAYER ACTION
        self.showNightLayerAction = QAction('&Show Night Layer', self, checkable=True)
        self.showNightLayerAction.setChecked(self.settings['2D_MAP']['SHOW_NIGHT'])
        self.showNightLayerAction.setStatusTip('Show 2D Map Night Layer')
        self.showNightLayerAction.toggled.connect(self._checkNightLayer)
        # SHOW 2D MAP SUN INDICATOR
        self.sunIndicatorAction = QAction('&Show Sun Indicator', self, checkable=True)
        self.sunIndicatorAction.setChecked(self.settings['2D_MAP']['SHOW_SUN'])
        self.sunIndicatorAction.setStatusTip('Show 2D Map Sun Indicator')
        self.sunIndicatorAction.toggled.connect(self._checkSunIndicator)
        # SHOW 2D MAP VERNAL POINT
        self.vernalPointAction = QAction('&Show Vernal Point', self, checkable=True)
        self.vernalPointAction.setChecked(self.settings['2D_MAP']['SHOW_VERNAL'])
        self.vernalPointAction.setStatusTip('Show 2D Map Vernal Point')
        self.vernalPointAction.toggled.connect(self._checkVernalPoint)
        # SHOW 2D MAP GROUND TRACKS
        self.showGroundTracksAction = QAction('&Show Ground Tracks', self, checkable=True)
        self.showGroundTracksAction.setChecked(self.settings['2D_MAP']['SHOW_GROUND_TRACK'])
        self.showGroundTracksAction.setStatusTip('Allow showing 2D Map Ground Tracks')
        self.showGroundTracksAction.toggled.connect(self._checkGroundTracks)
        # SHOW 2D MAP VISIBILITY FOOTPRINTS
        self.showFootprintsAction = QAction('&Show Footprints', self, checkable=True)
        self.showFootprintsAction.setChecked(self.settings['2D_MAP']['SHOW_FOOTPRINT'])
        self.showFootprintsAction.setStatusTip('Allow showing 2D Map Visibility Footprints')
        self.showFootprintsAction.toggled.connect(self._checkFootprints)

        # RESET 3D VIEW CONFIGURATION
        self.set3dViewConfigAsDefaultAction = QAction('&Set as Default', self)
        self.set3dViewConfigAsDefaultAction.setStatusTip('Set Current Object\'s 3D View Configuration as Default')
        self.set3dViewConfigAsDefaultAction.triggered.connect(self._setObject3dViewConfigAsDefault)
        self._selectionDependentActions.append(self.set3dViewConfigAsDefaultAction)
        # RESET 3D VIEW CONFIGURATION
        self.reset3dViewConfigAction = QAction('&Reset Configuration', self)
        self.reset3dViewConfigAction.setStatusTip('Reset Object\'s 3D View Configuration to Default')
        self.reset3dViewConfigAction.triggered.connect(self._resetObject3dViewConfig)
        self._selectionDependentActions.append(self.reset3dViewConfigAction)
        # SHOW 3D VIEW EARTH MODEL
        self.showEarthAction = QAction('&Show Earth', self, checkable=True)
        self.showEarthAction.setChecked(self.settings['3D_VIEW']['SHOW_EARTH'])
        self.showEarthAction.setStatusTip('Show 3D View Earth Model')
        self.showEarthAction.toggled.connect(self._checkEarth)
        # SHOW 3D VIEW EARTH GRID
        self.showEarthGridAction = QAction('&Show Earth Grid', self, checkable=True)
        self.showEarthGridAction.setChecked(self.settings['3D_VIEW']['SHOW_EARTH_GRID'])
        self.showEarthGridAction.setStatusTip('Show 3D View Earth Longitudes/Latitudes Grid')
        self.showEarthGridAction.toggled.connect(self._checkEarthGrid)
        # SHOW 3D VIEW ECI AXIS
        self.showEciAxesAction = QAction('&Show ECI Reference Frame', self, checkable=True)
        self.showEciAxesAction.setChecked(self.settings['3D_VIEW']['SHOW_ECI_AXES'])
        self.showEciAxesAction.setStatusTip('Show 3D View ECI Reference Frame Axes')
        self.showEciAxesAction.toggled.connect(self._checkEciAxes)
        # SHOW 3D VIEW ECEF AXIS
        self.showEcefAxesAction = QAction('&Show ECEF Reference Frame', self, checkable=True)
        self.showEcefAxesAction.setChecked(self.settings['3D_VIEW']['SHOW_ECEF_AXES'])
        self.showEcefAxesAction.setStatusTip('Show 3D View ECEF Reference Frame Axes')
        self.showEcefAxesAction.toggled.connect(self._checkEcefAxes)
        # SHOW 3D VIEW ORBITAL PATHS
        self.showOrbitalPathsAction = QAction('&Show Orbital Paths', self, checkable=True)
        self.showOrbitalPathsAction.setChecked(self.settings['3D_VIEW']['SHOW_ORBITS'])
        self.showOrbitalPathsAction.setStatusTip('Allow showing 3D View Orbital Paths')
        self.showOrbitalPathsAction.toggled.connect(self._checkOrbitalPaths)

        # VISIT GITHUB
        self.githubAction = QAction('&Visit GitHub', self)
        self.githubAction.setIcon(self.icons['GITHUB'])
        self.githubAction.setStatusTip('Visit the Project\'s GitHub Repository')
        self.githubAction.triggered.connect(self._openGithub)
        # REPORT ISSUE
        self.reportIssueAction = QAction('&Report Issue', self)
        self.reportIssueAction.setIcon(self.icons['BUG'])
        self.reportIssueAction.setStatusTip('Report an Issue')
        self.reportIssueAction.triggered.connect(self._reportIssue)

    def _createMenuBar(self):
        self.menuBar = self.menuBar()
        self._selectionDependentActions = []

        ### VIEW MENU ###
        self.viewMenu = self.menuBar.addMenu('&View')
        # 2D MAP MENU
        self.map2dMenu = self.viewMenu.addMenu('&2D Map')
        self.map2dMenu.addAction(self.reset2dMapConfigAction)
        self.map2dMenu.addAction(self.set2dMapConfigAsDefaultAction)
        self.map2dMenu.addSeparator()
        self.map2dMenu.addAction(self.showNightLayerAction)
        self.map2dMenu.addAction(self.sunIndicatorAction)
        self.map2dMenu.addAction(self.vernalPointAction)
        self.map2dMenu.addSeparator()
        self.map2dMenu.addAction(self.showGroundTracksAction)
        self.map2dMenu.addAction(self.showFootprintsAction)
        # 3D VIEW MENU
        self.view3dMenu = self.viewMenu.addMenu('&3D View')
        self.view3dMenu.addAction(self.reset3dViewConfigAction)
        self.view3dMenu.addAction(self.set3dViewConfigAsDefaultAction)
        self.view3dMenu.addSeparator()
        self.view3dMenu.addAction(self.showEarthAction)
        self.view3dMenu.addAction(self.showEarthGridAction)
        self.view3dMenu.addAction(self.showEciAxesAction)
        self.view3dMenu.addAction(self.showEcefAxesAction)
        self.view3dMenu.addSeparator()
        self.view3dMenu.addAction(self.showOrbitalPathsAction)

        ### HELP MENU ###
        self.helpMenu = self.menuBar.addMenu('&Help')
        self.helpMenu.addAction(self.githubAction)
        self.helpMenu.addAction(self.reportIssueAction)

    def _createIcons(self):
        self.iconPath = os.path.join(self.currentDir, f'src/assets/icons')
        self.icons['PLAY'] = QIcon(os.path.join(self.iconPath, 'play.png'))
        self.icons['PAUSE'] = QIcon(os.path.join(self.iconPath, 'pause.png'))
        self.icons['FAST_FORWARD'] = QIcon(os.path.join(self.iconPath, 'fast-forward.png'))
        self.icons['SLOW_DOWN'] = QIcon(os.path.join(self.iconPath, 'slow-down.png'))
        self.icons['RESUME'] = QIcon(os.path.join(self.iconPath, 'resume.png'))
        self.icons['BUG'] = QIcon(os.path.join(self.iconPath, 'bug.png'))
        self.icons['GITHUB'] = QIcon(os.path.join(self.iconPath, 'github.png'))

    def _resetObject3dViewConfig(self):
        if self.selectedObject is None:
            return
        self.settings['3D_VIEW']['OBJECTS'][str(self.selectedObject)] = copy.deepcopy(self.settings['3D_VIEW']['DEFAULT_CONFIG'])
        self.saveSettings()
        self.object3dViewConfigDock.setSelectedObject(self.selectedObject, self.settings['3D_VIEW']['OBJECTS'])
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _setObject3dViewConfigAsDefault(self):
        if self.selectedObject is None:
            return
        self.settings['3D_VIEW']['DEFAULT_CONFIG'] = copy.deepcopy(self.settings['3D_VIEW']['OBJECTS'][str(self.selectedObject)])
        self.saveSettings()

    def _checkEarth(self, checked):
        self.settings['3D_VIEW']['SHOW_EARTH'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkEarthGrid(self, checked):
        self.settings['3D_VIEW']['SHOW_EARTH_GRID'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkEciAxes(self, checked):
        self.settings['3D_VIEW']['SHOW_ECI_AXES'] = checked
        self.saveSettings()
        self.centralViewWidget.set3dViewConfiguration(copy.deepcopy(self.settings['3D_VIEW']))

    def _checkEcefAxes(self, checked):
        self.settings['3D_VIEW']['SHOW_ECEF_AXES'] = checked
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
