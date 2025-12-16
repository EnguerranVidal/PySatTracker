import os
import sys

import qdarktheme
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread

from src.core.tleDatabase import TLELoaderWorker
from src.gui.widgets import LoadingScreen
from src.gui.mainWindow import MainWindow

def main():
    qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    currentDirectory = os.path.dirname(os.path.realpath(__file__))
    dataDir = os.path.join(currentDirectory, "data", "norad")
    splash = LoadingScreen()
    splash.show()

    # LOADING WORKER THREAD
    thread = QThread()
    loader = TLELoaderWorker(dataDir)
    loader.moveToThread(thread)
    thread.started.connect(loader.run)
    loader.progress.connect(splash.setProgress)
    loader.status.connect(splash.setStatus)

    def onFinished(db):
        window = MainWindow(currentDirectory)
        window.setDatabase(db)
        splash.launchMainWindow(window)
        thread.quit()
        loader.deleteLater()
        thread.deleteLater()

    loader.finished.connect(onFinished)
    thread.start()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()