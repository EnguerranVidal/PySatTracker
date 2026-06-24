from PyQt5.QtCore import QObject, pyqtSignal

from core.database.starDatabase import StarDatabase
from core.database.tleDatabase import TLEDatabase


class DatabaseLoaderWorker(QObject):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, dataDir='data'):
        super().__init__()
        self.dataDir = dataDir

    def run(self):
        self.status.emit("Initializing databases...")
        tleDatabase = TLEDatabase(self.dataDir, statusCallback=self.status.emit)
        starDatabase = StarDatabase(self.dataDir, statusCallback=self.status.emit)
        total = len(TLEDatabase.CELESTRAK_SOURCES) + 1
        step = 100 / total
        current = 0
        for tag in TLEDatabase.CELESTRAK_SOURCES:
            tleDatabase.loadSource(tag)
            current += step
            self.progress.emit(int(current))
        tleDatabase.finalize()
        self.status.emit("Done.")
        self.finished.emit([tleDatabase, starDatabase])
