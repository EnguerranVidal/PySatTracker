import os
from datetime import datetime, timedelta, timezone

from PyQt5.QtCore import pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QPen, QPixmap, QIcon
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class LoadingScreen(QSplashScreen):
    def __init__(self, pixmapPath='', duration=2000):
        pixmap = QPixmap(pixmapPath) if pixmapPath else QPixmap(400, 300)
        if not pixmapPath:
            pixmap.fill(Qt.black)
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.statusLabel = QLabel('Starting…', self)
        self.statusLabel.setStyleSheet('color: white;')
        self.statusLabel.setGeometry(20, pixmap.height() - 90, pixmap.width() - 40, 25)
        self.progress = QProgressBar(self)
        self.progress.setGeometry(20, pixmap.height() - 60, pixmap.width() - 40, 20)
        self.progress.setValue(0)

        self.mainWindow = None

    def setProgress(self, value):
        self.progress.setValue(value)

    def setStatus(self, text):
        self.statusLabel.setText(text)

    def launchMainWindow(self, mainWindow):
        self.mainWindow = mainWindow
        self.finish(mainWindow)
        mainWindow.show()


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