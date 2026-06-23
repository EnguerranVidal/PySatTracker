from dataclasses import dataclass
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal, pyqtSlot, QMetaObject, Q_ARG, QThreadPool, QRunnable


@dataclass
class VisiblePassesRequest:
    longitude: float
    latitude: float
    timeSpan: str = "Tonight"


class VisiblePassesCalculationSignals(QObject):
    progress = pyqtSignal(int)
    result = pyqtSignal(list)


class VisiblePassesCalculationTask(QRunnable):
    def __init__(self, request: VisiblePassesRequest, tleDatabase=None):
        super().__init__()
        self.request = request
        self.tleDatabase = tleDatabase
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
        pass