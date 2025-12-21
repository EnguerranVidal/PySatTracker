from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class SimulationClock(QObject):
    timeChanged = pyqtSignal(datetime)
    speedChanged = pyqtSignal(float)
    stateChanged = pyqtSignal(bool)

    def __init__(self, startTime=None, parent=None):
        super().__init__(parent)
        self.currentTime = startTime or datetime.utcnow()
        self.speed = 1.0
        self.running = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)

    def _tick(self):
        if not self.running:
            return
        delta = timedelta(seconds=self.speed * 0.033)
        self.currentTime += delta
        self.timeChanged.emit(self.currentTime)

    def play(self):
        self.running = True
        self.stateChanged.emit(True)

    def pause(self):
        self.running = False
        self.stateChanged.emit(False)

    def toggle(self):
        self.play() if not self.running else self.pause()

    def setSpeed(self, speed):
        self.speed = speed
        self.speedChanged.emit(speed)

    def setTime(self, newTime):
        self.currentTime = newTime
        self.timeChanged.emit(self.currentTime)


class AddObjectDialog(QDialog):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Satellites")
        self.resize(400, 500)
        self.database = database
        self.selectedNoradIndices = []

        # LIST & SEARCH BAR
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search satellites…")
        self.searchBar.textChanged.connect(self.filterList)
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QListWidget.MultiSelection)

        # BUTTON BAR
        buttonBar = QHBoxLayout()
        cancelButton = QPushButton("Cancel")
        addButton = QPushButton("Add")
        cancelButton.clicked.connect(self.reject)
        addButton.clicked.connect(self.acceptSelection)
        buttonBar.addStretch()
        buttonBar.addWidget(cancelButton)
        buttonBar.addWidget(addButton)

        layout = QVBoxLayout(self)
        layout.addWidget(self.searchBar)
        layout.addWidget(self.listWidget)
        layout.addLayout(buttonBar)
        self._populate()

    def _populate(self):
        self.listWidget.clear()
        rows = self.database.dataFrame.sort_values("OBJECT_NAME")
        for _, row in rows.iterrows():
            item = QListWidgetItem(row["OBJECT_NAME"])
            item.setData(Qt.UserRole, row["NORAD_CAT_ID"])
            self.listWidget.addItem(item)

    def filterList(self, text):
        text = text.lower()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            item.setHidden(text not in item.text().lower())

    def acceptSelection(self):
        self.selectedNoradIndices = [item.data(Qt.UserRole) for item in self.listWidget.selectedItems()]
        self.accept()
