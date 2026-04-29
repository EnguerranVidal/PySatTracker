import os
from typing import Optional

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon

from src.gui.plots.line import LinePlot, LinePlotSettingsWidget
from src.gui.plots.time import TimeSeriesPlot, TimeSeriesSettingsWidget
from src.gui.plots.polar import PolarPlot, PolarPlotSettingsWidget
from src.gui.common import SquareIconButton, AreaCycler


class PlotViewTabWidget(QMainWindow):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.displayConfiguration = {}
        self.lastPositions = None
        self.dockAreaCycler = AreaCycler()
        self.dockSpaces = [Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea, Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea]
        self.tabWidget = QTabWidget()
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self._closeTab)
        self.tabWidget.tabBarDoubleClicked.connect(self._tabDoubleClicked)
        self.setCentralWidget(self.tabWidget)
        self.settingsDockWidget = PlotSettingsDockWidget(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.settingsDockWidget)
        self.settingsDockWidget.hide()

    def closeCurrentTab(self):
        currentIndex = self.tabWidget.currentIndex()
        self._closeTab(currentIndex)

    def _closeTab(self, index):
        widget = self.tabWidget.widget(index)
        dockWidgets = widget.findChildren(PlotDockWidget)
        for dw in dockWidgets:
            self.settingsDockWidget.removeSettingsForDock(dw)
        self.tabWidget.removeTab(index)
        widget.deleteLater()

    def closeAllTabs(self):
        while self.tabWidget.count() > 0:
            self._closeTab(0)

    def addNewTab(self, title=None):
        if title is None:
            title = f'Tab {self.tabWidget.count() + 1}'
        self.tabWidget.addTab(QMainWindow(), title)

    def _tabDoubleClicked(self, tabIndex):
        self.tabWidget.setTabsClosable(False)
        plotTabName = self.tabWidget.tabText(tabIndex)
        lineEdit = QLineEdit(plotTabName, self.tabWidget)
        self.tabWidget.setTabText(tabIndex, '')
        tabBar = self.tabWidget.tabBar()
        tabBar.setTabButton(tabIndex, tabBar.ButtonPosition.LeftSide, lineEdit)
        lineEdit.setFocus()
        lineEdit.selectAll()
        lineEdit.editingFinished.connect(lambda: self._finishEditingTabName(tabIndex, lineEdit))

    def _finishEditingTabName(self, tabIndex, lineEdit):
        tabBar = self.tabWidget.tabBar()
        self.tabWidget.setTabText(tabIndex, lineEdit.text())
        tabBar.setTabButton(tabIndex, tabBar.ButtonPosition.LeftSide, None)
        self.tabWidget.setTabsClosable(True)
        parentTab = self.tabWidget.widget(tabIndex)
        dockWidgets = parentTab.findChildren(PlotDockWidget)
        for dockWidget in dockWidgets:
            self.settingsDockWidget.updateSettingsTabTitle(dockWidget)

    def addNewPlot(self, widget, title=None, area=None):
        currentTabIndex = self.tabWidget.currentIndex()
        if currentTabIndex == -1:
            self.addNewTab()
            currentTabIndex = 0
        title = f'Plot {len(self.tabWidget.widget(currentTabIndex).findChildren(QDockWidget))}' if title is None else title
        dockWidget = PlotDockWidget(parent=self, title=title, widget=widget, currentDir=self.currentDir)
        dockWidget.showSettingsRequested.connect(self.handleShowSettings)
        dockWidget.closed.connect(self.settingsDockWidget.removeSettingsForDock)
        area = self.dockAreaCycler.next() if area is None else area
        self.tabWidget.widget(currentTabIndex).addDockWidget(area, dockWidget)

    def handleShowSettings(self, dockWidget):
        parentTab = dockWidget.parent()
        tabIndex = self.tabWidget.indexOf(parentTab)
        plotTabName = self.tabWidget.tabText(tabIndex)
        plotDockWidgetName = dockWidget.windowTitle()
        title = f"{plotTabName} > {plotDockWidgetName}"
        self.settingsDockWidget.addSettingsTab(title, dockWidget)
        self.settingsDockWidget.show()
        self.settingsDockWidget.raise_()
        self.settingsDockWidget.activateWindow()

    def updateData(self, positions: dict):
         self.lastPositions = positions
         for i in range(self.tabWidget.count()):
            tab = self.tabWidget.widget(i)
            dockWidgets = tab.findChildren(PlotDockWidget)
            for dockWidget in dockWidgets:
                dockWidget.plotWidget.updateData(positions)

    def getLayoutConfiguration(self):
        layout = {"TABS": []}
        for i in range(self.tabWidget.count()):
            tab = self.tabWidget.widget(i)
            tabName = self.tabWidget.tabText(i)
            dockWidgets = []
            for dock in tab.findChildren(PlotDockWidget):
                config = dock.plotWidget.configuration
                if isinstance(dock.plotWidget, LinePlot):
                    plotType = "LINE"
                elif isinstance(dock.plotWidget, TimeSeriesPlot):
                    plotType = "TIME_SERIES"
                elif isinstance(dock.plotWidget, PolarPlot):
                    plotType = "POLAR"
                else:
                    plotType = "NONE"
                dockWidgets.append({"TITLE": dock.windowTitle(), "AREA": tab.dockWidgetArea(dock), "PLOT_TYPE": plotType, "CONFIGURATION": config})
            layout["TABS"].append({"NAME": tabName, "DOCKS": dockWidgets})
        return layout


class PlotDockWidget(QDockWidget):
    showSettingsRequested = pyqtSignal('QDockWidget')
    closed = pyqtSignal('QDockWidget')

    def __init__(self, parent=None, title=None, currentDir:str = None, widget: Optional[LinePlot] = None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.setMouseTracking(True)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.plotWidget = widget
        self.setWidget(self.plotWidget)
        self.setWindowTitle(title)

        settingsIconPath = os.path.join(self.currentDir, f'src/assets/icons/settings.png')
        self.settingsButton = SquareIconButton(settingsIconPath, parent=self, flat=True, size=30)
        self.settingsButton.setIcon(QIcon(settingsIconPath))
        self.settingsButton.hide()
        self.settingsButton.clicked.connect(lambda: self.showSettingsRequested.emit(self))
        self.lastPositions, self.visibleNorads = None, set()

    def enterEvent(self, event):
        self.settingsButton.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.settingsButton.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        buttonSize = self.settingsButton.sizeHint()
        hasTitleBar = not bool(self.features() & QDockWidget.NoDockWidgetFeatures)
        x, y = self.plotWidget.width() - buttonSize.width() - 2, 30 if hasTitleBar else 0
        self.settingsButton.setGeometry(x, y, buttonSize.width(), buttonSize.height())

    def closeEvent(self, event):
        if hasattr(self.plotWidget, "destroyDataRequest"):
            self.plotWidget.destroyDataRequest()
        self.closed.emit(self)
        super().closeEvent(event)
        self.deleteLater()


class PlotSettingsDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Settings")
        self.tabWidget = QTabWidget(self)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.tabCloseRequested.connect(self._closeSettingsTab)
        self.setWidget(self.tabWidget)
        self.setFeatures(QDockWidget.DockWidgetClosable)
        self.dockToSettings = {}

    def addSettingsTab(self, title, dockWidget: PlotDockWidget):
        if dockWidget not in self.dockToSettings:
            if isinstance(dockWidget.plotWidget, LinePlot):
                widget = LinePlotSettingsWidget(dockWidget.plotWidget, dockWidget=dockWidget, parent=self.tabWidget)
            elif isinstance(dockWidget.plotWidget, TimeSeriesPlot):
                widget = TimeSeriesSettingsWidget(dockWidget.plotWidget, dockWidget=dockWidget, parent=self.tabWidget)
            elif isinstance(dockWidget.plotWidget, PolarPlot):
                widget = PolarPlotSettingsWidget(dockWidget.plotWidget, dockWidget=dockWidget, parent=self.tabWidget)
            else:
                widget = QWidget()
            index = self.tabWidget.addTab(widget, title)
            self.dockToSettings[dockWidget] = widget
            dockWidget.windowTitleChanged.connect(lambda title: self.updateSettingsTabTitle(dockWidget))
        else:
            widget = self.dockToSettings[dockWidget]
            index = self.tabWidget.indexOf(widget)
        self.tabWidget.setCurrentIndex(index)

    def removeSettingsForDock(self, dockWidget: PlotDockWidget):
        if dockWidget in self.dockToSettings:
            widget = self.dockToSettings[dockWidget]
            index = self.tabWidget.indexOf(widget)
            if index != -1:
                self._closeSettingsTab(index)
        if self.tabWidget.count() == 0:
            self.hide()

    def _closeSettingsTab(self, index: int):
        widget = self.tabWidget.widget(index)
        self.tabWidget.removeTab(index)
        dockToRemove = None
        for dock, w in list(self.dockToSettings.items()):
            if w == widget:
                dockToRemove = dock
                break
        if dockToRemove:
            del self.dockToSettings[dockToRemove]
        widget.deleteLater()
        if self.tabWidget.count() == 0:
            self.hide()

    def updateSettingsTabTitle(self, dockWidget: PlotDockWidget):
        if dockWidget in self.dockToSettings:
            widget = self.dockToSettings[dockWidget]
            index = self.tabWidget.indexOf(widget)
            if index != -1:
                main = self.parent()
                parentTab = dockWidget.parent()
                tabIndex = main.tabWidget.indexOf(parentTab)
                plotTabName = main.tabWidget.tabText(tabIndex)
                plotDockWidgetName = dockWidget.windowTitle()
                title = f"{plotTabName} > {plotDockWidgetName}"
                self.tabWidget.setTabText(index, title)
