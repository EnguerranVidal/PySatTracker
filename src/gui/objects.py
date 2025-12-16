from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from datetime import datetime, timedelta


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
