from PyQt5.QtWidgets import QSplashScreen, QProgressBar
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer


class LoadingScreen(QSplashScreen):
    def __init__(self, pixmap_path="", duration=2000):
        pixmap = QPixmap(pixmap_path) if pixmap_path else QPixmap(400, 300)
        if pixmap_path == "":
            pixmap.fill(Qt.black)

        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setFont(QFont("Arial", 12))

        self.progress = QProgressBar(self)
        self.progress.setGeometry(50, pixmap.height() - 60, pixmap.width() - 100, 20)
        self.progress.setValue(0)

        self.counter = 0
        self.duration = duration

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(30)

    def update_progress(self):
        step = int((30 / self.duration) * 100)
        self.counter += step
        self.counter = min(self.counter, 100)
        self.progress.setValue(self.counter)

        if self.counter >= 100:
            self.timer.stop()
            self.finish(self.main_window)
            self.main_window.show()