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
        self.findVisiblePassesButton = QPushButton("Find Visible Passes")
        # LOCATION GROUP BOX
        self.locationGroupBox = QGroupBox("Location")
        self.setLocationButton = QPushButton("Set Location")
        self.locationLongitudeLineEdit = QLineEdit()
        self.locationLatitudeLineEdit = QLineEdit()
        locationLayout = QHBoxLayout()
        locationLayout.addWidget(self.setLocationButton)
        locationLayout.addWidget(self.locationLongitudeLineEdit)
        locationLayout.addWidget(self.locationLatitudeLineEdit)
        self.locationGroupBox.setLayout(locationLayout)
        # TIME SPAN GROUP BOX
        self.timeSpanGroupBox = QGroupBox("Time Span")
        self.timeSpanButtonGroup = QButtonGroup()
        self.tonightButton = QRadioButton("Tonight")
        self.oneDayButton = QRadioButton("Next 24 hours")
        self.twoDayButton = QRadioButton("Next 48 hours")
        self.timeSpanButtonGroup.addButton(self.tonightButton)
        self.timeSpanButtonGroup.addButton(self.oneDayButton)
        self.timeSpanButtonGroup.addButton(self.twoDayButton)
        timeLayout = QHBoxLayout()
        timeLayout.addWidget(self.tonightButton)
        timeLayout.addWidget(self.oneDayButton)
        timeLayout.addWidget(self.twoDayButton)
        self.timeSpanGroupBox.setLayout(timeLayout)
        # MAIN LAYOUT
        content = QWidget()
        mainLayout = QVBoxLayout(content)
        mainLayout.addWidget(self.locationGroupBox)
        mainLayout.addWidget(self.timeSpanGroupBox)
        mainLayout.addWidget(self.findVisiblePassesButton)
        mainLayout.addStretch()
        self.setWidget(content)


class VisiblePassesViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)