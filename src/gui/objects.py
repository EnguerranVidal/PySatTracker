import os
import time
from datetime import datetime, timedelta, timezone
import numpy as np
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPainter, QPen
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QRect

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
        self._lastRealTime = datetime.utcnow()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def _tick(self):
        now = datetime.utcnow()
        realDelta = (now - self._lastRealTime).total_seconds()
        self._lastRealTime = now
        if not self.running:
            return
        simDelta = timedelta(seconds=realDelta * self.speed)
        self.currentTime += simDelta
        self.timeChanged.emit(self.currentTime)

    def play(self):
        self._lastRealTime = datetime.utcnow()
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
        self._lastRealTime = datetime.utcnow()
        self.timeChanged.emit(self.currentTime)


class OrbitWorker(QObject):
    positionsReady = pyqtSignal(dict)

    def __init__(self, database):
        super().__init__()
        self.engine = OrbitalMechanicsEngine()
        self.database = database
        self.noradIndices = []
        self._running = True

    def stop(self):
        self._running = False

    def compute(self, simulationTime: datetime):
        if not self._running or self.database is None:
            return
        results = {}
        # FLAT 2D MAP CALCULATIONS
        map2dResults = {'OBJECTS' : {noradIndex: {'NAME': self.database.getObjectName(noradIndex)} for noradIndex in self.noradIndices}}
        for noradIndex in self.noradIndices:
            try:
                # MAP CALCULATIONS
                satellite = self.database.getSatrec(noradIndex)
                state = self.engine.satelliteState(satellite, simulationTime)
                groundLongitudes, groundLatitudes, groundElevations = self.engine.satelliteGroundTrack(satellite, simulationTime)
                visibilityLongitudes, visibilityLatitudes = self.engine.satelliteVisibilityFootPrint(state, nbPoints=361)
                longitude, latitude = np.rad2deg(state['longitude']), np.rad2deg(state['latitude'])
                groundLongitudes, groundLatitudes = np.rad2deg(groundLongitudes), np.rad2deg(groundLatitudes)
                visibilityLongitudes, visibilityLatitudes = np.rad2deg(visibilityLongitudes), np.rad2deg(visibilityLatitudes)
                map2dResults['OBJECTS'][noradIndex]['POSITION'] =  {'LONGITUDE': longitude, 'LATITUDE': latitude}
                map2dResults['OBJECTS'][noradIndex]['GROUND_TRACK'] = {'LONGITUDE': groundLongitudes, 'LATITUDE': groundLatitudes}
                map2dResults['OBJECTS'][noradIndex]['VISIBILITY'] = {'LONGITUDE': visibilityLongitudes, 'LATITUDE': visibilityLatitudes}
            except Exception as e:
                print(f"Worker error {noradIndex}: {e}")
        # SUN POSITION AND TERMINATOR CALCULATION
        sunLongitude, sunLatitude, sunDistance = self.engine.subSolarPoint(simulationTime, radians=False)
        terminatorLongitudes, terminatorLatitudes = self.engine.terminatorCurve(simulationTime, nbPoints=361, radians=False)
        vernalLongitude, vernalLatitude = self.engine.getVernalSubPoint(simulationTime, radians=False)
        map2dResults['SUN'] = {'LONGITUDE': sunLongitude, 'LATITUDE': sunLatitude, 'DISTANCE': sunDistance}
        map2dResults['NIGHT'] = {'LONGITUDE': terminatorLongitudes, 'LATITUDE': terminatorLatitudes}
        map2dResults['VERNAL'] = {'LONGITUDE': vernalLongitude, 'LATITUDE': vernalLatitude}
        results['2D_MAP'] = map2dResults
        # 3D EARTH VIEW CALCULATIONS
        earth3dResults = {'OBJECTS': {noradIndex: {'NAME': self.database.getObjectName(noradIndex)} for noradIndex in self.noradIndices}}
        for noradIndex in self.noradIndices:
            try:
                satellite = self.database.getSatrec(noradIndex)
                state = self.engine.satelliteState(satellite, simulationTime)
                # INSTANT POSITION
                rEci, vEci = state['rECI'], state['vECI']
                earth3dResults['OBJECTS'][noradIndex]['POSITION'] = {'R_ECI': rEci, 'V_ECI': vEci, 'ALTITUDE': state['altitude'], 'LATITUDE': np.rad2deg(state['latitude']), 'LONGITUDE': np.rad2deg(state['longitude'])}
                # ORBIT PATH
                positionsEci = self.engine.satelliteOrbitPath(satellite, simulationTime, nbPoints=361, nbPast=0.5, nbFuture=0.5)
                earth3dResults['OBJECTS'][noradIndex]['ORBIT_PATH'] = positionsEci
            except Exception as e:
                print(f"Worker error {noradIndex}: {e}")
        # GMST FOR 3D VIEW
        earth3dResults['GMST'] = self.engine.greenwichMeridianSiderealTime(simulationTime)
        earth3dResults['SUN_DIRECTION_ECI'] = self.engine.solarDirectionEci(simulationTime)
        earth3dResults['SUN_DIRECTION_ECEF'] =  self.engine.eciToEcef(earth3dResults['SUN_DIRECTION_ECI'], simulationTime)
        results['3D_VIEW'] = earth3dResults
        # RESULTS EMISSION
        self.positionsReady.emit(results)


class AddObjectDialog(QDialog):
    def __init__(self, database, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Add Objects')
        self.resize(400, 500)
        self.database = database
        self.selectedNoradIndices = []

        # LIST & SEARCH BAR
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText('Search Objects…')
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


class SquareIconButton(QPushButton):
    def __init__(self, iconPath: str, parent=None, size=24, flat=False):
        super(SquareIconButton, self).__init__(parent)
        self.iconPath = iconPath
        self.setIcon(QIcon(self.iconPath))
        self.setIconSize(QSize(size, size))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if flat:
            styleSheet = 'border: none; text-align: center;'
            self.setFlat(True)
        else:
            styleSheet = 'text-align: center;'
        self.setStyleSheet(styleSheet)
        self.setAutoFillBackground(False)

    def setIconPath(self, iconPath: str):
        self.iconPath = iconPath
        self.setIcon(QIcon(iconPath))

    def setIconObject(self, icon: QIcon):
        self.iconPath = None
        self.setIcon(icon)

    def setIconSize(self, size):
        super().setIconSize(size)
        self.setFixedSize(size)

    def sizeHint(self):
        return self.iconSize()


class TimelineWidget(QWidget):
    playRequested = pyqtSignal()
    pauseRequested = pyqtSignal()
    toggleRequested = pyqtSignal()
    speedRequested = pyqtSignal(float)
    timeRequested = pyqtSignal(datetime)
    jumpToNowRequested = pyqtSignal()

    def __init__(self, parent = None, currentDir:str = None):
        super().__init__(parent)
        self.referenceTime = datetime.utcnow()
        self.ignoreSlider = False
        self.isRunning = False
        self.allowedSpeeds = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500]
        self.speedIndex = self.allowedSpeeds.index(1)
        self.displayMode = 0

        # MAIN WIDGETS
        self.iconPath = os.path.join(currentDir, 'src/assets/icons')
        self.timeButton = QPushButton("UTC ---------- --:--:--.---")
        self.timeButton.setFlat(True)
        self.timeButton.setMinimumWidth(160)
        self.slowDownButton = SquareIconButton(os.path.join(self.iconPath, 'slow-down.png'))
        self.playPauseButton = SquareIconButton(os.path.join(self.iconPath, 'pause.png'))
        self.fastForwardButton = SquareIconButton(os.path.join(self.iconPath, 'fast-forward.png'))
        self.jumpToNowButton = SquareIconButton(os.path.join(self.iconPath, 'resume.png'))
        self.speedLabel = QLabel("x1")
        self.speedLabel.setMinimumWidth(40)
        self.timeSlider = GraduatedTimeSlider()

        # LAYOUT
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.timeButton)
        layout.addWidget(self.slowDownButton)
        layout.addWidget(self.playPauseButton)
        layout.addWidget(self.fastForwardButton)
        layout.addWidget(self.jumpToNowButton)
        layout.addWidget(self.speedLabel)
        layout.addWidget(self.timeSlider, stretch=1)

        # CONNECTIONS
        self.timeButton.clicked.connect(self._cycleDisplayMode)
        self.slowDownButton.clicked.connect(self._slow)
        self.fastForwardButton.clicked.connect(self._fast)
        self.playPauseButton.clicked.connect(self.toggleRequested)
        self.jumpToNowButton.clicked.connect(self.jumpToNowRequested)
        self.timeSlider.slider.valueChanged.connect(self._scrub)
        self.timeSlider.slider.sliderPressed.connect(self._beginScrub)
        self.timeSlider.slider.sliderReleased.connect(self._endScrub)

    def _slow(self):
        if self.speedIndex > 0:
            self.speedIndex -= 1
            self.speedRequested.emit(self.allowedSpeeds[self.speedIndex])
            self.setSpeed(self.allowedSpeeds[self.speedIndex])

    def _fast(self):
        if self.speedIndex < len(self.allowedSpeeds) - 1:
            self.speedIndex += 1
            self.speedRequested.emit(self.allowedSpeeds[self.speedIndex])
            self.setSpeed(self.allowedSpeeds[self.speedIndex])

    def _beginScrub(self):
        if self.isRunning:
            self.pauseRequested.emit()

    def _scrub(self, value):
        if self.ignoreSlider:
            return
        self.timeRequested.emit(self.referenceTime + timedelta(seconds=value))

    def _endScrub(self):
        if self.isRunning:
            self.playRequested.emit()

    def _cycleDisplayMode(self):
        self.displayMode = (self.displayMode + 1) % 3

    def setTime(self, simTime: datetime):
        realNow = datetime.utcnow()
        minimumValue, maximumValue = self.timeSlider.slider.minimum(), self.timeSlider.slider.maximum()
        tentativeDelta = (simTime - self.referenceTime).total_seconds()
        if self.allowedSpeeds[self.speedIndex] == 1 and self.isRunning and abs((simTime - realNow).total_seconds()) < 1:
            self.referenceTime = simTime
            delta = 0
        else:
            delta = max(min(round(tentativeDelta), maximumValue), minimumValue)
        if self.displayMode == 0:
            text = simTime.strftime("UTC %Y-%m-%d %H:%M:%S.%f")[:-4]
        elif self.displayMode == 1:
            local_time = simTime.replace(tzinfo=timezone.utc).astimezone()
            text = local_time.strftime("LOC %Y-%m-%d %H:%M:%S.%f")[:-4]
        else:
            timeDifference = int((simTime - realNow).total_seconds())
            sign = "+" if timeDifference >= 0 else "-"
            text = f"Δ {sign}{abs(timeDifference)}s"
        self.timeButton.setText(text)
        if not self.timeSlider.slider.isSliderDown():
            self.ignoreSlider = True
            self.timeSlider.slider.setValue(delta)
            self.ignoreSlider = False

    def setRunning(self, running: bool):
        self.isRunning = running
        self.playPauseButton.setIconPath(os.path.join(self.iconPath, 'pause.png') if running else os.path.join(self.iconPath, 'play.png'))

    def setSpeed(self, speed: float):
        self.speedLabel.setText(f"x{speed:g}")
        if speed in self.allowedSpeeds:
            self.speedIndex = self.allowedSpeeds.index(speed)

    def setNow(self, now: datetime):
        self.referenceTime = now

    def resetReferenceTime(self, t: datetime):
        self.referenceTime = t
        self.ignoreSlider = True
        self.timeSlider.slider.setValue(0)
        self.ignoreSlider = False


class GraduatedTimeSlider(QWidget):
    def __init__(self, parent=None, nbHours=2):
        super().__init__(parent)
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(-3600 * nbHours, 3600 * nbHours)
        self.majorStep, self.minorStep = 600, 60
        self.topMargin, self.bottomMargin = 14, 4

    def resizeEvent(self, event):
        self.slider.setGeometry(0, self.topMargin, self.width(), self.height() - self.topMargin - self.bottomMargin)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.gray))
        rectangle = self.slider.geometry()
        minimumValue, maximumValue = self.slider.minimum(), self.slider.maximum()
        span = maximumValue - minimumValue
        for value in range(minimumValue, maximumValue + 1, self.minorStep):
            x = rectangle.left() + (value - minimumValue) / span * rectangle.width()
            if value % self.majorStep == 0:
                painter.drawLine(int(x), rectangle.top() - 8, int(x), rectangle.top())
            else:
                painter.drawLine(int(x), rectangle.top() - 4, int(x), rectangle.top())

    def setRangeHours(self, hours: int):
        self.slider.setRange(-3600 * hours, 3600 * hours)
        self.update()
