import time

import numpy as np
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

from src.core.orbitalEngine import OrbitalMechanicsEngine


class SimulationClock(QObject):
    timeChanged = pyqtSignal(datetime)
    speedChanged = pyqtSignal(float)
    stateChanged = pyqtSignal(bool)

    def __init__(self, startTime=None, parent=None):
        super().__init__(parent)

        self.currentTime = startTime or datetime.utcnow()
        self.speed = 1.0
        self.running = False
        self._lastRealTime = time.perf_counter()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def _tick(self):
        now = time.perf_counter()
        realDelta = now - self._lastRealTime
        self._lastRealTime = now
        if not self.running:
            return
        simDelta = timedelta(seconds=realDelta * self.speed)
        self.currentTime += simDelta
        self.timeChanged.emit(self.currentTime)

    def play(self):
        self._lastRealTime = time.perf_counter()
        self.running = True
        self.stateChanged.emit(True)

    def pause(self):
        self.running = False
        self.stateChanged.emit(False)

    def toggle(self):
        self.play() if not self.running else self.pause()

    def setSpeed(self, speed: float):
        self.speed = max(0.0, speed)
        self.speedChanged.emit(self.speed)

    def setTime(self, newTime: datetime):
        self.currentTime = newTime
        self._lastRealTime = time.perf_counter()
        self.timeChanged.emit(self.currentTime)


class OrbitWorker(QObject):
    positionsReady = pyqtSignal(dict)

    def __init__(self, database):
        super().__init__()
        self.engine = OrbitalMechanicsEngine()
        self.database = database
        self.visibleNoradIndices = []
        self._running = True

    def stop(self):
        self._running = False

    def compute(self, simulationTime: datetime):
        if not self._running or self.database is None:
            return
        results = {}
        # FLAT 2D MAP CALCULATIONS
        mapResults = {noradIndex: {}  for noradIndex in self.visibleNoradIndices}
        for noradIndex in self.visibleNoradIndices:
            try:
                # MAP CALCULATIONS
                mapResults = {}
                satellite = self.database.getSatrec(noradIndex)
                state = self.engine.satelliteState(satellite, simulationTime)
                groundLongitudes, groundLatitudes, groundElevations = self.engine.satelliteGroundTrack(satellite, simulationTime)
                visibilityLongitudes, visibilityLatitudes = self.engine.satelliteVisibilityFootPrint(state, nbPoints=360)
                longitude, latitude = np.rad2deg(state['longitude']), np.rad2deg(state['latitude'])
                groundLongitudes, groundLatitudes = np.rad2deg(groundLongitudes), np.rad2deg(groundLatitudes)
                visibilityLongitudes, visibilityLatitudes = np.rad2deg(visibilityLongitudes), np.rad2deg(visibilityLatitudes)
                mapResults['POSITION'] =  {'LONGITUDE': longitude, 'LATITUDE': latitude}
                mapResults['GROUND_TRACK'] = {'LONGITUDE': groundLongitudes, 'LATITUDE': groundLatitudes}
                mapResults['VISIBILITY'] = {'LONGITUDE': visibilityLongitudes, 'LATITUDE': visibilityLatitudes}
                results[noradIndex] = mapResults
            except Exception as e:
                print(f"Worker error {noradIndex}: {e}")
        # SUN POSITION AND TERMINATOR CALCULATION
        sunLongitude, sunLatitude, sunDistance = self.engine.subSolarPoint(simulationTime, radians=False)
        terminatorLongitudes, terminatorLatitudes = self.engine.terminatorCurve(simulationTime, nbPoints=361, radians=False)
        mapResults['SUN'] = {'LONGITUDE': sunLongitude, 'LATITUDE': sunLatitude, 'DISTANCE': sunDistance}
        mapResults['NIGHT'] = {'LONGITUDE': terminatorLongitudes, 'LATITUDE': terminatorLatitudes}
        results['MAP'] = mapResults
        # RESULTS EMISSION
        self.positionsReady.emit(results)


class AddObjectDialog(QDialog):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Satellites')
        self.resize(400, 500)
        self.database = database
        self.selectedNoradIndices = []

        # LIST & SEARCH BAR
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText('Search satellites…')
        self.searchBar.textChanged.connect(self.filterList)
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QListWidget.MultiSelection)

        # BUTTON BAR
        buttonBar = QHBoxLayout()
        addButton = QPushButton('Add')
        cancelButton = QPushButton('Cancel')
        addButton.clicked.connect(self.acceptSelection)
        cancelButton.clicked.connect(self.reject)
        buttonBar.addStretch()
        buttonBar.addWidget(addButton)
        buttonBar.addWidget(cancelButton)
        # DIALOG LAYOUT
        layout = QVBoxLayout(self)
        layout.addWidget(self.searchBar)
        layout.addWidget(self.listWidget)
        layout.addLayout(buttonBar)
        self._populate()

    def _populate(self):
        self.listWidget.clear()
        rows = self.database.dataFrame.sort_values('OBJECT_NAME')
        for _, row in rows.iterrows():
            name, noradIndex = row['OBJECT_NAME'], row['NORAD_CAT_ID']
            text = f'{name} — {noradIndex}'
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, noradIndex)
            item.setData(Qt.UserRole + 1, f'{name.lower()} {noradIndex}')
            self.listWidget.addItem(item)

    def filterList(self, text):
        text = text.lower().strip()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            item.setHidden(text not in item.text().lower())

    def acceptSelection(self):
        self.selectedNoradIndices = [item.data(Qt.UserRole) for item in self.listWidget.selectedItems()]
        self.accept()
