from dataclasses import dataclass
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QObject, pyqtSignal, QRunnable

from src.core.database.tleDatabase import TLEDatabase
from src.core.engine.orbitalEngine import OrbitalMechanicsEngine


@dataclass
class VisiblePassesRequest:
    longitude: float
    latitude: float
    timeSpan: str = "Tonight"
    timeResolution: int = 60
    minElevationAngle: float = 10
    maxSunElevationAngle: float = 30
    observerAltitude: float = 0


class VisiblePassesCalculationSignals(QObject):
    progress = pyqtSignal(int)
    result = pyqtSignal(list)


class VisiblePassesCalculationTask(QRunnable):
    def __init__(self, request: VisiblePassesRequest, tleDatabase: TLEDatabase =None):
        super().__init__()
        self.request = request
        self.tleDatabase = tleDatabase
        self.engine = OrbitalMechanicsEngine()
        self.signals = VisiblePassesCalculationSignals()
        self.setAutoDelete(True)

    def run(self):
        try:
            results = []
            noradIndices = self.tleDatabase.dataFrame["NORAD_CAT_ID"].dropna().astype(int).to_list()
            for i, noradIndex in enumerate(noradIndices):
                try:
                    results.append(0)
                except Exception as e:
                    print(f"Skipping NORAD {noradIndex}: {e}")
                self.signals.progress.emit(i + 1)
            self.signals.result.emit(results)
        except Exception as e:
            print(f"Calculation error: {e}")
            self.signals.result.emit([])

    def _timeSpanBounds(self, now: datetime):
        if self.request.timeSpan == "Next 24 hours":
            return now, now + timedelta(hours=24)
        if self.request.timeSpan == "Next 48 hours":
            return now, now + timedelta(hours=48)
        end = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if end <= now:
            end += timedelta(days=1)
        return now, end

    def _buildFullJulianDates(self, startDateTime: datetime, endDateTime: datetime):
        durationSeconds = max(1, int((endDateTime - startDateTime).total_seconds()))
        resolution = max(2, durationSeconds // self.request.timeResolution + 1)
        julianDates, fractions = self.engine.datetimeToJulianDateArray(startDateTime, endDateTime, resolution=resolution)
        return julianDates + fractions