import os
import sys

import qdarktheme
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread

from src.core.database.general import DatabaseLoaderWorker
from src.gui.common import LoadingScreen
from src.gui.mainWindow import MainWindow


def main():
    qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    qdarktheme.setup_theme('dark', additional_qss='QToolTip {color: black;}')
    currentDirectory = os.path.dirname(os.path.realpath(__file__))
    dataDir = os.path.join(currentDirectory, 'data')
    splash = LoadingScreen()
    splash.show()

    # LOADING WORKER THREAD
    thread = QThread()
    databaseLoader = DatabaseLoaderWorker(dataDir)
    databaseLoader.moveToThread(thread)
    thread.started.connect(databaseLoader.run)
    databaseLoader.progress.connect(splash.setProgress)
    databaseLoader.status.connect(splash.setStatus)

    def onFinished(databases):
        tleDatabase, starDatabase = databases
        splash.setToMaximumProgress()
        window = MainWindow(currentDirectory)
        window.setDatabases(tleDatabase, starDatabase)
        splash.launchMainWindow(window)
        thread.quit()
        databaseLoader.deleteLater()
        thread.deleteLater()

    databaseLoader.finished.connect(onFinished)
    thread.start()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()