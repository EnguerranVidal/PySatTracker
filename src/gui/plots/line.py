from datetime import datetime, timedelta
from pyqtgraph import PlotWidget, mkPen
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtWidgets import *

from src.core.objects import ActiveObjectsModel
from src.core.engine.orbitalEngine import OrbitalMechanicsEngine


class LinePlot(QWidget):
    activeObjectsChanged = pyqtSignal()
    dataRequestCreated = pyqtSignal(int, dict)
    dataRequestUpdated = pyqtSignal(int, dict)
    dataRequestDestroyed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot = PlotWidget(self)
        self.plot.addLegend()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.lastPositions = None
        self.activeObjects = None
        self.configuration = {'LINES': [], 'TIME': {'MODE': 'REAL', 'BEFORE': 30.0, 'BEFORE_UNIT': 'minutes', 'AFTER': 30.0, 'AFTER_UNIT': 'minutes', 'START': None, 'END': None}}
        self.plotItems = []
        self.requestIndexProvider = None

    def addLine(self, name=None, color='#ffffff', width=3, style=Qt.SolidLine, lineConfiguration=None):
        if name is None:
            name = f"Line {len(self.configuration['LINES']) + 1}"
        colorName = QColor(color).name()
        xRequestIndex, yRequestIndex = self.requestIndexProvider(), self.requestIndexProvider()
        if lineConfiguration is None:
            lineConfiguration = {'NAME': name, 'COLOR': colorName, 'WIDTH': width, 'STYLE': style, 'X_OBJECT': None, 'X_VARIABLE': None, 'Y_OBJECT': None, 'Y_VARIABLE': None, 'RESOLUTION': 361, 'X_REQUEST_ID': xRequestIndex, 'Y_REQUEST_ID': yRequestIndex}
            self.configuration['LINES'].append(lineConfiguration)
        lineConfiguration['X_REQUEST_ID'] = xRequestIndex
        lineConfiguration['Y_REQUEST_ID'] = yRequestIndex
        pen = mkPen(QColor(colorName), width=width, style=style)
        item = self.plot.plot([], [], pen=pen, name=name)
        self.plotItems.append(item)
        self.dataRequestCreated.emit(xRequestIndex, self._buildDataRequest(self.configuration['TIME'].copy(), lineConfiguration['X_OBJECT'], lineConfiguration['X_VARIABLE'], lineConfiguration['RESOLUTION']))
        self.dataRequestCreated.emit(yRequestIndex, self._buildDataRequest(self.configuration['TIME'].copy(), lineConfiguration['Y_OBJECT'], lineConfiguration['Y_VARIABLE'], lineConfiguration['RESOLUTION']))

    def setConfiguration(self, configuration):
        self.destroyDataRequest()
        for item in self.plotItems:
            self.plot.removeItem(item)
        self.plotItems = []
        self.configuration = configuration.copy()
        for lineConfiguration in self.configuration['LINES']:
            name = lineConfiguration.get('NAME', f"Line {len(self.plotItems) + 1}")
            color = lineConfiguration.get('COLOR', '#ffffff')
            width = lineConfiguration.get('WIDTH', 1)
            style = lineConfiguration.get('STYLE', Qt.SolidLine)
            self.addLine(name=name, color=color, width=width, style=style, lineConfiguration=lineConfiguration)

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects
        self.activeObjectsChanged.emit()

    def updateData(self, positions: dict):
        self.lastPositions = positions
        newPlotData = positions.get('PLOT_VIEW', {}).get('REQUESTS', {})
        if not newPlotData:
            return
        self._updatePlotItems(newPlotData)

    def _updatePlotItems(self, newPlotData: dict):
        updatedRequestIndices = set(newPlotData.keys())
        for i, line in enumerate(self.configuration['LINES']):
            xIndex, yIndex = line.get('X_REQUEST_ID'), line.get('Y_REQUEST_ID')
            xDataUpdated, yDataUpdated = xIndex in updatedRequestIndices, yIndex in updatedRequestIndices
            xVariableDefined, yVariableDefined = line.get('X_VARIABLE') is not None, line.get('Y_VARIABLE') is not None
            plotItem = self.plotItems[i]
            if xDataUpdated and yDataUpdated:
                xPlotData, yPlotData = newPlotData.get(xIndex), newPlotData.get(yIndex)
                if not xPlotData or not yPlotData:
                    plotItem.setData([], [])
                    continue
                xDataValues, yDataValues = xPlotData.get("VALUES", []), yPlotData.get("VALUES", [])
                nbDataPoints = min(len(xDataValues), len(yDataValues))
                if nbDataPoints == 0:
                    plotItem.setData([], [])
                    continue
                xCleanDataValues, yCleanDataValues = [], []
                for xv, yv in zip(xDataValues[:nbDataPoints], yDataValues[:nbDataPoints]):
                    if xv is None or yv is None:
                        continue
                    xCleanDataValues.append(xv)
                    yCleanDataValues.append(yv)
                plotItem.setData(xCleanDataValues, yCleanDataValues)
            elif xDataUpdated or yDataUpdated:
                plotItem.setData([], [])
            else:
                if xVariableDefined and yVariableDefined:
                    continue
                else:
                    plotItem.setData([], [])

    @staticmethod
    def _buildDataRequest(timeConfiguration, objectIndex, variable, resolution):
        return {'TIME': timeConfiguration, 'OBJECT': objectIndex, 'VARIABLE': variable, 'RESOLUTION': resolution}

    def createDataRequest(self):
        for line in self.configuration['LINES']:
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('X_OBJECT'), line.get('X_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestCreated.emit(line.get('X_REQUEST_ID'), request)
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('Y_OBJECT'), line.get('Y_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestCreated.emit(line.get('Y_REQUEST_ID'), request)

    def updateDataRequest(self):
        for line in self.configuration['LINES']:
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('X_OBJECT'), line.get('X_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestUpdated.emit(line.get('X_REQUEST_ID'), request)
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('Y_OBJECT'), line.get('Y_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestUpdated.emit(line.get('Y_REQUEST_ID'), request)

    def destroyDataRequest(self):
        for line in self.configuration['LINES']:
            if line.get('X_REQUEST_ID'):
                self.dataRequestDestroyed.emit(line.get('X_REQUEST_ID'))
            if line.get('Y_REQUEST_ID'):
                self.dataRequestDestroyed.emit(line.get('Y_REQUEST_ID'))

    def closeEvent(self, event):
        self.destroyDataRequest()
        super().closeEvent(event)


class LinePlotSettingsWidget(QWidget):
    def __init__(self, linePlot: LinePlot, dockWidget=None, parent=None):
        super().__init__(parent)
        self.linePlot = linePlot
        self.linePlot.activeObjectsChanged.connect(self.refreshObjectCombos)
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
        self.addButton = QPushButton('Add Line')
        self.removeButton = QPushButton('Remove Line')
        self.addButton.clicked.connect(self.addNewLine)
        self.removeButton.clicked.connect(self.removeSelectedLine)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addWidget(self.addButton)
        self.buttonLayout.addWidget(self.removeButton)
        self.listWidget = QListWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.listWidget.currentRowChanged.connect(self.stackedWidget.setCurrentIndex)

        # TIME SETTINGS
        self.timeGroup = QGroupBox('Time Settings')
        self.realTimeRadio = QRadioButton('Real Time')
        self.fixedTimeRadio = QRadioButton('Fixed Time')
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
        self.beforeRealTimeUnitComboBox.addItems(['seconds', 'minutes', 'hours', 'days', 'orbital periods'])
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
        self.afterRealTimeUnitComboBox.addItems(['seconds', 'minutes', 'hours', 'days', 'orbital periods'])
        self.afterRealTimeUnitComboBox.setCurrentText(self.linePlot.configuration['TIME']['AFTER_UNIT'])
        self.afterRealTimeUnitComboBox.currentTextChanged.connect(self._afterUnitChanged)
        afterRealTimeLayout = QHBoxLayout()
        afterRealTimeLayout.addWidget(self.afterRealTimeSpinBox)
        afterRealTimeLayout.addWidget(self.afterRealTimeUnitComboBox)
        self.realTimeWidget = QWidget()
        realTimeFormLayout = QFormLayout(self.realTimeWidget)
        realTimeFormLayout.addRow('Time Before:', beforeRealTimeLayout)
        realTimeFormLayout.addRow('Time After:', afterRealTimeLayout)
        self.startTimeEdit = QDateTimeEdit()
        self.startTimeEdit.setCalendarPopup(True)
        self.startTimeEdit.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        startTimeString = self.linePlot.configuration['TIME']['START']
        if startTimeString:
            dt = QDateTime.fromString(startTimeString, Qt.ISODate)
            if dt.isValid():
                self.startTimeEdit.setDateTime(dt)
        self.startTimeEdit.dateTimeChanged.connect(self._startChanged)
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setCalendarPopup(True)
        self.endTimeEdit.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        endTimeString = self.linePlot.configuration['TIME']['END']
        if endTimeString:
            dt = QDateTime.fromString(endTimeString, Qt.ISODate)
            if dt.isValid():
                self.endTimeEdit.setDateTime(dt)
        self.endTimeEdit.dateTimeChanged.connect(self._endChanged)
        self.fixedTimeWidget = QWidget()
        fixedTimeLayout = QFormLayout(self.fixedTimeWidget)
        fixedTimeLayout.addRow('Start Time:', self.startTimeEdit)
        fixedTimeLayout.addRow('End Time:', self.endTimeEdit)
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
        line = self.linePlot.configuration['LINES'][row]
        if line.get('X_REQUEST_ID'):
            self.linePlot.dataRequestDestroyed.emit(line.get('X_REQUEST_ID'))
        if line.get('Y_REQUEST_ID'):
            self.linePlot.dataRequestDestroyed.emit(line.get('Y_REQUEST_ID'))
        self.linePlot.configuration['LINES'].pop(row)
        item = self.linePlot.plotItems.pop(row)
        self.linePlot.plot.removeItem(item)
        self.updateLinesList()

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
        if self.fixedTimeRadio.isChecked():
            now = datetime.utcnow()
            timeConfiguration = self.linePlot.configuration['TIME']
            if not timeConfiguration.get('START'):
                start = now - timedelta(minutes=30)
                self.linePlot.configuration['TIME']['START'] = start.isoformat()
            if not timeConfiguration.get('END'):
                end = now + timedelta(minutes=30)
                self.linePlot.configuration['TIME']['END'] = end.isoformat()
            self.startTimeEdit.setDateTime(QDateTime.fromString(timeConfiguration['START'], Qt.ISODate))
            self.endTimeEdit.setDateTime(QDateTime.fromString(timeConfiguration['END'], Qt.ISODate))
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

    def _startChanged(self, dt):
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
        self.styleComboBox.addItem('Solid', Qt.SolidLine)
        self.styleComboBox.addItem('Dash', Qt.DashLine)
        self.styleComboBox.addItem('Dot', Qt.DotLine)
        self.styleComboBox.addItem('Dash Dot', Qt.DashDotLine)
        self.styleComboBox.setCurrentIndex(self.styleComboBox.findData(self.line['STYLE']))
        self.styleComboBox.currentIndexChanged.connect(self._updateStyle)
        generalLayout = QFormLayout(self.generalGroup)
        generalLayout.addRow('Name:', self.nameEdit)
        generalLayout.addRow('Color:', colorLayout)
        generalLayout.addRow('Width:', self.widthSpinBox)
        generalLayout.addRow('Style:', self.styleComboBox)

        # X & Y AXES SETTINGS
        self.xGroup = QGroupBox('X Axis')
        self.xObjectComboBox = QComboBox()
        self.fillObjectCombo(self.xObjectComboBox)
        index = self.xObjectComboBox.findData(self.line['X_OBJECT'])
        self.xObjectComboBox.setCurrentIndex(index if index != -1 else 0)
        self.xVariableComboBox = QComboBox()
        self._fillVariableCombo(self.xVariableComboBox, self.xObjectComboBox)
        index = self.xVariableComboBox.findData(self.line['X_VARIABLE'])
        self.xVariableComboBox.setCurrentIndex(index if index != -1 else 0)
        self.xVariableComboBox.currentTextChanged.connect(self._updateVariableX)
        self.xObjectComboBox.currentTextChanged.connect(self._updateObjectX)
        xLayout = QFormLayout(self.xGroup)
        xLayout.addRow('Object:', self.xObjectComboBox)
        xLayout.addRow('Variable:', self.xVariableComboBox)
        self.yGroup = QGroupBox('Y Axis')
        self.yObjectComboBox = QComboBox()
        self.fillObjectCombo(self.yObjectComboBox)
        index = self.yObjectComboBox.findData(self.line['Y_OBJECT'])
        self.yObjectComboBox.setCurrentIndex(index if index != -1 else 0)
        self.yVariableComboBox = QComboBox()
        self._fillVariableCombo(self.yVariableComboBox, self.yObjectComboBox)
        index = self.yVariableComboBox.findData(self.line['Y_VARIABLE'])
        self.yVariableComboBox.setCurrentIndex(index if index != -1 else 0)
        self.yVariableComboBox.currentTextChanged.connect(self._updateVariableY)
        self.yObjectComboBox.currentTextChanged.connect(self._updateObjectY)
        yLayout = QFormLayout(self.yGroup)
        yLayout.addRow('Object:', self.yObjectComboBox)
        yLayout.addRow('Variable:', self.yVariableComboBox)
        self.swapButton = QPushButton('Swap Axes')
        self.swapButton.clicked.connect(self._swapAxes)
        self.axesGroup = QGroupBox('Axes Settings')
        self.resolutionSpinBox = QSpinBox()
        self.resolutionSpinBox.setRange(2, 10000)
        self.resolutionSpinBox.setValue(self.line.get('RESOLUTION', 361))
        self.resolutionSpinBox.setToolTip("Number of points used to compute the line")
        self.resolutionSpinBox.valueChanged.connect(self._updateResolution)
        resolutionLayout = QFormLayout()
        resolutionLayout.addRow("Resolution:", self.resolutionSpinBox)
        axesLayout = QVBoxLayout(self.axesGroup)
        axesLayout.addWidget(self.xGroup)
        axesLayout.addWidget(self.yGroup)
        axesLayout.addWidget(self.swapButton)
        axesLayout.addLayout(resolutionLayout)

        layout = QVBoxLayout(self)
        layout.addWidget(self.generalGroup)
        layout.addWidget(self.axesGroup)
        self._updateSwapButtonState()

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
        colorButton.setStyleSheet('border: 1px solid #666;')
        return colorButton

    @staticmethod
    def _setButtonColor(colorButton, color):
        colorButton.setStyleSheet(f'background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;')

    def fillObjectCombo(self, combo: QComboBox):
        combo.blockSignals(True)
        currentData = combo.currentData()
        combo.clear()
        combo.addItem("NONE", None)
        combo.insertSeparator(combo.count())
        activeObjects = self.linePlot.activeObjects
        if activeObjects is None:
            combo.blockSignals(False)
            return
        objects = activeObjects.getAllObjects()
        sortedObjects = sorted(objects, key=lambda o: (o.name or "", o.noradIndex))
        for obj in sortedObjects:
            displayName = obj.name if obj.name else str(obj.noradIndex)
            combo.addItem(displayName, obj.noradIndex)
        index = combo.findData(currentData)
        combo.setCurrentIndex(index if index != -1 else 0)
        combo.blockSignals(False)

    def _fillVariableCombo(self, combo: QComboBox, objectCombo: QComboBox = None):
        combo.blockSignals(True)
        currentVariable = combo.currentData()
        combo.clear()
        combo.addItem("NONE", None)
        if objectCombo.currentData() is not None:
            combo.insertSeparator(combo.count())
            for variable in self.engineVariables:
                combo.addItem(variable, variable)
        index = combo.findData(currentVariable)
        combo.setCurrentIndex(index if index != -1 else 0)
        combo.blockSignals(False)

    def _swapAxes(self):
        self.xObjectComboBox.blockSignals(True)
        self.yObjectComboBox.blockSignals(True)
        self.xVariableComboBox.blockSignals(True)
        self.yVariableComboBox.blockSignals(True)
        xObject, yObject = self.xObjectComboBox.currentData(), self.yObjectComboBox.currentData()
        xVariable, yVariable = self.xVariableComboBox.currentData(), self.yVariableComboBox.currentData()
        self.xObjectComboBox.setCurrentIndex(self.xObjectComboBox.findData(yObject))
        self.yObjectComboBox.setCurrentIndex(self.yObjectComboBox.findData(xObject))
        self._fillVariableCombo(self.xVariableComboBox, self.xObjectComboBox)
        self._fillVariableCombo(self.yVariableComboBox, self.yObjectComboBox)
        self.xVariableComboBox.setCurrentIndex(self.xVariableComboBox.findData(yVariable))
        self.yVariableComboBox.setCurrentIndex(self.yVariableComboBox.findData(xVariable))
        self.xObjectComboBox.blockSignals(False)
        self.yObjectComboBox.blockSignals(False)
        self.xVariableComboBox.blockSignals(False)
        self.yVariableComboBox.blockSignals(False)
        self._updateObjectX(None)
        self._updateObjectY(None)
        self._updateVariableX(None)
        self._updateVariableY(None)
        self._updateSwapButtonState()

    def _updateSwapButtonState(self):
        xObject, yObject = self.xObjectComboBox.currentData(), self.yObjectComboBox.currentData()
        xVariable, yVariable = self.xVariableComboBox.currentData(), self.yVariableComboBox.currentData()
        is_same = (xObject == yObject) and (xVariable == yVariable)
        self.swapButton.setEnabled(not is_same)

    def _updateObjectX(self, text):
        self._fillVariableCombo(self.xVariableComboBox, self.xObjectComboBox)
        self.line['X_OBJECT'] = self.xObjectComboBox.currentData()
        self.xVariableComboBox.setEnabled(self.xObjectComboBox.currentData() is not None)
        self.linePlot.updateDataRequest()
        self._updateSwapButtonState()

    def _updateObjectY(self, text):
        self._fillVariableCombo(self.yVariableComboBox, self.yObjectComboBox)
        self.line['Y_OBJECT'] = self.yObjectComboBox.currentData()
        self.yVariableComboBox.setEnabled(self.yObjectComboBox.currentData() is not None)
        self.linePlot.updateDataRequest()
        self._updateSwapButtonState()

    def _updateVariableX(self, text):
        self.line['X_VARIABLE'] = self.xVariableComboBox.currentData()
        self.linePlot.updateDataRequest()
        self._updateSwapButtonState()

    def _updateVariableY(self, text):
        self.line['Y_VARIABLE'] = self.yVariableComboBox.currentData()
        self.linePlot.updateDataRequest()
        self._updateSwapButtonState()

    def _updateResolution(self, value):
        self.line['RESOLUTION'] = value
        self.linePlot.updateDataRequest()
