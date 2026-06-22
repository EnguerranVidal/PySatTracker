from dataclasses import dataclass

from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal, pyqtSlot, QMetaObject, Q_ARG, QThreadPool, QRunnable


@dataclass
class VisiblePassesRequest:
    longitude: float
    latitude: float
    timeSpan: str = "Tonight"


class VisiblePassesCalculationTask(QRunnable):
    def __init__(self, request: VisiblePassesRequest, callback):
        super().__init__()
        self.request = request
        self.callback = callback
        self.setAutoDelete(True)

    def run(self):
        try:
            satellites = ["ISS", "STARLINK-1234", "STARLINK-5678", "METEOR-M", "HST"]
            results = []
            for i, sat_name in enumerate(satellites):
                results.append(0)
                progress = i + 1
                QMetaObject.invokeMethod(self, "_emitProgress", Qt.QueuedConnection, Q_ARG(int, progress))
            self.callback(results)
        except Exception as e:
            print(f"Calculation error: {e}")
            self.callback([])

    @pyqtSlot(int)
    def _emitProgress(self, progress: int):
        pass