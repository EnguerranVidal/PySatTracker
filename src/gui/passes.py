from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import *


class VisiblePassesWidget(QMainWindow):
    passesRequest = pyqtSignal(list)

    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.viewWidget = VisiblePassesViewWidget(self)
        self.setCentralWidget(self.viewWidget)
        self.settingsDockWidget = VisiblePassesSettingsWidget(self)
        self.settingsDockWidget.passesRequest.connect(self._requestPasses)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.settingsDockWidget)

    def _requestPasses(self, settings: dict):
        self.passesRequest.emit(settings)



class VisiblePassesSettingsWidget(QDockWidget):
    passesRequest = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__("Pass Request Settings", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea)

class VisiblePassesViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)