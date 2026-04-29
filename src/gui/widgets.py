from PyQt5.QtWidgets import QSplashScreen, QProgressBar, QLabel
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer


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