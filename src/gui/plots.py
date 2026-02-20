from typing import Optional
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt
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
        area = self.dockAreaCycler.next()
        currentTabIndex = self.tabWidget.currentIndex()
        if currentTabIndex == -1:
            self.addNewTab()
            currentTabIndex = 0
        self.tabWidget.widget(currentTabIndex).addDockWidget(area, dockWidget)


class LinePlot(QWidget):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir


class PlotDockWidget(QDockWidget):
    def __init__(self, parent=None, title=None, widget: Optional[LinePlot] = None):
        super().__init__(parent)
        self.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.plotWidget = GraphicsLayoutWidget()
        self.setWidget(self.plotWidget)
        self.setWindowTitle(title)