import copy
import os
from datetime import datetime
import time

from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtCore import Qt, QDateTime, QTimer, pyqtSignal, QThread, QUrl, Q_ARG, QMetaObject
from PyQt5.QtWidgets import *

from src.core.objects import ActiveObjectsEditorWidget, ActiveObjectsModel, ObjectInfoDockWidget, ObjectViewConfigDockWidget
from src.gui.map2d import Map2dWidget
from src.gui.plots.general import PlotViewTabWidget
from src.gui.plots.requests import PlotRequestRegistryWindow, PlotRequestManager
from src.gui.plots.line import LinePlot
from src.gui.plots.time import TimeSeriesPlot
from src.gui.plots.polar import PolarPlot
from src.gui.common import TimelineWidget, SimulationClock, OrbitWorker, SetTimeDialog
from src.gui.view3d import View3dWidget
from src.gui.utilities import generateDefaultSettingsJson, loadSettingsJson, saveSettingsJson, getKeyFromValue
from src.core.quantities import VariableRegistry


class MainWindow(QMainWindow):
    def __init__(self, currentDir: str):
        super().__init__()
        self.settings = {}
        self.icons = {}
        # FOLDER PATHS & SETTINGS
        self.currentDir = currentDir
        self.settingsPath = os.path.join(self.currentDir, 'settings.json')
        self.dataPath = os.path.join(self.currentDir, 'data')
        self.noradPath = os.path.join(self.dataPath, 'norad')
        self._checkEnvironment()
        self.loadSettings()

        # CENTRAL VISUALIZATION WIDGET
        self.centralViewWidget = CentralViewWidget(parent=self, currentDir=self.currentDir, timeLineMode=self.settings['TIMELINE_MODE'])
        self.setCentralWidget(self.centralViewWidget)
        self.centralViewWidget.view3dWidget.zoom = self.settings['VIEW_CONFIG']['3D_VIEW']['ZOOM']
        self.centralViewWidget.view3dWidget.rotX = self.settings['VIEW_CONFIG']['3D_VIEW']['ROTATION']['X']
        self.centralViewWidget.view3dWidget.rotY = self.settings['VIEW_CONFIG']['3D_VIEW']['ROTATION']['Y']
        self.centralViewWidget.view3dWidget.cameraChanged.connect(self._change3dViewCameraSettings)

        # SATELLITE LIST WIDGET
        self.activeObjectsDock = ActiveObjectsEditorWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.activeObjectsDock)
        self.activeObjectsDock.activeObjectsChanged.connect(self._onActiveObjectsChanged)
        self.centralViewWidget.map2dWidget.objectSelected.connect(self.activeObjectsDock.outsideObjectSelection)
        self.centralViewWidget.view3dWidget.objectSelected.connect(self.activeObjectsDock.outsideObjectSelection)
        self.centralViewWidget.timeLineModeChanged.connect(self._timelineModeChanged)

        # OBJECT DOCK WIDGETS
        self.objectInfoDock = ObjectInfoDockWidget(self)
        self.objectViewConfigDock = ObjectViewConfigDockWidget(self)
        self.objectViewConfigDock.objectConfigChanged.connect(self._onObjectViewConfigChanged)
        self.objectViewConfigDock.groupConfigChanged.connect(self._onGroupViewConfigChanged)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objectInfoDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objectViewConfigDock)

        self.tleDatabase, self.starDatabase, self.registryWindow = None, None, None
        self._createIcons()
        self._createActions()
        self._createToolBars()
        self._createMenuBar()
        self._setupStatusBar()
        self._updateActionStates()

    def _updateStackedWidget(self, widgetIndex):
        self.settings['CURRENT_TAB'] = self.centralViewWidget.TABS[widgetIndex]
        self.objectViewConfigDock.applyGlobalVisibility(copy.deepcopy(self.settings['VIEW_CONFIG']), self.settings['CURRENT_TAB'])
        self.setObjectConfigWidgetsVisibility()
        self._manageToolBarVisibility(self.centralViewWidget.TABS[widgetIndex])

    def _timelineModeChanged(self, mode):
        self.settings['TIMELINE_MODE'] = mode
        self.saveSettings()

    def _createActions(self):
        self._selectionDependentActions = []
        # OPEN 2D MAP
        self.open2dMapAction = QAction('&Open 2D Map', self, checkable=True)
        self.open2dMapAction.setChecked(self.settings['CURRENT_TAB'] == '2D_MAP')
        self.open2dMapAction.setIcon(self.icons['MAP'])
        self.open2dMapAction.setStatusTip('Open 2D Map')
        self.open2dMapAction.triggered.connect(self._open2dMap)
        # OPEN 3D VIEW
        self.open3dViewAction = QAction('&Open 3D View', self, checkable=True)
        self.open3dViewAction.setChecked(self.settings['CURRENT_TAB'] == '3D_VIEW')
        self.open3dViewAction.setIcon(self.icons['SATELLITE_GLOBE'])
        self.open3dViewAction.setStatusTip('Open 3D View')
        self.open3dViewAction.triggered.connect(self._open3dView)
        # OPEN PLOT VIEW
        self.openPlotViewAction = QAction('&Open Plot View', self, checkable=True)
        self.openPlotViewAction.setChecked(self.settings['CURRENT_TAB'] == 'PLOT_VIEW')
        self.openPlotViewAction.setIcon(self.icons['PLOT'])
        self.openPlotViewAction.setStatusTip('Open Plot View')
        self.openPlotViewAction.triggered.connect(self._openPlotView)
        # SET AS DEFAULT VIEW CONFIGURATION
        self.setViewConfigAsDefaultAction = QAction('&Set as Default', self)
        self.setViewConfigAsDefaultAction.setStatusTip('Set Current Object\'s View Configuration as Default')
        self.setViewConfigAsDefaultAction.triggered.connect(self._setObjectViewConfigAsDefault)
        self._selectionDependentActions.append(self.setViewConfigAsDefaultAction)
        # RESET VIEW CONFIGURATION
        self.resetViewConfigAction = QAction('&Reset Configuration', self)
        self.resetViewConfigAction.setStatusTip('Reset Object\'s View Configuration to Default')
        self.resetViewConfigAction.triggered.connect(self._resetObjectViewConfig)
        self._selectionDependentActions.append(self.resetViewConfigAction)

        # SHOW 2D MAP GROUND TRACKS
        self.showGroundTracks2dAction = QAction('Show Ground Tracks', self, checkable=True)
        self.showGroundTracks2dAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_GROUND_TRACKS'])
        self.showGroundTracks2dAction.toggled.connect(self._toggleGroundTracks2d)
        self.showGroundTracks2dAction.setIconVisibleInMenu(False)
        # SHOW 2D MAP FOOTPRINTS
        self.showFootprints2dAction = QAction('Show Footprints', self, checkable=True)
        self.showFootprints2dAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_FOOTPRINTS'])
        self.showFootprints2dAction.toggled.connect(self._toggleFootprints2d)
        self.showFootprints2dAction.setIconVisibleInMenu(False)
        # SHOW 2D MAP NIGHT LAYER ACTION
        self.showNightLayerAction = QAction('&Show Night Layer', self, checkable=True)
        self.showNightLayerAction.setIcon(self.icons['SHADOW'])
        self.showNightLayerAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_NIGHT'])
        self.showNightLayerAction.setStatusTip('Show 2D Map Night Layer')
        self.showNightLayerAction.toggled.connect(self._checkNightLayer)
        self.showNightLayerAction.setIconVisibleInMenu(False)
        # SHOW 2D MAP GRID
        self.showGrid2dAction = QAction('&Show Grid', self, checkable=True)
        self.showGrid2dAction.setIcon(self.icons['MAP_GRID'])
        self.showGrid2dAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_GRID'])
        self.showGrid2dAction.setStatusTip('Show 2D Map Grid')
        self.showGrid2dAction.toggled.connect(self._check2dGrid)
        self.showGrid2dAction.setIconVisibleInMenu(False)
        # SHOW 2D MAP TERMINATOR LINE
        self.showMap2dTerminatorAction = QAction('&Show Terminator Line', self, checkable=True)
        self.showMap2dTerminatorAction.setIcon(self.icons['SUNSET'])
        self.showMap2dTerminatorAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_TERMINATOR'])
        self.showMap2dTerminatorAction.setStatusTip('Show 2D Map Terminator')
        self.showMap2dTerminatorAction.toggled.connect(self._checkMap2dTerminator)
        self.showMap2dTerminatorAction.setIconVisibleInMenu(False)
        # SHOW 2D MAP SUN INDICATOR
        self.sunIndicatorAction = QAction('&Show Sun Indicator', self, checkable=True)
        self.sunIndicatorAction.setIcon(self.icons['SUN'])
        self.sunIndicatorAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_SUN'])
        self.sunIndicatorAction.setStatusTip('Show 2D Map Sun Indicator')
        self.sunIndicatorAction.toggled.connect(self._checkSunIndicator)
        self.sunIndicatorAction.setIconVisibleInMenu(False)
        # SHOW 2D MAP VERNAL POINT
        self.vernalPointAction = QAction('&Show Vernal Point', self, checkable=True)
        self.vernalPointAction.setChecked(self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_VERNAL'])
        self.vernalPointAction.setStatusTip('Show 2D Map Vernal Point')
        self.vernalPointAction.toggled.connect(self._checkVernalPoint)
        # RESET 2D CAMERA VIEW
        self.reset2dCameraViewAction = QAction('&Reset Camera View', self)
        self.reset2dCameraViewAction.setIcon(self.icons['RESET_VIEW'])
        self.reset2dCameraViewAction.setStatusTip('Reset 2D View to Default Zoom and Center')
        self.reset2dCameraViewAction.triggered.connect(self._reset2dCameraView)

        # SHOW 3D VIEW ORBIT PATHS
        self.showOrbitPaths3dAction = QAction('Show Orbit Paths', self, checkable=True)
        self.showOrbitPaths3dAction.setChecked(self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_ORBIT_PATHS'])
        self.showOrbitPaths3dAction.toggled.connect(self._toggleOrbitPaths3d)
        self.showOrbitPaths3dAction.setIconVisibleInMenu(False)
        # SHOW 3D VIEW EARTH MODEL
        self.showEarthAction = QAction('&Show Earth', self, checkable=True)
        self.showEarthAction.setChecked(self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_EARTH'])
        self.showEarthAction.setIcon(self.icons['EARTH'])
        self.showEarthAction.setStatusTip('Show 3D View Earth Model')
        self.showEarthAction.toggled.connect(self._checkEarth)
        self.showEarthAction.setIconVisibleInMenu(False)
        # SHOW 3D VIEW EARTH GRID
        self.showEarthGridAction = QAction('&Show Earth Grid', self, checkable=True)
        self.showEarthGridAction.setChecked(self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_EARTH_GRID'])
        self.showEarthGridAction.setIcon(self.icons['EARTH_GRID'])
        self.showEarthGridAction.setStatusTip('Show 3D View Earth Longitudes/Latitudes Grid')
        self.showEarthGridAction.toggled.connect(self._checkEarthGrid)
        self.showEarthGridAction.setIconVisibleInMenu(False)
        # SHOW 3D VIEW ECI AXIS
        self.showEciAxesAction = QAction('&Show ECI Reference Frame', self, checkable=True)
        self.showEciAxesAction.setChecked(self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_ECI_AXES'])
        self.showEciAxesAction.setIcon(self.icons['ECI'])
        self.showEciAxesAction.setStatusTip('Show 3D View ECI Reference Frame Axes')
        self.showEciAxesAction.toggled.connect(self._checkEciAxes)
        self.showEciAxesAction.setIconVisibleInMenu(False)
        # SHOW 3D VIEW ECEF AXIS
        self.showEcefAxesAction = QAction('&Show ECEF Reference Frame', self, checkable=True)
        self.showEcefAxesAction.setChecked(self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_ECEF_AXES'])
        self.showEcefAxesAction.setIcon(self.icons['ECEF'])
        self.showEcefAxesAction.setStatusTip('Show 3D View ECEF Reference Frame Axes')
        self.showEcefAxesAction.toggled.connect(self._checkEcefAxes)
        self.showEcefAxesAction.setIconVisibleInMenu(False)
        # RESET CAMERA VIEW
        self.reset3dCameraViewAction = QAction('&Reset Camera View', self)
        self.reset3dCameraViewAction.setIcon(self.icons['RESET_VIEW'])
        self.reset3dCameraViewAction.setStatusTip('Reset 3D View Camera to Default Zoom and Rotation')
        self.reset3dCameraViewAction.triggered.connect(self._reset3dCameraView)

        # TOGGLE PLAY/PAUSE
        self.playPauseAction = QAction('&Pause Simulation', self)
        self.playPauseAction.setIcon(self.icons['PAUSE'])
        self.playPauseAction.setStatusTip('Pause Simulation')
        self.playPauseAction.triggered.connect(self._togglePlayPause)
        # SET SIMULATION TIME
        self.setSimulationTimeAction = QAction('&Set Simulation DateTime', self)
        self.setSimulationTimeAction.setIcon(self.icons['TIME'])
        self.setSimulationTimeAction.setStatusTip('Set Simulation DateTime')
        self.setSimulationTimeAction.triggered.connect(self._setSimulationTime)

        # ADD PLOT TAB
        self.addPlotTabAction = QAction('&Add Plot Tab', self)
        self.addPlotTabAction.setIcon(self.icons['ADD_TAB'])
        self.addPlotTabAction.setStatusTip('Add a new Plot Tab')
        self.addPlotTabAction.triggered.connect(self._addPlotTab)
        # REMOVE PLOT TAB
        self.removePlotTabAction = QAction('&Remove Current Plot Tab', self)
        self.removePlotTabAction.setIcon(self.icons['CLOSE_TAB'])
        self.removePlotTabAction.setStatusTip('Remove the Current Plot Tab')
        self.removePlotTabAction.triggered.connect(self._removePlotTab)
        # REMOVE ALL PLOT TABS
        self.removeAllPlotTabsAction = QAction('&Remove All Plot Tabs', self)
        self.removeAllPlotTabsAction.setIcon(self.icons['CLOSE_ALL_TABS'])
        self.removeAllPlotTabsAction.setStatusTip('Remove All Plot Tabs')
        self.removeAllPlotTabsAction.triggered.connect(self._removeAllPlotTabs)
        # ADD LINE PLOT
        self.addLinePlotAction = QAction('&Add Line Plot', self)
        self.addLinePlotAction.setIcon(self.icons['LINE_PLOT'])
        self.addLinePlotAction.setStatusTip('Add a Line Plot to the Current Plot Tab')
        self.addLinePlotAction.triggered.connect(self._addLinePlot)
        # ADD TIME SERIES PLOT
        self.addTimeSeriesAction = QAction('&Add Time Series', self)
        self.addTimeSeriesAction.setIcon(self.icons['TIME_SERIES'])
        self.addTimeSeriesAction.setStatusTip('Add a Time Series to the Current Plot Tab')
        self.addTimeSeriesAction.triggered.connect(self._addTimeSeriesPlot)
        # ADD POLAR PLOT
        self.addPolarPlotAction = QAction('&Add Polar Plot', self)
        self.addPolarPlotAction.setIcon(self.icons['POLAR'])
        self.addPolarPlotAction.setStatusTip('Add a Polar Plot to the Current Plot Tab')
        self.addPolarPlotAction.triggered.connect(self._addPolarPlot)

        # OPEN DATA ENGINE REQUESTS REGISTRY
        self.openEngineRegistryAction = QAction('&Data Registry', self)
        self.openEngineRegistryAction.setStatusTip('Open Orbital Engine Data Registry')
        self.openEngineRegistryAction.triggered.connect(self._openRegistryInspector)
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
        # QUIT APPLICATION
        self.quitAction = QAction('&Quit', self)
        self.quitAction.setStatusTip('Quit Application')
        self.quitAction.triggered.connect(self.close)

    def _createMenuBar(self):
        self.menuBar = self.menuBar()
        ### FILE MENU ###
        self.fileMenu = self.menuBar.addMenu('&File')
        self.fileMenu.addAction(self.quitAction)
        ### VIEW MENU ###
        self.viewMenu = self.menuBar.addMenu('&View')
        self.viewMenu.addAction(self.resetViewConfigAction)
        self.viewMenu.addAction(self.setViewConfigAsDefaultAction)
        self.viewMenu.addSeparator()
        # 2D MAP MENU
        self.map2dMenu = self.viewMenu.addMenu('&2D Map')
        self.map2dMenu.addAction(self.showGrid2dAction)
        self.map2dMenu.addAction(self.showNightLayerAction)
        self.map2dMenu.addAction(self.sunIndicatorAction)
        self.map2dMenu.addAction(self.showMap2dTerminatorAction)
        self.map2dMenu.addAction(self.vernalPointAction)
        self.map2dMenu.addSeparator()
        self.map2dMenu.addAction(self.showGroundTracks2dAction)
        self.map2dMenu.addAction(self.showFootprints2dAction)
        self.map2dMenu.addSeparator()
        self.map2dMenu.addAction(self.reset2dCameraViewAction)
        # 3D VIEW MENU
        self.view3dMenu = self.viewMenu.addMenu('&3D View')
        self.view3dMenu.addAction(self.showEarthAction)
        self.view3dMenu.addAction(self.showEarthGridAction)
        self.view3dMenu.addAction(self.showEciAxesAction)
        self.view3dMenu.addAction(self.showEcefAxesAction)
        self.view3dMenu.addSeparator()
        self.view3dMenu.addAction(self.showOrbitPaths3dAction)
        self.view3dMenu.addSeparator()
        self.view3dMenu.addAction(self.reset3dCameraViewAction)
        # PLOT VIEW MENU
        self.plotMenu = self.viewMenu.addMenu('&Plots')
        self.plotTabMenu = self.plotMenu.addMenu('&Tabs')
        self.plotTabMenu.addAction(self.addPlotTabAction)
        self.plotTabMenu.addAction(self.removePlotTabAction)
        self.plotTabMenu.addAction(self.removeAllPlotTabsAction)
        self.plotMenu.addSeparator()
        self.plotMenu.addAction(self.addTimeSeriesAction)
        self.plotMenu.addAction(self.addLinePlotAction)
        self.plotMenu.addAction(self.addPolarPlotAction)
        ### TOOLS MENU ###
        self.toolsMenu = self.menuBar.addMenu('&Tools')
        self.simulationMenu = self.toolsMenu.addMenu('&Simulation')
        self.simulationMenu.addAction(self.playPauseAction)
        self.simulationMenu.addAction(self.setSimulationTimeAction)
        ### HELP MENU ###
        self.helpMenu = self.menuBar.addMenu('&Help')
        self.helpMenu.addAction(self.openEngineRegistryAction)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.githubAction)
        self.helpMenu.addAction(self.reportIssueAction)

    def _createToolBars(self):
        # MAIN TOOLBAR
        self.mainToolBar = QToolBar('Main Toolbar', self)
        self.mainToolBar.setMovable(False)
        self.mainToolBar.addAction(self.open3dViewAction)
        self.mainToolBar.addAction(self.open2dMapAction)
        self.mainToolBar.addAction(self.openPlotViewAction)
        # 3D VIEW TOOLBAR
        self.view3dToolBar = QToolBar('3D View Toolbar', self)
        self.view3dToolBar.addAction(self.showEarthAction)
        self.view3dToolBar.addAction(self.showEarthGridAction)
        self.view3dToolBar.addAction(self.showEciAxesAction)
        self.view3dToolBar.addAction(self.showEcefAxesAction)
        self.view3dToolBar.addSeparator()
        self.view3dToolBar.addAction(self.reset3dCameraViewAction)
        # 2D MAP TOOLBAR
        self.map2dToolBar = QToolBar('2D Map Toolbar', self)
        self.map2dToolBar.addAction(self.showGrid2dAction)
        self.map2dToolBar.addAction(self.sunIndicatorAction)
        self.map2dToolBar.addAction(self.showNightLayerAction)
        self.map2dToolBar.addAction(self.showMap2dTerminatorAction)
        self.map2dToolBar.addSeparator()
        self.map2dToolBar.addAction(self.reset2dCameraViewAction)
        # PLOT VIEW TOOLBAR
        self.plotViewToolBar = QToolBar('Plot View Toolbar', self)
        self.plotViewToolBar.addAction(self.addPlotTabAction)
        self.plotViewToolBar.addSeparator()
        self.plotViewToolBar.addAction(self.addTimeSeriesAction)
        self.plotViewToolBar.addAction(self.addLinePlotAction)
        self.plotViewToolBar.addAction(self.addPolarPlotAction)

        # ADDING ALL TOOLBARS TO THE MAIN WINDOW
        self.addToolBar(self.mainToolBar)
        self.addToolBar(self.view3dToolBar)
        self.addToolBar(self.map2dToolBar)
        self.addToolBar(self.plotViewToolBar)

    def _manageToolBarVisibility(self, tabName):
        if tabName == '2D_MAP':
            self.view3dToolBar.setVisible(False)
            self.map2dToolBar.setVisible(True)
            self.plotViewToolBar.setVisible(False)
        elif tabName == '3D_VIEW':
            self.view3dToolBar.setVisible(True)
            self.map2dToolBar.setVisible(False)
            self.plotViewToolBar.setVisible(False)
        elif tabName == 'PLOT_VIEW':
            self.view3dToolBar.setVisible(False)
            self.map2dToolBar.setVisible(False)
            self.plotViewToolBar.setVisible(True)
        else:
            self.view3dToolBar.setVisible(False)
            self.map2dToolBar.setVisible(False)
            self.plotViewToolBar.setVisible(False)

    def _createIcons(self):
        self.iconPath = os.path.join(self.currentDir, f'src/assets/icons')
        self.icons['SATELLITE_GLOBE'] = QIcon(os.path.join(self.iconPath, 'satellite-globe.png'))
        self.icons['MAP'] = QIcon(os.path.join(self.iconPath, 'map.png'))
        self.icons['PLOT'] = QIcon(os.path.join(self.iconPath, 'plot.png'))
        self.icons['EARTH'] = QIcon(os.path.join(self.iconPath, 'earth.png'))
        self.icons['EARTH_GRID'] = QIcon(os.path.join(self.iconPath, 'earth-grid.png'))
        self.icons['ECI'] = QIcon(os.path.join(self.iconPath, 'eci.png'))
        self.icons['ECEF'] = QIcon(os.path.join(self.iconPath, 'ecef.png'))
        self.icons['RESET_VIEW'] = QIcon(os.path.join(self.iconPath, 'reset-view.png'))
        self.icons['MAP_GRID'] = QIcon(os.path.join(self.iconPath, 'map-grid.png'))
        self.icons['SHADOW'] = QIcon(os.path.join(self.iconPath, 'shadow.png'))
        self.icons['SUN'] = QIcon(os.path.join(self.iconPath, 'sun.png'))
        self.icons['SUNSET'] = QIcon(os.path.join(self.iconPath, 'sunset.png'))
        self.icons['ADD_TAB'] = QIcon(os.path.join(self.iconPath, 'add-tab.png'))
        self.icons['CLOSE_TAB'] = QIcon(os.path.join(self.iconPath, 'close-tab.png'))
        self.icons['CLOSE_ALL_TABS'] = QIcon(os.path.join(self.iconPath, 'close-all-tabs.png'))
        self.icons['LINE_PLOT'] = QIcon(os.path.join(self.iconPath, 'line-plot.png'))
        self.icons['TIME_SERIES'] = QIcon(os.path.join(self.iconPath, 'time-series.png'))
        self.icons['POLAR'] = QIcon(os.path.join(self.iconPath, 'polar.png'))
        self.icons['PLAY'] = QIcon(os.path.join(self.iconPath, 'play.png'))
        self.icons['PAUSE'] = QIcon(os.path.join(self.iconPath, 'pause.png'))
        self.icons['FAST_FORWARD'] = QIcon(os.path.join(self.iconPath, 'fast-forward.png'))
        self.icons['SLOW_DOWN'] = QIcon(os.path.join(self.iconPath, 'slow-down.png'))
        self.icons['RESUME'] = QIcon(os.path.join(self.iconPath, 'resume.png'))
        self.icons['TIME'] = QIcon(os.path.join(self.iconPath, 'time.png'))
        self.icons['BUG'] = QIcon(os.path.join(self.iconPath, 'bug.png'))
        self.icons['GITHUB'] = QIcon(os.path.join(self.iconPath, 'github.png'))

    def _togglePlayPause(self):
        if self.centralViewWidget.timeline.isRunning:
            self.centralViewWidget.timeline.toggleRequested.emit()
            self.playPauseAction.setIcon(self.icons['PLAY'])
            self.playPauseAction.setText('&Play Simulation')
            self.playPauseAction.setStatusTip('Play Simulation')
        else:
            self.centralViewWidget.timeline.toggleRequested.emit()
            self.playPauseAction.setIcon(self.icons['PAUSE'])
            self.playPauseAction.setText('&Pause Simulation')
            self.playPauseAction.setStatusTip('Pause Simulation')

    def _setSimulationTime(self):
        currentDatetime = self.centralViewWidget.clock.getDateTime()
        dialog = SetTimeDialog(currentDatetime, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            newDatetime = dialog.getDatetime().toPyDateTime()
            self.centralViewWidget.clock.setDateTime(newDatetime)
            self.centralViewWidget.timeline.setTime(newDatetime)

    def _checkEarth(self, checked):
        self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_EARTH'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkEarthGrid(self, checked):
        self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_EARTH_GRID'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkEciAxes(self, checked):
        self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_ECI_AXES'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkEcefAxes(self, checked):
        self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_ECEF_AXES'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _reset3dCameraView(self):
        self.centralViewWidget.view3dWidget.resetView()

    def _reset2dCameraView(self):
        self.centralViewWidget.map2dWidget.resetView()

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

    def _updateActionStates(self, model: ActiveObjectsModel | None = None):
        if model is None:
            model = self.activeObjectsDock.getActiveObjectsModel()
        canConfigure = (len(model.selectedObjects) == 1 and not model.isGroupSelected)
        for action in self._selectionDependentActions:
            action.setEnabled(canConfigure)
        self._updateObjectConfigDocks(model)

    def _updateObjectConfigDocks(self, model: ActiveObjectsModel | None = None):
        if model is None:
            model = self.activeObjectsDock.getActiveObjectsModel()
        hasSingleObject = len(model.selectedObjects) == 1 and not model.isGroupSelected
        hasGroup = model.isGroupSelected and model.selectedGroupName is not None
        if hasSingleObject:
            obj = next(iter(model.selectedObjects))
            self.objectViewConfigDock.setActiveObjects(model)
            self.objectViewConfigDock.setSelectedObject(obj.noradIndex, self.settings['VIEW_CONFIG']['OBJECTS'])
        elif hasGroup:
            groupName = model.selectedGroupName
            self.objectViewConfigDock.setActiveObjects(model)
            self.objectViewConfigDock.setSelectedGroup(groupName)
        else:
            self.objectViewConfigDock.setActiveObjects(model)
            self.objectViewConfigDock.setSelectedObject(None, self.settings['VIEW_CONFIG']['OBJECTS'])

    def _updateObjectInfoDock(self, model: ActiveObjectsModel | None = None):
        if model is None:
            model = self.activeObjectsDock.getActiveObjectsModel()
        canConfigure = (len(model.selectedObjects) == 1 and not model.isGroupSelected)
        if canConfigure:
            noradIndex = next(iter(model.selectedObjects))
            if self.tleDatabase is None:
                return
            row = self.tleDatabase.dataFrame[self.tleDatabase.dataFrame['NORAD_CAT_ID'] == noradIndex]
            self.objectInfoDock.setObject(row.iloc[0] if not row.empty else None)
        else:
            self.objectInfoDock.clear()

    def _restoreWindow(self):
        self.setWindowTitle('Satellite Tracker')
        if self.settings['WINDOW']['MAXIMIZED']:
            self.showMaximized()
        else:
            windowGeometry = self.settings['WINDOW']['GEOMETRY']
            self.setGeometry(windowGeometry['X'], windowGeometry['Y'], windowGeometry['WIDTH'], windowGeometry['HEIGHT'])

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

    def setDatabases(self, tleDatabase, starDatabase):
        self.tleDatabase, self.starDatabase = tleDatabase, starDatabase
        self.centralViewWidget.setDatabases(self.tleDatabase, starDatabase)
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))
        self.objectViewConfigDock.applyGlobalVisibility(copy.deepcopy(self.settings['VIEW_CONFIG']), self.settings['CURRENT_TAB'])
        self.activeObjectsDock.populate(self.tleDatabase, self.settings.get('ACTIVE_OBJECTS_MODEL', {}))
        self.centralViewWidget.setActiveObjects(self.activeObjectsDock.getActiveObjectsModel())
        self.centralViewWidget.requestManager.submitAllFixed()
        self.centralViewWidget.start()
        self._updateActionStates()
        self.centralViewWidget.stackedWidget.setCurrentIndex(getKeyFromValue(self.centralViewWidget.TABS, self.settings['CURRENT_TAB']))
        self.centralViewWidget.stackedChanged.connect(self._updateStackedWidget)
        self.centralViewWidget.setPlotViewLayoutConfiguration(self.settings['PLOT_VIEW'])
        self.setObjectConfigWidgetsVisibility()
        self._manageToolBarVisibility(self.settings['CURRENT_TAB'])
        self._restoreWindow()

    def setObjectConfigWidgetsVisibility(self):
        if self.settings['CURRENT_TAB'] == '2D_MAP':
            self.objectViewConfigDock.setVisible(True)
            self.objectViewConfigDock.setViewMode('2D')
        if self.settings['CURRENT_TAB'] == '3D_VIEW':
            self.objectViewConfigDock.setVisible(True)
            self.objectViewConfigDock.setViewMode('3D')
        if self.settings['CURRENT_TAB'] == 'PLOT_VIEW':
            self.objectViewConfigDock.setVisible(False)

    def loadSettings(self):
        self.settings = loadSettingsJson(self.settingsPath)

    def saveSettings(self):
        saveSettingsJson(self.settingsPath, self.settings)

    def _onActiveObjectsChanged(self):
        model = self.activeObjectsDock.getActiveObjectsModel()
        self.settings['ACTIVE_OBJECTS_MODEL'] = model.toDict()
        for noradIndex in model.allNoradIndices():
            if str(noradIndex) not in self.settings['VIEW_CONFIG']['OBJECTS']:
                self.settings['VIEW_CONFIG']['OBJECTS'][str(noradIndex)] = copy.deepcopy(self.settings['VIEW_CONFIG']['DEFAULT_CONFIG'])
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))
        self.centralViewWidget.setActiveObjects(model)
        self.saveSettings()
        self._updateActionStates()
        self._updateObjectInfoDock()

    def _open2dMap(self):
        self.centralViewWidget.stackedWidget.setCurrentIndex(getKeyFromValue(self.centralViewWidget.TABS, '2D_MAP'))
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))
        self.open2dMapAction.setChecked(True)
        self.open3dViewAction.setChecked(False)
        self.openPlotViewAction.setChecked(False)

    def _open3dView(self):
        self.centralViewWidget.stackedWidget.setCurrentIndex(getKeyFromValue(self.centralViewWidget.TABS, '3D_VIEW'))
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))
        self.open2dMapAction.setChecked(False)
        self.open3dViewAction.setChecked(True)
        self.openPlotViewAction.setChecked(False)

    def _openPlotView(self):
        self.centralViewWidget.stackedWidget.setCurrentIndex(getKeyFromValue(self.centralViewWidget.TABS, 'PLOT_VIEW'))
        self.open2dMapAction.setChecked(False)
        self.open3dViewAction.setChecked(False)
        self.openPlotViewAction.setChecked(True)

    def _addPlotTab(self):
        self.centralViewWidget.plotViewWidget.addNewTab()

    def _removePlotTab(self):
        self.centralViewWidget.plotViewWidget.closeCurrentTab()

    def _removeAllPlotTabs(self):
        self.centralViewWidget.plotViewWidget.closeAllTabs()

    def _addLinePlot(self):
        self.centralViewWidget.addLinePlot()

    def _addTimeSeriesPlot(self):
        self.centralViewWidget.addTimeSeriesPlot()

    def _addPolarPlot(self):
        self.centralViewWidget.addPolarPlot()

    def _onObjectViewConfigChanged(self, noradIndex, newConfiguration):
        self.settings['VIEW_CONFIG']['OBJECTS'][str(noradIndex)] = newConfiguration
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _onGroupViewConfigChanged(self, groupName, config):
        model = self.activeObjectsDock.getActiveObjectsModel()
        model.setGroupConfig(groupName, config)
        self.settings['ACTIVE_OBJECTS_MODEL'] = model.toDict()
        self.saveSettings()
        self.centralViewWidget.setActiveObjects(model)

    def _resetObjectViewConfig(self):
        model = self.activeObjectsDock.getActiveObjectsModel()
        if len(model.selectedObjects) != 1 or model.isGroupSelected:
            return
        noradIndex = next(iter(model.selectedObjects))
        self.settings['VIEW_CONFIG']['OBJECTS'][str(noradIndex)] = copy.deepcopy(self.settings['VIEW_CONFIG']['DEFAULT_CONFIG'])
        self.saveSettings()
        self.objectViewConfigDock.setSelectedObject(noradIndex, self.settings['VIEW_CONFIG']['OBJECTS'])
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _setObjectViewConfigAsDefault(self):
        model = self.activeObjectsDock.getActiveObjectsModel()
        if len(model.selectedObjects) != 1 or model.isGroupSelected:
            return
        noradIndex = next(iter(model.selectedObjects))
        self.settings['VIEW_CONFIG']['DEFAULT_CONFIG'] = copy.deepcopy(self.settings['VIEW_CONFIG']['OBJECTS'][str(noradIndex)])
        self.saveSettings()

    def _check2dGrid(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_GRID'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkNightLayer(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_NIGHT'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkSunIndicator(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_SUN'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkVernalPoint(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_VERNAL'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _checkMap2dTerminator(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_TERMINATOR'] = checked
        self.saveSettings()
        self.centralViewWidget.setDisplayConfiguration(copy.deepcopy(self.settings['VIEW_CONFIG']))

    def _change3dViewCameraSettings(self):
        self.settings['VIEW_CONFIG']['3D_VIEW']['ZOOM'] = self.centralViewWidget.view3dWidget.zoom
        self.settings['VIEW_CONFIG']['3D_VIEW']['ROTATION']['X'] = self.centralViewWidget.view3dWidget.rotX
        self.settings['VIEW_CONFIG']['3D_VIEW']['ROTATION']['Y'] = self.centralViewWidget.view3dWidget.rotY
        self.saveSettings()

    def _toggleGroundTracks2d(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_GROUND_TRACKS'] = checked
        self.saveSettings()
        self._updateGlobalVisibility()

    def _toggleFootprints2d(self, checked):
        self.settings['VIEW_CONFIG']['2D_MAP']['SHOW_FOOTPRINTS'] = checked
        self.saveSettings()
        self._updateGlobalVisibility()

    def _toggleOrbitPaths3d(self, checked):
        self.settings['VIEW_CONFIG']['3D_VIEW']['SHOW_ORBIT_PATHS'] = checked
        self.saveSettings()
        self._updateGlobalVisibility()

    def _updateGlobalVisibility(self):
        viewConfiguration = copy.deepcopy(self.settings['VIEW_CONFIG'])
        self.centralViewWidget.setDisplayConfiguration(viewConfiguration)
        self.objectViewConfigDock.applyGlobalVisibility(viewConfiguration, self.settings['CURRENT_TAB'])

    def _openRegistryInspector(self):
        self.registryWindow = PlotRequestRegistryWindow(self.centralViewWidget.requestManager)
        self.registryWindow.show()

    def closeEvent(self, event):
        self.centralViewWidget.close()
        if self.registryWindow is not None:
            self.registryWindow.close()
        self.settings['PLOT_VIEW']  = self.centralViewWidget.plotViewWidget.getLayoutConfiguration()
        self.settings['WINDOW']['MAXIMIZED'] = self.isMaximized()
        if not self.isMaximized():
            g = self.geometry()
            self.settings['WINDOW']['GEOMETRY'] = {'X': g.x(), 'Y': g.y(), 'WIDTH': g.width(), 'HEIGHT': g.height()}
        model = self.activeObjectsDock.getActiveObjectsModel()
        self.settings['ACTIVE_OBJECTS_MODEL'] = model.toDict()
        self.saveSettings()
        event.accept()


class CentralViewWidget(QWidget):
    activeObjectsChanged = pyqtSignal(object)
    stackedChanged = pyqtSignal(int)
    timeLineModeChanged = pyqtSignal(str)
    TABS = {0: '3D_VIEW', 1: '2D_MAP', 2: 'PLOT_VIEW'}
    TIMELINE_MODES = {0: 'UTC', 1: 'LOCAL', 2: 'DELTA'}

    def __init__(self, parent=None, icons=None, currentTab='3D_VIEW', currentDir=None, timeLineMode='UTC'):
        super().__init__(parent)
        self.currentDir = currentDir
        self.icons = icons if icons is not None else {}
        self.tleDatabase, self.starDatabase = None, None
        # DATA REQUEST SYSTEM
        self.variableRegistry = VariableRegistry()
        self._requestCounter = 100000
        self.requestManager = PlotRequestManager(tleDatabase=None, variableRegistry=self.variableRegistry)
        self.requestManager.resultReady.connect(self._onPlotResultsReady)
        # CLOCK & ORBITS CALCULATIONS WORKER
        self.clock = SimulationClock()
        self.workerThread = QThread(self)
        self.orbitWorker = OrbitWorker(None)
        self.orbitWorker.moveToThread(self.workerThread)
        self.workerThread.start()

        # TIMELINE WIDGET
        self.timeline = TimelineWidget(self, self.currentDir)
        self.timeline.displayMode = getKeyFromValue(self.TIMELINE_MODES, timeLineMode)
        self.timeline.playRequested.connect(self.clock.play)
        self.timeline.pauseRequested.connect(self.clock.pause)
        self.timeline.toggleRequested.connect(self.clock.toggle)
        self.timeline.speedRequested.connect(self._onSpeedRequested)
        self.timeline.timeRequested.connect(self.clock.setDateTime)
        self.timeline.resumeRequested.connect(self._resume)
        self.timeline.timeFormatChanged.connect(self._onTimeModeChanged)
        self.clock.timeChanged.connect(self._onClockTimeChanged)
        self.clock.stateChanged.connect(self.timeline.setRunning)

        # VISUALIZATION CONFIGURATION
        self.activeObjects: ActiveObjectsModel | None = None
        self.selectedObject = None
        self.displayConfiguration = {}
        self.lastPositions = {'3D_VIEW': {}, '2D_MAP': {}, 'PLOT_VIEW': {}}

        # MAIN TABS
        self.view3dWidget = View3dWidget()
        self.map2dWidget = Map2dWidget()
        self.plotViewWidget = PlotViewTabWidget(currentDir=self.currentDir)
        self.stackedWidget = QStackedWidget()
        self.stackedWidget.addWidget(self.view3dWidget)
        self.stackedWidget.addWidget(self.map2dWidget)
        self.stackedWidget.addWidget(self.plotViewWidget)
        self.stackedWidget.setCurrentIndex(getKeyFromValue(self.TABS, currentTab))

        self.orbitWorker.positionsReady.connect(self._onPositionsReady)
        self.stackedWidget.currentChanged.connect(self._onTabChanged)
        self.view3dVisible = (self.stackedWidget.currentWidget() is self.view3dWidget)
        self.map2dVisible = (self.stackedWidget.currentWidget() is self.map2dWidget)
        self.plotViewVisible = (self.stackedWidget.currentWidget() is self.plotViewWidget)

        # MAIN LAYOUT
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stackedWidget, 1)
        layout.addWidget(self.timeline, 0)

    def _onTabChanged(self, index):
        self.map2dVisible = (self.stackedWidget.currentWidget() is self.map2dWidget)
        self.view3dVisible = (self.stackedWidget.currentWidget() is self.view3dWidget)
        self.plotViewVisible = (self.stackedWidget.currentWidget() is self.plotViewWidget)
        currentTime = self.clock.currentDateTime
        if not self.clock.isRunning:
            if self.map2dVisible or self.view3dVisible:
                QMetaObject.invokeMethod(self.orbitWorker, "compute", Qt.QueuedConnection, Q_ARG(object, currentTime), Q_ARG(dict, copy.deepcopy(self.displayConfiguration)))
            if self.plotViewVisible:
                self.requestManager.tick(currentTime)
        if self.map2dVisible and self.lastPositions['2D_MAP']:
            self._refresh2dMap()
        if self.view3dVisible and self.lastPositions['3D_VIEW']:
            self._refresh3dView()
        if self.plotViewVisible and self.lastPositions['PLOT_VIEW']:
            self._refreshPlotView()
        self.stackedChanged.emit(index)

    def _onPositionsReady(self, positions: dict):
        if self.lastPositions is None:
            self.lastPositions = {'3D_VIEW': {}, '2D_MAP': {}, 'PLOT_VIEW': {}}
        self.lastPositions.update(positions)
        if self.map2dVisible and self.lastPositions['2D_MAP']:
            self._refresh2dMap()
        if self.view3dVisible and self.lastPositions['3D_VIEW']:
            self._refresh3dView()
        if self.plotViewVisible and self.lastPositions['PLOT_VIEW']:
            self._refreshPlotView()

    def setDatabases(self, tleDatabase, starDatabase):
        self.tleDatabase, self.starDatabase = tleDatabase, starDatabase
        self.orbitWorker.tleDatabase = tleDatabase
        self.requestManager.tleDatabase = tleDatabase

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects
        self.orbitWorker.setActiveObjects(activeObjects)
        self.view3dWidget.setActiveObjects(activeObjects)
        self.map2dWidget.setActiveObjects(activeObjects)
        self.activeObjectsChanged.emit(activeObjects)
        if self.map2dVisible and self.lastPositions['2D_MAP']:
            self._refresh2dMap()
        if self.view3dVisible and self.lastPositions['3D_VIEW']:
            self._refresh3dView()
        if self.plotViewVisible and self.lastPositions['PLOT_VIEW']:
            self._refreshPlotView()

    def setDisplayConfiguration(self, displayConfiguration):
        self.displayConfiguration = displayConfiguration
        self._refresh2dMap()
        self._refresh3dView()

    def _refresh2dMap(self):
        if self.map2dVisible and self.lastPositions['2D_MAP']:
            self.map2dWidget.updateMap({'2D_MAP': self.lastPositions['2D_MAP']}, self.displayConfiguration)

    def _refresh3dView(self):
        if self.view3dVisible and self.lastPositions['3D_VIEW']:
            self.view3dWidget.updateData({'3D_VIEW' : self.lastPositions['3D_VIEW']}, self.displayConfiguration)

    def _refreshPlotView(self):
        if self.plotViewVisible and self.lastPositions['PLOT_VIEW']:
            self.plotViewWidget.updateData({'PLOT_VIEW' : self.lastPositions['PLOT_VIEW']})

    def start(self):
        self.clock.play()

    def _onClockTimeChanged(self, simTime: datetime):
        self.timeline.setTime(simTime)
        if self.map2dVisible or self.view3dVisible:
            QMetaObject.invokeMethod(self.orbitWorker, "compute", Qt.QueuedConnection, Q_ARG(object, simTime), Q_ARG(dict, copy.deepcopy(self.displayConfiguration)))
        if self.plotViewVisible:
            self.requestManager.tick(simTime)

    def _onTimeModeChanged(self, mode):
        self.timeLineModeChanged.emit(self.TIMELINE_MODES[mode])

    def _onSpeedRequested(self, speed):
        self.clock.setSpeed(speed)

    def _resume(self):
        now = datetime.utcnow()
        self.timeline.setTime(now)
        self.clock.setDateTime(now)

    def generateRequestIndex(self):
        self._requestCounter += 1
        return self._requestCounter

    def _onPlotDataRequestCreated(self, requestIndex, request):
        self.requestManager.create(requestIndex, request)

    def _onPlotDataRequestUpdated(self, requestIndex, request):
        self.requestManager.update(requestIndex, request)

    def _onPlotDataRequestDestroyed(self, requestIndex):
        self.requestManager.remove(requestIndex)

    def _onPlotResultsReady(self, data):
        if self.lastPositions is None:
            self.lastPositions = {'3D_VIEW': {}, '2D_MAP': {}, 'PLOT_VIEW': {}}
        self.lastPositions['PLOT_VIEW'] = data
        if self.plotViewVisible and self.lastPositions['PLOT_VIEW']:
            self._refreshPlotView()

    def setPlotViewLayoutConfiguration(self, layout):
        self.plotViewWidget.closeAllTabs()
        for tabConfiguration in layout.get("TABS", []):
            self.plotViewWidget.addNewTab(tabConfiguration["NAME"])
            for dockWidgetConfiguration in tabConfiguration["DOCKS"]:
                title = dockWidgetConfiguration["TITLE"]
                area = dockWidgetConfiguration["AREA"]
                if dockWidgetConfiguration["PLOT_TYPE"] == "LINE":
                    self.addLinePlot(configuration=dockWidgetConfiguration["CONFIGURATION"], title=title, area=area)
                if dockWidgetConfiguration["PLOT_TYPE"] == "TIME_SERIES":
                    self.addTimeSeriesPlot(configuration=dockWidgetConfiguration["CONFIGURATION"], title=title, area=area)
                if dockWidgetConfiguration["PLOT_TYPE"] == "POLAR":
                    self.addPolarPlot(configuration=dockWidgetConfiguration["CONFIGURATION"], title=title, area=area)

    def addLinePlot(self, configuration=None, title=None, area=None):
        linePlot = LinePlot(self)
        linePlot.requestIndexProvider = self.generateRequestIndex
        linePlot.dataRequestCreated.connect(self._onPlotDataRequestCreated)
        linePlot.dataRequestUpdated.connect(self._onPlotDataRequestUpdated)
        linePlot.dataRequestDestroyed.connect(self._onPlotDataRequestDestroyed)
        self.activeObjectsChanged.connect(linePlot.setActiveObjects)
        linePlot.setActiveObjects(self.activeObjects)
        if configuration is not None:
            linePlot.setConfiguration(configuration)
        self.plotViewWidget.addNewPlot(widget=linePlot, title=title, area=area)

    def addTimeSeriesPlot(self, configuration=None, title=None, area=None):
        timeSeriesPlot = TimeSeriesPlot(self)
        timeSeriesPlot.requestIndexProvider = self.generateRequestIndex
        timeSeriesPlot.dataRequestCreated.connect(self._onPlotDataRequestCreated)
        timeSeriesPlot.dataRequestUpdated.connect(self._onPlotDataRequestUpdated)
        timeSeriesPlot.dataRequestDestroyed.connect(self._onPlotDataRequestDestroyed)
        self.activeObjectsChanged.connect(timeSeriesPlot.setActiveObjects)
        timeSeriesPlot.setActiveObjects(self.activeObjects)
        if configuration is not None:
            timeSeriesPlot.setConfiguration(configuration)
        self.plotViewWidget.addNewPlot(widget=timeSeriesPlot, title=title, area=area)

    def addPolarPlot(self, configuration=None, title=None, area=None):
        polarPlot = PolarPlot(self)
        polarPlot.requestIndexProvider = self.generateRequestIndex
        polarPlot.dataRequestCreated.connect(self._onPlotDataRequestCreated)
        polarPlot.dataRequestUpdated.connect(self._onPlotDataRequestUpdated)
        polarPlot.dataRequestDestroyed.connect(self._onPlotDataRequestDestroyed)
        self.activeObjectsChanged.connect(polarPlot.setActiveObjects)
        polarPlot.setActiveObjects(self.activeObjects)
        if configuration is not None:
            polarPlot.setConfiguration(configuration)
        self.plotViewWidget.addNewPlot(widget=polarPlot, title=title, area=area)

    def closeEvent(self, event):
        self.orbitWorker.stop()
        self.workerThread.quit()
        self.workerThread.wait()
        self.requestManager.pool.waitForDone()
        super().closeEvent(event)
