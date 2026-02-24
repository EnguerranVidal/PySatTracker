from pyqtgraph import PlotWidget, mkPen
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *


class LinePlot(QWidget):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.plot = PlotWidget(self)
        self.plot.addLegend()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.configuration = {'LINES': []}

    def addLine(self, name=None, color='w', width=1, style=Qt.SolidLine):
        if name is None:
            name = f"Line {len(self.configuration['LINES']) + 1}"
        pen = mkPen(color, width=width, style=style)
        item = self.plot.plot([], [], pen=pen, name=name)
        self.configuration['LINES'].append({'ITEM': item, 'NAME': name, 'PEN': pen})


class LinePlotSettingsWidget(QWidget):
    def __init__(self, linePlot: LinePlot, parent=None):
        super().__init__(parent)
        self.linePlot = linePlot
        # LINE MANAGEMENT BUTTONS
        self.addButton = QPushButton("Add Line")
        self.removeButton = QPushButton("Remove Line")
        self.addButton.clicked.connect(self.addNewLine)
        self.removeButton.clicked.connect(self.removeSelectedLine)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addWidget(self.addButton)
        self.buttonLayout.addWidget(self.removeButton)

        # LINE LIST AND SETTINGS PANEL
        self.listWidget = QListWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.listWidget.currentRowChanged.connect(self.stackedWidget.setCurrentIndex)

        # MAIN LAYOUT
        mainLayout = QVBoxLayout(self)
        mainLayout.addLayout(self.buttonLayout)
        mainLayout.addWidget(self.listWidget)
        mainLayout.addWidget(self.stackedWidget)

    def addNewLine(self):
        self.linePlot.addLine()
        self.updateLinesList()

    def removeSelectedLine(self):
        row = self.listWidget.currentRow()
        if row >= 0:
            line = self.linePlot.configuration['LINES'].pop(row)
            self.linePlot.plot.removeItem(line['ITEM'])
            self.updateLinesList()

    def updateLinesList(self):
        self.listWidget.clear()
        while self.stackedWidget.count() > 0:
            widget = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(widget)
            widget.deleteLater()
        for lineConfiguration in self.linePlot.configuration['LINES']:
            self.listWidget.addItem(lineConfiguration['NAME'])
            settingsPage = LineSettingsPage(lineConfiguration)
            settingsPage.nameChanged.connect(lambda text, l=lineConfiguration: self.updateLineName(l, text))
            self.stackedWidget.addWidget(settingsPage)

    def updateLineName(self, line, text):
        line['NAME'] = text
        row = self.linePlot.configuration['LINES'].index(line)
        self.listWidget.item(row).setText(text)


class LineSettingsPage(QWidget):
    nameChanged = pyqtSignal(str)

    def __init__(self, line, parent=None):
        super().__init__(parent)
        self.line = line