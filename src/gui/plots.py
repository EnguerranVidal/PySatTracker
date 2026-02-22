from typing import Optional
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *

from gui.objects import AreaCycler


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
        plotWidget = LinePlot(self, self.currentDir)
        dockWidget = PlotDockWidget(self, 'Line Plot', plotWidget)
        dockWidget.showSettingsRequested.connect(self.handleShowSettings)
        area = self.dockAreaCycler.next()
        currentTabIndex = self.tabWidget.currentIndex()
        if currentTabIndex == -1:
            self.addNewTab()
            currentTabIndex = 0
        self.tabWidget.widget(currentTabIndex).addDockWidget(area, dockWidget)

    def handleShowSettings(self, dockWidget):
        self.settingsDockWidget.show()
        self.settingsDockWidget.raise_()
        self.settingsDockWidget.activateWindow()

class LinePlot(QWidget):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.plot = GraphicsLayoutWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)


class PlotDockWidget(QDockWidget):
    showSettingsRequested = pyqtSignal('QDockWidget')

    def __init__(self, parent=None, title=None, widget: Optional[LinePlot] = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.plotWidget = widget
        self.setWidget(self.plotWidget)
        self.setWindowTitle(title)

        self.settingsButton = QPushButton("Settings", self.plotWidget)
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
        x, y = self.plotWidget.width() - buttonSize.width() - 10, 10
        self.settingsButton.setGeometry(x, y, buttonSize.width(), buttonSize.height())

    def showSettingsDialog(self):
        QMessageBox.information(self, "Settings", "This is a placeholder settings dialog.")


class PlotSettingsDockWidget(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Settings")
        self.tabWidget = QTabWidget(self)
        self.setWidget(self.tabWidget)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
