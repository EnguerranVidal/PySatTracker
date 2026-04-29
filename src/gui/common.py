import os
from datetime import datetime, timedelta, timezone

import numpy as np
from PyQt5.QtCore import pyqtSignal, QSize, QDateTime, QEvent, QPointF, QPropertyAnimation, QEasingCurve, pyqtSlot, QObject, QTimer
from PyQt5.QtGui import QPainter, QPen, QPixmap, QIcon, QPolygonF
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

from core.engine.orbitalEngine import OrbitalMechanicsEngine
from core.objects import ActiveObjectsModel


class LoadingScreen(QSplashScreen):
    def __init__(self, pixmapPath='', progressAnimDuration=250):
        pixmap = QPixmap(pixmapPath) if pixmapPath else QPixmap(400, 300)
        if not pixmapPath:
            pixmap.fill(Qt.black)
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.statusLabel = QLabel('Starting…', self)
        self.statusLabel.setStyleSheet('color: white; font-size: 12px;')
        self.statusLabel.setGeometry(20, pixmap.height() - 90, pixmap.width() - 40, 25)
        self.progress = QProgressBar(self)
        self.progress.setGeometry(20, pixmap.height() - 60, pixmap.width() - 40, 20)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progressAnimation = QPropertyAnimation(self.progress, b"value")
        self.progressAnimation.setDuration(progressAnimDuration)
        self.progressAnimation.setEasingCurve(QEasingCurve.OutCubic)
        self.opacityEffect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacityEffect)
        self.fadeAnimation = QPropertyAnimation(self.opacityEffect, b"opacity")
        self.fadeAnimation.setDuration(400)
        self.fadeAnimation.setEasingCurve(QEasingCurve.InOutQuad)
        self.mainWindow = None

    def showEvent(self, event):
        super().showEvent(event)
        self.fadeAnimation.stop()
        self.fadeAnimation.setStartValue(0)
        self.fadeAnimation.setEndValue(1)
        self.fadeAnimation.start()

    def setProgress(self, value):
        if abs(self.progress.value() - value) < 1:
            return
        self.progressAnimation.stop()
        self.progressAnimation.setStartValue(self.progress.value())
        self.progressAnimation.setEndValue(value)
        self.progressAnimation.start()

    def setStatus(self, text):
        self.statusLabel.setText(text)
        self.statusLabel.repaint()

    def launchMainWindow(self, mainWindow):
        self.progress.setValue(100)
        self.mainWindow = mainWindow
        self.setUpdatesEnabled(False)
        def finish():
            self.finish(mainWindow)
            mainWindow.show()
            self.setUpdatesEnabled(True)
        self.fadeAnimation.stop()
        self.fadeAnimation.setStartValue(1)
        self.fadeAnimation.setEndValue(0)
        self.fadeAnimation.finished.connect(finish)
        self.fadeAnimation.start()

    def setToMaximumProgress(self):
        self.progress.setValue(100)


class TimelineWidget(QWidget):
    playRequested = pyqtSignal()
    pauseRequested = pyqtSignal()
    toggleRequested = pyqtSignal()
    speedRequested = pyqtSignal(float)
    timeFormatChanged = pyqtSignal(int)
    timeRequested = pyqtSignal(datetime)
    resumeRequested = pyqtSignal()

    def __init__(self, parent = None, currentDir:str = None):
        super().__init__(parent)
        self.referenceTime = datetime.utcnow()
        self.ignoreSlider = False
        self.isRunning = False
        self.allowedSpeeds = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
        self.speedIndex = self.allowedSpeeds.index(1)
        self.displayMode = 0

        # MAIN WIDGETS
        self.iconPath = os.path.join(currentDir, 'src/assets/icons')
        self.timeButton = QPushButton("UTC ---------- --:--:--.---")
        self.timeButton.setFlat(True)
        self.timeButton.setMinimumWidth(160)
        self.timeButton.installEventFilter(self)
        self.timeButton.setToolTip("Left click: set simulation time\nRight click: change time display mode")
        self.slowDownButton = SquareIconButton(os.path.join(self.iconPath, 'slow-down.png'))
        self.playPauseButton = SquareIconButton(os.path.join(self.iconPath, 'pause.png'))
        self.fastForwardButton = SquareIconButton(os.path.join(self.iconPath, 'fast-forward.png'))
        self.resumeButton = SquareIconButton(os.path.join(self.iconPath, 'resume.png'))
        self.speedButton = QPushButton("x1")
        self.speedButton.setMinimumWidth(40)
        self.timeSlider = GraduatedTimeSlider()

        # LAYOUT
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.timeButton)
        layout.addWidget(self.slowDownButton)
        layout.addWidget(self.playPauseButton)
        layout.addWidget(self.fastForwardButton)
        layout.addWidget(self.resumeButton)
        layout.addWidget(self.speedButton)
        layout.addWidget(self.timeSlider, stretch=1)

        # CONNECTIONS
        self.timeButton.clicked.connect(self._openTimeDialog)
        self.slowDownButton.clicked.connect(self._slow)
        self.fastForwardButton.clicked.connect(self._fast)
        self.playPauseButton.clicked.connect(self.toggleRequested)
        self.resumeButton.clicked.connect(self._resume)
        self.speedButton.clicked.connect(self._resetSpeed)
        self.timeSlider.slider.valueChanged.connect(self._scrubSlider)
        self.timeSlider.slider.sliderPressed.connect(self._beginScrubSlider)
        self.timeSlider.slider.sliderReleased.connect(self._endScrubSlider)

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

    def _resetSpeed(self):
        self.speedIndex = self.allowedSpeeds.index(1)
        self.speedRequested.emit(self.allowedSpeeds[self.speedIndex])
        self.setSpeed(self.allowedSpeeds[self.speedIndex])

    def _resume(self):
        self.resumeRequested.emit()
        if not self.isRunning:
            self.playRequested.emit()

    def _beginScrubSlider(self):
        if self.isRunning:
            self.pauseRequested.emit()

    def _scrubSlider(self, value):
        if self.ignoreSlider:
            return
        self.timeRequested.emit(self.referenceTime + timedelta(seconds=value))

    def _endScrubSlider(self):
        if self.isRunning:
            self.playRequested.emit()

    def _openTimeDialog(self):
        current = self.referenceTime + timedelta(seconds=self.timeSlider.slider.value())
        dialog = SetTimeDialog(QDateTime(current), parent=self)
        if dialog.exec_() == QDialog.Accepted:
            newTime = dialog.getDatetime().toPyDateTime()
            self.timeRequested.emit(newTime)

    def _cycleDisplayMode(self):
        self.displayMode = (self.displayMode + 1) % 3
        self.timeFormatChanged.emit(self.displayMode)

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
            localDateTime = simTime.replace(tzinfo=timezone.utc).astimezone()
            text = localDateTime.strftime("LOC %Y-%m-%d %H:%M:%S.%f")[:-4]
        else:
            timeDifference = int((simTime - realNow).total_seconds())
            sign = "+" if timeDifference >= 0 else "-"
            remaining = abs(timeDifference)
            years = int(remaining // (365 * 86400))
            remaining %= (365 * 86400)
            months = int(remaining // (30 * 86400))
            remaining %= (30 * 86400)
            days = int(remaining // 86400)
            remaining %= 86400
            hours = int(remaining // 3600)
            remaining %= 3600
            minutes = int(remaining // 60)
            remaining %= 60
            seconds = int(remaining)
            fraction = int((remaining - seconds) * 100)
            text = f"Δ  {sign} {years:04}-{months:02}-{days:02}-{hours:02}-{minutes:02}-{seconds:02}.{fraction:02}"
        self.timeButton.setText(text)
        if not self.timeSlider.slider.isSliderDown():
            self.ignoreSlider = True
            self.timeSlider.slider.setValue(delta)
            self.ignoreSlider = False

    def setRunning(self, running: bool):
        self.isRunning = running
        self.playPauseButton.setIconPath(os.path.join(self.iconPath, 'pause.png') if running else os.path.join(self.iconPath, 'play.png'))

    def setSpeed(self, speed: float):
        self.speedButton.setText(f"x{speed:g}")
        if speed in self.allowedSpeeds:
            self.speedIndex = self.allowedSpeeds.index(speed)

    def setNow(self, now: datetime):
        self.referenceTime = now

    def eventFilter(self, obj, event):
        if obj == self.timeButton and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                self._cycleDisplayMode()
                return True
        return super().eventFilter(obj, event)


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
        xSliderZeroValue = rectangle.left() + (0 - minimumValue) / span * rectangle.width()
        arrowPoints = QPolygonF([QPointF(xSliderZeroValue - 4, rectangle.top() - 10), QPointF(xSliderZeroValue + 4, rectangle.top() - 10), QPointF(xSliderZeroValue, rectangle.top() - 2)])
        painter.setBrush(Qt.gray)
        painter.drawPolygon(arrowPoints)

    def setRangeHours(self, hours: int):
        self.slider.setRange(-3600 * hours, 3600 * hours)
        self.update()


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


class SimulationClock(QObject):
    timeChanged = pyqtSignal(datetime)
    speedChanged = pyqtSignal(float)
    stateChanged = pyqtSignal(bool)

    def __init__(self, startDateTime=None, parent=None):
        super().__init__(parent)

        self.currentDateTime = startDateTime or datetime.utcnow()
        self.speed = 1.0
        self.isRunning = False
        self._lastRealDateTime = datetime.utcnow()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

    def _tick(self):
        now = datetime.utcnow()
        realDelta = (now - self._lastRealDateTime).total_seconds()
        self._lastRealDateTime = now
        if not self.isRunning:
            return
        simDelta = timedelta(seconds=realDelta * self.speed)
        self.currentDateTime += simDelta
        self.timeChanged.emit(self.currentDateTime)

    def play(self):
        self._lastRealDateTime = datetime.utcnow()
        self.isRunning = True
        self.stateChanged.emit(True)

    def pause(self):
        self.isRunning = False
        self.stateChanged.emit(False)

    def toggle(self):
        self.play() if not self.isRunning else self.pause()

    def setSpeed(self, speed: float):
        self.speed = max(0.0, speed)
        self.speedChanged.emit(self.speed)

    def getDateTime(self):
        return self.currentDateTime

    def setDateTime(self, newDateTime: datetime):
        self.currentDateTime = newDateTime
        self._lastRealDateTime = datetime.utcnow()
        self.timeChanged.emit(self.currentDateTime)


class OrbitWorker(QObject):
    positionsReady = pyqtSignal(dict)

    def __init__(self, tleDatabase):
        super().__init__()
        self.engine = OrbitalMechanicsEngine()
        self.tleDatabase = tleDatabase
        self.activeObjects: ActiveObjectsModel | None = None
        self._running = True

    def stop(self):
        self._running = False

    def buildTimeArray(self, simulationTime: datetime, orbitalPeriod, configuration, resolution):
        timeScales = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400, 'orbital periods': orbitalPeriod}
        beforeDuration, beforeDurationUnit = configuration['BEFORE'], configuration['BEFORE_UNIT']
        afterDuration, afterDurationUnit = configuration['AFTER'], configuration['AFTER_UNIT']
        startDateTime = simulationTime - timedelta(seconds=beforeDuration * timeScales[beforeDurationUnit])
        endDateTime = simulationTime + timedelta(seconds=afterDuration * timeScales[afterDurationUnit])
        return self.engine.datetimeToJulianDateArray(startDateTime, endDateTime, resolution)

    def map2dCalculations(self, simulationTime, configuration):
        if not self.activeObjects:
            return {}
        noradIndices = self.activeObjects.allNoradIndices()
        map2dResults = {'OBJECTS': {noradIndex: {'NAME': self.tleDatabase.getObjectName(noradIndex)} for noradIndex in noradIndices}}
        julianDate, fraction = self.engine.datetimeToJulianDate(simulationTime)
        simFullJulianDate = julianDate + fraction
        for noradIndex in noradIndices:
            satObject = self.tleDatabase.getSatrec(noradIndex)
            nowState = self.engine.satelliteState(satObject, simFullJulianDate)
            nowOrbitalPeriod = self.engine.orbitalPeriodFromState(nowState['rECI'], nowState['vECI'])
            julianDates, fractions = self.buildTimeArray(simulationTime, nowOrbitalPeriod, configuration['OBJECTS'][str(noradIndex)], resolution=max(500, int(nowOrbitalPeriod / 2)) + 1)
            fullJulianDates = julianDates + fractions
            states = self.engine.satelliteState(satObject, fullJulianDates)
            visibilityLongitudes, visibilityLatitudes = self.engine.satellite2dVisibilityFootPrint(nowState['longitude'], nowState['latitude'], nowState['altitude'], nbPoints=501)
            map2dResults['OBJECTS'][noradIndex]['POSITION'] = {'LONGITUDE': np.rad2deg(nowState['longitude']), 'LATITUDE': np.rad2deg(nowState['latitude'])}
            map2dResults['OBJECTS'][noradIndex]['GROUND_TRACK'] = {'LONGITUDE': np.rad2deg((states['longitude'] + np.pi) % (2 * np.pi) - np.pi), 'LATITUDE': np.rad2deg(states['latitude'])}
            map2dResults['OBJECTS'][noradIndex]['VISIBILITY'] = {'LONGITUDE': np.rad2deg(visibilityLongitudes), 'LATITUDE': np.rad2deg(visibilityLatitudes)}
        sunLongitude, sunLatitude, sunDistance = self.engine.subSolarPoint(simFullJulianDate, radians=False)
        terminatorLongitudes, terminatorLatitudes = self.engine.terminatorCurve(simFullJulianDate, nbPoints=501, radians=False)
        vernalLongitude, vernalLatitude = self.engine.getVernalSubPoint(simFullJulianDate, radians=False)
        map2dResults['SUN'] = {'LONGITUDE': sunLongitude, 'LATITUDE': sunLatitude, 'DISTANCE': sunDistance}
        map2dResults['NIGHT'] = {'LONGITUDE': terminatorLongitudes, 'LATITUDE': terminatorLatitudes}
        map2dResults['VERNAL'] = {'LONGITUDE': vernalLongitude, 'LATITUDE': vernalLatitude}
        return map2dResults

    def view3dCalculations(self, simulationTime, configuration):
        if not self.activeObjects:
            return {}
        noradIndices = self.activeObjects.allNoradIndices()
        view3dResults = {'OBJECTS': {noradIndex: {'NAME': self.tleDatabase.getObjectName(noradIndex)} for noradIndex in noradIndices}}
        julianDate, fraction = self.engine.datetimeToJulianDate(simulationTime)
        simFullJulianDate = julianDate + fraction
        for noradIndex in noradIndices:
            satObject = self.tleDatabase.getSatrec(noradIndex)
            nowState = self.engine.satelliteState(satObject, simFullJulianDate)
            nowOrbitalPeriod = self.engine.orbitalPeriodFromState(nowState['rECI'], nowState['vECI'])
            julianDates, fractions = self.buildTimeArray(simulationTime, nowOrbitalPeriod, configuration['OBJECTS'][str(noradIndex)], resolution= max(500, int(nowOrbitalPeriod / 2)) + 1)
            fullJulianDates = julianDates + fractions
            states = self.engine.satelliteState(satObject, fullJulianDates)
            groundTrackEci = self.engine.satellite3dGroundTrack(states['rECI'], fullJulianDates)
            visibilityEci = self.engine.satellite3dVisibilityFootPrint(nowState['longitude'], nowState['latitude'], nowState['altitude'], simFullJulianDate, nbPoints=501)
            view3dResults['OBJECTS'][noradIndex]['POSITION'] = {'R_ECI': nowState['rECI'], 'V_ECI': nowState['vECI'], 'ALTITUDE': nowState['altitude'], 'LATITUDE': np.rad2deg(nowState['latitude']), 'LONGITUDE': np.rad2deg(nowState['longitude'])}
            view3dResults['OBJECTS'][noradIndex]['ORBIT_PATH'] = states['rECI']
            view3dResults['OBJECTS'][noradIndex]['GROUND_TRACK'] = groundTrackEci
            view3dResults['OBJECTS'][noradIndex]['VISIBILITY'] = visibilityEci
        view3dResults['GMST'] = self.engine.greenwichMeridianSiderealTime(simFullJulianDate)
        view3dResults['SUN_DIRECTION_ECI'] = self.engine.solarDirectionEci(simFullJulianDate)
        view3dResults['SUN_DIRECTION_ECEF'] = self.engine.eciToEcef(view3dResults['SUN_DIRECTION_ECI'], simFullJulianDate)
        return view3dResults

    @pyqtSlot(object, dict)
    def compute(self, simulationTime: datetime, configuration):
        if not self._running or self.tleDatabase is None or self.activeObjects is None:
            return
        results = {'2D_MAP': self.map2dCalculations(simulationTime=simulationTime, configuration=configuration), '3D_VIEW': self.view3dCalculations(simulationTime=simulationTime, configuration=configuration)}
        self.positionsReady.emit(results)

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects


class AreaCycler:
    def __init__(self):
        self.cycle = [Qt.LeftDockWidgetArea, Qt.RightDockWidgetArea, Qt.TopDockWidgetArea, Qt.BottomDockWidgetArea]
        self.step = 0

    def next(self, step=None):
        if step is not None:
            self.step = step
        value = self.cycle[self.step]
        self.step += 1
        if self.step == 4:
            self.step = 0
        return value

    def get(self, step):
        assert step < 4
        return self.cycle[step]


class SetTimeDialog(QDialog):
    def __init__(self, initialDatetime=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Date and Time")
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.dateTimeEdit = QDateTimeEdit(self)
        self.dateTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.dateTimeEdit.setCalendarPopup(True)
        self.okButton = QPushButton("OK")
        self.okButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.cancelButton.clicked.connect(self.reject)
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(8, 8, 8, 8)
        mainLayout.setSpacing(6)
        mainLayout.addWidget(self.dateTimeEdit)
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(6)
        buttonLayout.addWidget(self.okButton)
        buttonLayout.addWidget(self.cancelButton)
        mainLayout.addLayout(buttonLayout)
        if initialDatetime is None:
            initialDatetime = QDateTime.currentDateTime()
        self.setDatetime(initialDatetime)
        self.adjustSize()
        self.setFixedWidth(300)

    def setDatetime(self, dt):
        self.dateTimeEdit.setDateTime(dt)

    def getDatetime(self):
        return self.dateTimeEdit.dateTime()
