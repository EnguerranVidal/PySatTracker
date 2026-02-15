import os
from typing import Optional

import numpy as np
import imageio
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, pyqtSignal, QSignalBlocker
from PyQt5.QtWidgets import *


class PlotViewTabWidget(QMainWindow):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.dockSpaces = [Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea, Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea]
        self.tabWidget = QTabWidget()
        self.tabWidget.setMovable(True)
        self.setCentralWidget(self.tabWidget)

    def closeCurrentTab(self):
        currentIndex = self.tabWidget.currentIndex()
        if currentIndex != -1:
            self.tabWidget.removeTab(currentIndex)

    def closeAllTabs(self):
        self.tabWidget.clear()

    def addNewTab(self, title=None):
        if title is None:
            title = f'Tab {self.tabWidget.count() + 1}'
        self.tabWidget.addTab(QMainWindow(), title)

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

