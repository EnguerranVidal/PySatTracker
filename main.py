import os
import sys

import qdarktheme
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from src.gui.loadingScreen import LoadingScreen
from src.gui.mainWindow import MainWindow

if __name__ == "__main__":
    qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    currentDirectory = os.path.dirname(os.path.realpath(__file__))

    window = MainWindow(currentDirectory)

    splash = LoadingScreen()
    splash.mainWindow = window
    splash.show()

    sys.exit(app.exec_())