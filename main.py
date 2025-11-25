import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from src.gui.loadingScreen import LoadingScreen
from src.gui.mainWindow import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()

    splash = LoadingScreen()
    splash.main_window = window
    splash.show()

    sys.exit(app.exec_())