import os
from typing import Optional

from PyQt5.QtGui import QIcon
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *

from gui.objects import AreaCycler
from gui.widgets import SquareIconButton


class PlotViewTabWidget(QMainWindow):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir
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

    def addNewLinePlot(self):
        currentTabIndex = self.tabWidget.currentIndex()
        if currentTabIndex == -1:
            self.addNewTab()
            currentTabIndex = 0
        currentWidgetChildren = self.tabWidget.widget(currentTabIndex).findChildren(QDockWidget)
        dockWidget = PlotDockWidget(parent=self, title=f'Plot {len(currentWidgetChildren)}', widget=LinePlot(self), currentDir=self.currentDir)
        dockWidget.showSettingsRequested.connect(self.handleShowSettings)
        area = self.dockAreaCycler.next()
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

class LinePlot(QWidget):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.plot = GraphicsLayoutWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)


class PlotDockWidget(QDockWidget):
    showSettingsRequested = pyqtSignal('QDockWidget')

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
            widget = QWidget()
            index = self.tabWidget.addTab(widget, title)
            self.dockToSettings[dockWidget] = widget
        else:
            widget = self.dockToSettings[dockWidget]
            index = self.tabWidget.indexOf(widget)
        self.tabWidget.setCurrentIndex(index)


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

