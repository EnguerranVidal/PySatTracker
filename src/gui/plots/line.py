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
    def __init__(self, linePlot: LinePlot, dockWidget=None, parent=None):
        super().__init__(parent)
        self.linePlot = linePlot
        self.dockWidget = dockWidget

        # PLOT NAME EDITOR
        self.titleEdit = QLineEdit()
        if self.dockWidget is not None:
            self.titleEdit.setText(self.dockWidget.windowTitle())
        self.titleEdit.textChanged.connect(self._updateDockTitle)
        self.titleLayout = QHBoxLayout()
        self.titleLayout.addWidget(QLabel("Plot Name:"))
        self.titleLayout.addWidget(self.titleEdit)

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
        mainLayout.addLayout(self.titleLayout)
        mainLayout.addLayout(self.buttonLayout)
        mainLayout.addWidget(self.listWidget)
        mainLayout.addWidget(self.stackedWidget)

    def _updateDockTitle(self):
        if self.dockWidget is not None:
            self.dockWidget.setWindowTitle(self.titleEdit.text())
            print(f"Updated dock title to: {self.titleEdit.text()}")

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
        self.linePlot.configuration['LINES'][row]['NAME'] = text
        item = self.linePlot.configuration['LINES'][row]['ITEM']
        plotItem = self.linePlot.plot.getPlotItem()
        legend = getattr(plotItem, 'legend', None)
        if legend is not None:
            legend.removeItem(item)
            legend.addItem(item, text)
        self.listWidget.item(row).setText(text)


class LineSettingsPage(QWidget):
    nameChanged = pyqtSignal(str)

    def __init__(self, line, parent=None):
        super().__init__(parent)
        self.line = line
        pen = self.line.get('PEN', None)

        self.nameEdit = QLineEdit(self.line['NAME'])
        self.nameEdit.textChanged.connect(self._updateName)

        # COLOR SETTINGS
        self.colorLabel = QLabel(pen.color().name().upper() if pen is not None else "#FFFFFF")
        self.colorButton = self._colorButton()
        self._setButtonColor(self.colorButton, pen.color().getRgb()[:3] if pen is not None else (255, 255, 255))
        self.colorButton.clicked.connect(self._pickColor)
        colorLayout = QHBoxLayout()
        colorLayout.setContentsMargins(0, 0, 0, 0)
        colorLayout.addWidget(self.colorButton)
        colorLayout.addWidget(self.colorLabel)

        # WIDTH SETTINGS
        self.widthSpinBox = QSpinBox()
        self.widthSpinBox.setRange(1, 10)
        self.widthSpinBox.setValue(pen.width())
        self.widthSpinBox.valueChanged.connect(self._updateWidth)

        # LINE STYLE SETTINGS
        self.styleComboBox = QComboBox()
        self.styleComboBox.addItem("Solid", Qt.SolidLine)
        self.styleComboBox.addItem("Dash", Qt.DashLine)
        self.styleComboBox.addItem("Dot", Qt.DotLine)
        self.styleComboBox.addItem("Dash Dot", Qt.DashDotLine)
        self.styleComboBox.setCurrentIndex(self.styleComboBox.findData(pen.style()))
        self.styleComboBox.currentIndexChanged.connect(self._updateStyle)

        layout = QFormLayout(self)
        layout.addRow("Name:", self.nameEdit)
        layout.addRow("Color:", colorLayout)
        layout.addRow("Width:", self.widthSpinBox)
        layout.addRow("Style:", self.styleComboBox)

    def _updateName(self, text):
        self.line['NAME'] = text
        self.nameChanged.emit(text)

    def _updateWidth(self, value):
        pen = mkPen(color=self.line['PEN'].color(), width=value, style=self.line['PEN'].style())
        self.line['ITEM'].setPen(pen)
        self.line['PEN'] = pen

    def _updateStyle(self, index):
        style = self.styleComboBox.itemData(index)
        pen = mkPen(color=self.line['PEN'].color(), width=self.line['PEN'].width(), style=style)
        self.line['ITEM'].setPen(pen)
        self.line['PEN'] = pen

    def _pickColor(self):
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        self._setButtonColor(self.colorButton, color.getRgb()[:3])
        self.colorLabel.setText(color.name().upper())
        pen = mkPen(color=color.getRgb()[:3], width=self.line['PEN'].width(), style=self.line['PEN'].style())
        self.line['ITEM'].setPen(pen)
        self.line['PEN'] = pen

    @staticmethod
    def _colorButton():
        colorButton = QPushButton()
        colorButton.setFixedSize(24, 24)
        colorButton.setStyleSheet("border: 1px solid #666;")
        return colorButton

    @staticmethod
    def _setButtonColor(colorButton, color):
        colorButton.setStyleSheet(f"background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;")
