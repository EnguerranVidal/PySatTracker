from pyqtgraph import PlotWidget, mkPen
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *

from src.core.orbitalEngine import OrbitalMechanicsEngine

class LinePlot(QWidget):
    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.plot = PlotWidget(self)
        self.plot.addLegend()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.configuration = {'LINES': []}
        self.plotItems = []

    def addLine(self, name=None, color='#ffffff', width=1, style=Qt.SolidLine):
        if name is None:
            name = f"Line {len(self.configuration['LINES']) + 1}"
        colorName = QColor(color).name() if isinstance(color, str) else color.name()
        line_config = {'NAME': name, 'COLOR': colorName, 'WIDTH': width, 'STYLE': style, 'X_OBJECT': 'TIME', 'X_VARIABLE': '', 'Y_OBJECT': 'TIME', 'Y_VARIABLE': ''}
        self.configuration['LINES'].append(line_config)
        pen = mkPen(QColor(colorName), width=width, style=style)
        item = self.plot.plot([], [], pen=pen, name=name)
        self.plotItems.append(item)

    def setConfiguration(self, config):
        for item in self.plotItems:
            self.plot.removeItem(item)
        self.plotItems = []
        self.configuration = config.copy()
        for lineConfiguration in self.configuration['LINES']:
            name = lineConfiguration.get('NAME', f"Line {len(self.plotItems) + 1}")
            color = lineConfiguration.get('COLOR', '#ffffff')
            width = lineConfiguration.get('WIDTH', 1)
            style = lineConfiguration.get('STYLE', Qt.SolidLine)
            pen = mkPen(QColor(color), width=width, style=style)
            item = self.plot.plot([], [], pen=pen, name=name)
            self.plotItems.append(item)


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

        self.updateLinesList()

    def _updateDockTitle(self):
        if self.dockWidget is not None:
            self.dockWidget.setWindowTitle(self.titleEdit.text())

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
            settingsPage = LineSettingsPage(lineConfiguration, self.linePlot, parent=self)
            settingsPage.nameChanged.connect(lambda text, l=lineConfiguration: self.updateLineName(l, text))
            self.stackedWidget.addWidget(settingsPage)

    def updateLineName(self, line, text):
        line['NAME'] = text
        row = self.linePlot.configuration['LINES'].index(line)
        item = self.linePlot.plotItems[row]
        plotItem = self.linePlot.plot.getPlotItem()
        legend = getattr(plotItem, 'legend', None)
        if legend is not None:
            legend.removeItem(item)
            legend.addItem(item, text)
        self.listWidget.item(row).setText(text)


class LineSettingsPage(QWidget):
    nameChanged = pyqtSignal(str)

    def __init__(self, line, linePlot, parent=None):
        super().__init__(parent)
        self.line = line
        self.linePlot = linePlot

        self.nameEdit = QLineEdit(self.line['NAME'])
        self.nameEdit.textChanged.connect(self._updateName)

        # COLOR SETTINGS
        self.colorLabel = QLabel(QColor(self.line['COLOR']).name().upper())
        self.colorButton = self._colorButton()
        self._setButtonColor(self.colorButton, QColor(self.line['COLOR']).getRgb()[:3])
        self.colorButton.clicked.connect(self._pickColor)
        colorLayout = QHBoxLayout()
        colorLayout.setContentsMargins(0, 0, 0, 0)
        colorLayout.addWidget(self.colorButton)
        colorLayout.addWidget(self.colorLabel)

        # WIDTH SETTINGS
        self.widthSpinBox = QSpinBox()
        self.widthSpinBox.setRange(1, 10)
        self.widthSpinBox.setValue(self.line['WIDTH'])
        self.widthSpinBox.valueChanged.connect(self._updateWidth)

        # LINE STYLE SETTINGS
        self.styleComboBox = QComboBox()
        self.styleComboBox.addItem("Solid", Qt.SolidLine)
        self.styleComboBox.addItem("Dash", Qt.DashLine)
        self.styleComboBox.addItem("Dot", Qt.DotLine)
        self.styleComboBox.addItem("Dash Dot", Qt.DashDotLine)
        self.styleComboBox.setCurrentIndex(self.styleComboBox.findData(self.line['STYLE']))
        self.styleComboBox.currentIndexChanged.connect(self._updateStyle)

        # X & Y AXES SETTINGS
        self.xGroup = QGroupBox("X Axis")
        self.xObjectComboBox = QComboBox()
        self._populateFirstCombo(self.xObjectComboBox)
        self.xObjectComboBox.setCurrentText(self.line['X_OBJECT'])
        self.xObjectComboBox.currentTextChanged.connect(lambda text: self.line.update({'X_OBJECT': text}))
        self.xVariableComboBox = QComboBox()
        self._populateSecondCombo(self.xVariableComboBox)
        self.xVariableComboBox.setCurrentText(self.line['X_VARIABLE'])
        self.xVariableComboBox.currentTextChanged.connect(lambda text: self.line.update({'X_VARIABLE': text}))
        xLayout = QFormLayout(self.xGroup)
        xLayout.addRow("Object:", self.xObjectComboBox)
        xLayout.addRow("Variable:", self.xVariableComboBox)
        self.yGroup = QGroupBox("Y Axis")
        self.yObjectComboBox = QComboBox()
        self._populateFirstCombo(self.yObjectComboBox)
        self.yObjectComboBox.setCurrentText(self.line['Y_OBJECT'])
        self.yObjectComboBox.currentTextChanged.connect(lambda text: self.line.update({'Y_OBJECT': text}))
        self.yVariableComboBox = QComboBox()
        self._populateSecondCombo(self.yVariableComboBox)
        self.yVariableComboBox.setCurrentText(self.line['Y_VARIABLE'])
        self.yVariableComboBox.currentTextChanged.connect(lambda text: self.line.update({'Y_VARIABLE': text}))
        yLayout = QFormLayout(self.yGroup)
        yLayout.addRow("Object:", self.yObjectComboBox)
        yLayout.addRow("Variable:", self.yVariableComboBox)
        self.swapButton = QPushButton("Swap Axes")
        self.swapButton.clicked.connect(self._swapAxes)

        self.axesGroup = QGroupBox("Axes Settings")
        self.axesLayout = QVBoxLayout(self.axesGroup)
        self.axesLayout.addWidget(self.xGroup)
        self.axesLayout.addWidget(self.yGroup)
        self.axesLayout.addWidget(self.swapButton)

        layout = QFormLayout(self)
        layout.addRow("Name:", self.nameEdit)
        layout.addRow("Color:", colorLayout)
        layout.addRow("Width:", self.widthSpinBox)
        layout.addRow("Style:", self.styleComboBox)
        layout.addRow(self.axesGroup)

    def _updateName(self, text):
        self.line['NAME'] = text
        self.nameChanged.emit(text)

    def _updateWidth(self, value):
        self.line['WIDTH'] = value
        pen = mkPen(QColor(self.line['COLOR']), width=value, style=self.line['STYLE'])
        row = self.linePlot.configuration['LINES'].index(self.line)
        self.linePlot.plotItems[row].setPen(pen)

    def _updateStyle(self, index):
        style = self.styleComboBox.itemData(index)
        self.line['STYLE'] = style
        pen = mkPen(QColor(self.line['COLOR']), width=self.line['WIDTH'], style=style)
        row = self.linePlot.configuration['LINES'].index(self.line)
        self.linePlot.plotItems[row].setPen(pen)

    def _pickColor(self):
        color = QColorDialog.getColor(QColor(self.line['COLOR']))
        if not color.isValid():
            return
        self._setButtonColor(self.colorButton, color.getRgb()[:3])
        self.colorLabel.setText(color.name().upper())
        self.line['COLOR'] = color.name()
        pen = mkPen(color, width=self.line['WIDTH'], style=self.line['STYLE'])
        row = self.linePlot.configuration['LINES'].index(self.line)
        self.linePlot.plotItems[row].setPen(pen)

    @staticmethod
    def _colorButton():
        colorButton = QPushButton()
        colorButton.setFixedSize(24, 24)
        colorButton.setStyleSheet("border: 1px solid #666;")
        return colorButton

    @staticmethod
    def _setButtonColor(colorButton, color):
        colorButton.setStyleSheet(f"background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;")

    def _populateFirstCombo(self, combo):
        combo.clear()
        combo.addItem("TIME")
        visibleNorads = getattr(self.parent().dockWidget, 'visibleNorads', [])
        lastPositions = getattr(self.parent().dockWidget, 'lastPositions', None)
        if lastPositions is not None:
            objectNames = {noradIndex: lastPositions['PLOT_VIEW']['OBJECTS'][noradIndex]['NAME'] for noradIndex in visibleNorads}
            combo.insertSeparator(combo.count())
            for noradIndex, name in sorted(objectNames.items(), key=lambda kv: kv[1].lower()):
                combo.addItem(name, noradIndex)

    @staticmethod
    def _populateSecondCombo(combo):
        orbitalEngine = OrbitalMechanicsEngine()
        variables = orbitalEngine.getAvailableVariables()
        for text in variables:
            combo.addItem(text)

    def _swapAxes(self):
        xObject = self.xObjectComboBox.currentText()
        yObject = self.yObjectComboBox.currentText()
        self.xObjectComboBox.setCurrentText(yObject)
        self.yObjectComboBox.setCurrentText(xObject)
        xVariable = self.xVariableComboBox.currentText()
        yVariable = self.yVariableComboBox.currentText()
        self.xVariableComboBox.setCurrentText(yVariable)
        self.yVariableComboBox.setCurrentText(xVariable)
