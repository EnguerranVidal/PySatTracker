import random
from datetime import datetime
from pyqtgraph import PlotWidget, mkPen
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtWidgets import *

from src.core.orbitalEngine import OrbitalMechanicsEngine


class LinePlot(QWidget):
    visibleObjectsChanged = pyqtSignal()
    dataRequestCreated = pyqtSignal(int, dict)
    dataRequestUpdated = pyqtSignal(int, dict)
    dataRequestDestroyed = pyqtSignal(int)

    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.plot = PlotWidget(self)
        self.plot.addLegend()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.lastPositions = None
        self.visibleObjects = set()
        self.configuration = {'LINES': [], 'TIME': {'MODE': 'REAL', 'BEFORE': 30.0, 'BEFORE_UNIT': 'minutes', 'AFTER': 30.0, 'AFTER_UNIT': 'minutes', 'START': None, 'END': None}}
        self.plotItems = []
        self.requestIndexProvider = None

    def addLine(self, name=None, color='#ffffff', width=1, style=Qt.SolidLine):
        if name is None:
            name = f"Line {len(self.configuration['LINES']) + 1}"
        colorName = QColor(color).name() if isinstance(color, str) else color.name()
        xRequestIndex, yRequestIndex = self.requestIndexProvider(), self.requestIndexProvider()
        lineConfiguration = {'NAME': name, 'COLOR': colorName, 'WIDTH': width, 'STYLE': style, 'X_OBJECT': 'TIME', 'X_VARIABLE': '', 'Y_OBJECT': 'TIME', 'Y_VARIABLE': '', 'RESOLUTION': 361, 'X_REQUEST_ID': xRequestIndex, 'Y_REQUEST_ID': yRequestIndex}
        self.configuration['LINES'].append(lineConfiguration)
        pen = mkPen(QColor(colorName), width=width, style=style)
        item = self.plot.plot([], [], pen=pen, name=name)
        self.plotItems.append(item)
        # TODO : Add the data request creation

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

    def updateData(self, positions: dict, visibleObjects: set[int]):
        self.lastPositions = positions
        if self.visibleObjects != visibleObjects:
            self.visibleObjects = visibleObjects
            self.visibleObjectsChanged.emit()

    def _buildDataRequest(self, objectIndex, variable):
        timeConfiguration = self.configuration['TIME']
        return {'TIME': timeConfiguration, 'OBJECT': objectIndex, 'VARIABLE': variable}

    def createDataRequest(self):
        for line in self.configuration["LINES"]:
            request = self._buildDataRequest(line.get("X_OBJECT"), line.get("X_VARIABLE"))
            self.dataRequestCreated.emit(line.get("X_REQUEST_ID"), request)
            request = self._buildDataRequest(line.get("Y_OBJECT"), line.get("Y_VARIABLE"))
            self.dataRequestCreated.emit(line.get("Y_REQUEST_ID"), request)

    def updateDataRequest(self):
        for line in self.configuration["LINES"]:
            request = self._buildDataRequest(line.get("X_OBJECT"), line.get("X_VARIABLE"))
            self.dataRequestUpdated.emit(line.get("X_REQUEST_ID"), request)
            request = self._buildDataRequest(line.get("Y_OBJECT"), line.get("Y_VARIABLE"))
            self.dataRequestUpdated.emit(line.get("Y_REQUEST_ID"), request)

    def destroyDataRequest(self):
        for line in self.configuration["LINES"]:
            if line.get("X_REQUEST_ID"):
                self.dataRequestDestroyed.emit(line.get("X_REQUEST_ID"))
            if line.get("Y_REQUEST_ID"):
                self.dataRequestDestroyed.emit(line.get("Y_REQUEST_ID"))

    def closeEvent(self, event):
        self.destroyDataRequest()
        super().closeEvent(event)


class LinePlotSettingsWidget(QWidget):
    def __init__(self, linePlot: LinePlot, dockWidget=None, parent=None):
        super().__init__(parent)
        self.linePlot = linePlot
        self.linePlot.visibleObjectsChanged.connect(self.refreshObjectCombos)
        self.dockWidget = dockWidget

        # PLOT NAME EDITOR
        self.titleEdit = QLineEdit()
        if self.dockWidget is not None:
            self.titleEdit.setText(self.dockWidget.windowTitle())
        self.titleEdit.textChanged.connect(self._updateDockTitle)
        self.titleLayout = QHBoxLayout()
        self.titleLayout.addWidget(QLabel("Plot Name:"))
        self.titleLayout.addWidget(self.titleEdit)

        # LINE MANAGEMENT
        self.addButton = QPushButton("Add Line")
        self.removeButton = QPushButton("Remove Line")
        self.addButton.clicked.connect(self.addNewLine)
        self.removeButton.clicked.connect(self.removeSelectedLine)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addWidget(self.addButton)
        self.buttonLayout.addWidget(self.removeButton)
        self.listWidget = QListWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.listWidget.currentRowChanged.connect(self.stackedWidget.setCurrentIndex)

        # TIME SETTINGS
        self.timeGroup = QGroupBox("Time Settings")
        self.realTimeRadio = QRadioButton("Real Time")
        self.fixedTimeRadio = QRadioButton("Fixed Time")
        if self.linePlot.configuration['TIME']['MODE'] == 'REAL':
            self.realTimeRadio.setChecked(True)
        elif self.linePlot.configuration['TIME']['MODE'] == 'FIXED':
            self.fixedTimeRadio.setChecked(True)
        else:
            self.linePlot.configuration['TIME']['MODE'] = 'REAL'
            self.realTimeRadio.setChecked(True)
        self.realTimeRadio.toggled.connect(self.setTimeMode)
        timeModeLayout = QHBoxLayout()
        timeModeLayout.addWidget(self.realTimeRadio)
        timeModeLayout.addWidget(self.fixedTimeRadio)
        self.beforeRealTimeSpinBox = QDoubleSpinBox()
        self.beforeRealTimeSpinBox.setRange(0, 1e6)
        self.beforeRealTimeSpinBox.setDecimals(2)
        self.beforeRealTimeSpinBox.setValue(self.linePlot.configuration['TIME']['BEFORE'])
        self.beforeRealTimeSpinBox.valueChanged.connect(self._beforeChanged)
        self.beforeRealTimeUnitComboBox = QComboBox()
        self.beforeRealTimeUnitComboBox.addItems(["seconds", "minutes", "hours", "days", "orbital periods"])
        self.beforeRealTimeUnitComboBox.setCurrentText(self.linePlot.configuration['TIME']['BEFORE_UNIT'])
        self.beforeRealTimeUnitComboBox.currentTextChanged.connect(self._beforeUnitChanged)
        beforeRealTimeLayout = QHBoxLayout()
        beforeRealTimeLayout.addWidget(self.beforeRealTimeSpinBox)
        beforeRealTimeLayout.addWidget(self.beforeRealTimeUnitComboBox)
        self.afterRealTimeSpinBox = QDoubleSpinBox()
        self.afterRealTimeSpinBox.setRange(0, 1e6)
        self.afterRealTimeSpinBox.setDecimals(2)
        self.afterRealTimeSpinBox.setValue(self.linePlot.configuration['TIME']['AFTER'])
        self.afterRealTimeSpinBox.valueChanged.connect(self._afterChanged)
        self.afterRealTimeUnitComboBox = QComboBox()
        self.afterRealTimeUnitComboBox.addItems(["seconds", "minutes", "hours", "days", "orbital periods"])
        self.afterRealTimeUnitComboBox.setCurrentText(self.linePlot.configuration['TIME']['AFTER_UNIT'])
        self.afterRealTimeUnitComboBox.currentTextChanged.connect(self._afterUnitChanged)
        afterRealTimeLayout = QHBoxLayout()
        afterRealTimeLayout.addWidget(self.afterRealTimeSpinBox)
        afterRealTimeLayout.addWidget(self.afterRealTimeUnitComboBox)
        self.realTimeWidget = QWidget()
        realTimeFormLayout = QFormLayout(self.realTimeWidget)
        realTimeFormLayout.addRow("Time Before:", beforeRealTimeLayout)
        realTimeFormLayout.addRow("Time After:", afterRealTimeLayout)
        self.startTimeEdit = QDateTimeEdit()
        self.startTimeEdit.setCalendarPopup(True)
        self.startTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        startTimeString = self.linePlot.configuration['TIME']['START']
        if startTimeString:
            dt = QDateTime.fromString(startTimeString, Qt.ISODate)
            if dt.isValid():
                self.startTimeEdit.setDateTime(dt)
        self.startTimeEdit.dateTimeChanged.connect(lambda dt: self.linePlot.configuration['TIME'].update({'START': dt.toString(Qt.ISODate)}))
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setCalendarPopup(True)
        self.endTimeEdit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        endTimeString = self.linePlot.configuration['TIME']['END']
        if endTimeString:
            dt = QDateTime.fromString(endTimeString, Qt.ISODate)
            if dt.isValid():
                self.endTimeEdit.setDateTime(dt)
        self.endTimeEdit.dateTimeChanged.connect(lambda dt: self.linePlot.configuration['TIME'].update({'END': dt.toString(Qt.ISODate)}))
        self.fixedTimeWidget = QWidget()
        fixedTimeLayout = QFormLayout(self.fixedTimeWidget)
        fixedTimeLayout.addRow("Start Time:", self.startTimeEdit)
        fixedTimeLayout.addRow("End Time:", self.endTimeEdit)
        self.timeStackedWidget = QStackedWidget()
        self.timeStackedWidget.addWidget(self.realTimeWidget)
        self.timeStackedWidget.addWidget(self.fixedTimeWidget)
        self.timeStackedWidget.setCurrentIndex(0 if self.realTimeRadio.isChecked() else 1)
        timeLayout = QVBoxLayout(self.timeGroup)
        timeLayout.addLayout(timeModeLayout)
        timeLayout.addWidget(self.timeStackedWidget)

        # MAIN LAYOUT
        mainLayout = QVBoxLayout(self)
        mainLayout.addLayout(self.titleLayout)
        mainLayout.addWidget(self.timeGroup)
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
        self.linePlot.updateDataRequest()

    def removeSelectedLine(self):
        row = self.listWidget.currentRow()
        if row < 0 or row >= len(self.linePlot.plotItems):
            return
        self.linePlot.configuration['LINES'].pop(row)
        item = self.linePlot.plotItems.pop(row)
        self.linePlot.plot.removeItem(item)
        self.updateLinesList()
        self.linePlot.updateDataRequest()

    def updateLinesList(self):
        self.listWidget.clear()
        while self.stackedWidget.count() > 0:
            widget = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(widget)
            widget.deleteLater()
        for lineConfiguration in self.linePlot.configuration['LINES']:
            self.listWidget.addItem(lineConfiguration['NAME'])
            settingsPage = LineSettingsPage(owner=self, line=lineConfiguration, linePlot=self.linePlot)
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

    def refreshObjectCombos(self):
        for i in range(self.stackedWidget.count()):
            page = self.stackedWidget.widget(i)
            if isinstance(page, LineSettingsPage):
                page.fillObjectCombo(page.xObjectComboBox)
                page.fillObjectCombo(page.yObjectComboBox)

    def setTimeMode(self, mode):
        self.linePlot.configuration['TIME']['MODE'] = 'REAL' if self.realTimeRadio.isChecked() else 'FIXED'
        self.timeStackedWidget.setCurrentIndex(0 if self.realTimeRadio.isChecked() else 1)
        self.linePlot.updateDataRequest()

    def _beforeChanged(self, value):
        self.linePlot.configuration['TIME']['BEFORE'] = value
        self.linePlot.updateDataRequest()

    def _beforeUnitChanged(self, text):
        self.linePlot.configuration['TIME']['BEFORE_UNIT'] = text
        self.linePlot.updateDataRequest()

    def _afterChanged(self, value):
        self.linePlot.configuration['TIME']['AFTER'] = value
        self.linePlot.updateDataRequest()

    def _afterUnitChanged(self, text):
        self.linePlot.configuration['TIME']['AFTER_UNIT'] = text
        self.linePlot.updateDataRequest()

    def startChanged(self, dt):
        self.linePlot.configuration['TIME']['START'] = dt.toString(Qt.ISODate)
        self.linePlot.updateDataRequest()

    def _endChanged(self, dt):
        self.linePlot.configuration['TIME']['END'] = dt.toString(Qt.ISODate)
        self.linePlot.updateDataRequest()


class LineSettingsPage(QWidget):
    nameChanged = pyqtSignal(str)

    def __init__(self, line: dict, linePlot: LinePlot, parent=None, owner=None):
        super().__init__(parent)
        self.line = line
        self.linePlot = linePlot
        self.owner = owner if owner is not None else parent
        orbitalEngine = OrbitalMechanicsEngine()
        self.engineVariables = orbitalEngine.getAvailableVariables()
        # GENERAL LINE SETTINGS
        self.generalGroup = QGroupBox(f"General {self.line['NAME']} Settings")
        self.nameEdit = QLineEdit(self.line['NAME'])
        self.nameEdit.textChanged.connect(self._updateName)
        self.colorLabel = QLabel(QColor(self.line['COLOR']).name().upper())
        self.colorButton = self._colorButton()
        self._setButtonColor(self.colorButton, QColor(self.line['COLOR']).getRgb()[:3])
        self.colorButton.clicked.connect(self._pickColor)
        colorLayout = QHBoxLayout()
        colorLayout.setContentsMargins(0, 0, 0, 0)
        colorLayout.addWidget(self.colorButton)
        colorLayout.addWidget(self.colorLabel)
        self.widthSpinBox = QSpinBox()
        self.widthSpinBox.setRange(1, 10)
        self.widthSpinBox.setValue(self.line['WIDTH'])
        self.widthSpinBox.valueChanged.connect(self._updateWidth)
        self.styleComboBox = QComboBox()
        self.styleComboBox.addItem("Solid", Qt.SolidLine)
        self.styleComboBox.addItem("Dash", Qt.DashLine)
        self.styleComboBox.addItem("Dot", Qt.DotLine)
        self.styleComboBox.addItem("Dash Dot", Qt.DashDotLine)
        self.styleComboBox.setCurrentIndex(self.styleComboBox.findData(self.line['STYLE']))
        self.styleComboBox.currentIndexChanged.connect(self._updateStyle)
        generalLayout = QFormLayout(self.generalGroup)
        generalLayout.addRow("Name:", self.nameEdit)
        generalLayout.addRow("Color:", colorLayout)
        generalLayout.addRow("Width:", self.widthSpinBox)
        generalLayout.addRow("Style:", self.styleComboBox)

        # X & Y AXES SETTINGS
        self.xGroup = QGroupBox("X Axis")
        self.xObjectComboBox = QComboBox()
        self.fillObjectCombo(self.xObjectComboBox)
        self.xObjectComboBox.setCurrentText(self.line['X_OBJECT'])
        self.xObjectComboBox.currentTextChanged.connect(lambda text: self.line.update({'X_OBJECT': text}))
        self.xVariableComboBox = QComboBox()
        self._fillVariableCombo(self.xVariableComboBox, self.xObjectComboBox)
        self.xVariableComboBox.setCurrentText(self.line['X_VARIABLE'])
        self.xVariableComboBox.currentTextChanged.connect(self._updateVariableX)
        self.xObjectComboBox.currentTextChanged.connect(self._updateObjectX)
        xLayout = QFormLayout(self.xGroup)
        xLayout.addRow("Object:", self.xObjectComboBox)
        xLayout.addRow("Variable:", self.xVariableComboBox)
        self.yGroup = QGroupBox("Y Axis")
        self.yObjectComboBox = QComboBox()
        self.fillObjectCombo(self.yObjectComboBox)
        self.yObjectComboBox.setCurrentText(self.line['Y_OBJECT'])
        self.yObjectComboBox.currentTextChanged.connect(lambda text: self.line.update({'Y_OBJECT': text}))
        self.yVariableComboBox = QComboBox()
        self._fillVariableCombo(self.yVariableComboBox, self.yObjectComboBox)
        self.yVariableComboBox.setCurrentText(self.line['Y_VARIABLE'])
        self.yVariableComboBox.currentTextChanged.connect(self._updateVariableY)
        self.yObjectComboBox.currentTextChanged.connect(self._updateObjectY)
        yLayout = QFormLayout(self.yGroup)
        yLayout.addRow("Object:", self.yObjectComboBox)
        yLayout.addRow("Variable:", self.yVariableComboBox)
        self.swapButton = QPushButton("Swap Axes")
        self.swapButton.clicked.connect(self._swapAxes)
        self.axesGroup = QGroupBox("Axes Settings")
        axesLayout = QVBoxLayout(self.axesGroup)
        axesLayout.addWidget(self.xGroup)
        axesLayout.addWidget(self.yGroup)
        axesLayout.addWidget(self.swapButton)

        layout = QVBoxLayout(self)
        layout.addWidget(self.generalGroup)
        layout.addWidget(self.axesGroup)

    def _updateName(self, text):
        self.line['NAME'] = text
        self.generalGroup.setTitle(f"General {self.line['NAME']} Settings")
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

    def fillObjectCombo(self, combo: QComboBox):
        combo.blockSignals(True)
        currentObject, currentData = combo.currentText(), combo.currentData()
        combo.clear()
        combo.addItem("TIME")
        if self.linePlot.lastPositions:
            activeObjects = self.linePlot.lastPositions.get('PLOT_VIEW', {}).get('OBJECTS', {})
            objectNames = {norad: activeObjects[norad]['NAME'] for norad in self.linePlot.visibleObjects if norad in activeObjects}
            if objectNames:
                combo.insertSeparator(combo.count())
                for noradIndex, name in sorted(objectNames.items(), key=lambda kv: kv[1].lower()):
                     combo.addItem(name, noradIndex)
        if currentObject == "TIME":
            combo.setCurrentText("TIME")
        elif currentData is not None:
            index = combo.findData(currentData)
            combo.setCurrentIndex(index if index != -1 else 0)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _fillVariableCombo(self, combo: QComboBox, objectCombo: QComboBox = None):
        combo.blockSignals(True)
        currentVariable = combo.currentText()
        combo.clear()
        if objectCombo.currentText() == "TIME":
            combo.addItem("UTC_FORMAT")
            combo.addItem("LOC_FORMAT")
        else:
            for text in self.engineVariables:
                combo.addItem(text)
        if currentVariable:
            newIndex = combo.findText(currentVariable)
            combo.setCurrentIndex(newIndex if newIndex != -1 else 0)
        combo.blockSignals(False)

    def _swapAxes(self):
        xObject = self.xObjectComboBox.currentText()
        yObject = self.yObjectComboBox.currentText()
        self.xObjectComboBox.setCurrentText(yObject)
        self.yObjectComboBox.setCurrentText(xObject)
        xVariable = self.xVariableComboBox.currentText()
        yVariable = self.yVariableComboBox.currentText()
        self.xVariableComboBox.setCurrentText(yVariable)
        self.yVariableComboBox.setCurrentText(xVariable)

    def _updateObjectX(self, text):
        self._fillVariableCombo(self.xVariableComboBox, self.xObjectComboBox)
        self.line['X_OBJECT'] = text
        self.linePlot.updateDataRequest()

    def _updateObjectY(self, text):
        self._fillVariableCombo(self.yVariableComboBox, self.yObjectComboBox)
        self.line['Y_OBJECT'] = text
        self.linePlot.updateDataRequest()

    def _updateVariableX(self, text):
        self.line['X_VARIABLE'] = text
        self.linePlot.updateDataRequest()

    def _updateVariableY(self, text):
        self.line['Y_VARIABLE'] = text
        self.linePlot.updateRequest()
