from datetime import datetime, timedelta

import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, GraphicsObject
from PyQt5.QtGui import QColor, QPainter, QBrush, QPainterPath, QPen, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QRectF, QPointF
from PyQt5.QtWidgets import *

from src.core.objects import ActiveObjectsModel
from src.gui.utilities import upperBoundary
from src.core.engine.orbitalEngine import OrbitalMechanicsEngine


class PolarPlot(QWidget):
    activeObjectsChanged = pyqtSignal()
    dataRequestCreated = pyqtSignal(int, dict)
    dataRequestUpdated = pyqtSignal(int, dict)
    dataRequestDestroyed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot = PolarGraph(self)
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
        argumentRequestIndex, moduleRequestIndex = self.requestIndexProvider(), self.requestIndexProvider()
        if lineConfiguration is None:
            lineConfiguration = {'NAME': name, 'COLOR': colorName, 'WIDTH': width, 'STYLE': style, 'ARGUMENT_OBJECT': None, 'ARGUMENT_VARIABLE': None, 'MODULE_OBJECT': None, 'MODULE_VARIABLE': None, 'RESOLUTION': 361, 'ARGUMENT_REQUEST_ID': argumentRequestIndex, 'MODULE_REQUEST_ID': moduleRequestIndex}
            self.configuration['LINES'].append(lineConfiguration)
        lineConfiguration['ARGUMENT_REQUEST_ID'] = argumentRequestIndex
        lineConfiguration['MODULE_REQUEST_ID'] = moduleRequestIndex
        pen = mkPen(QColor(colorName), width=width, style=style)
        item = self.plot.plotPolar([], [], pen=pen, name=name)
        self.plotItems.append(item)
        self.dataRequestCreated.emit(argumentRequestIndex, self._buildDataRequest(self.configuration['TIME'].copy(), lineConfiguration['ARGUMENT_OBJECT'], lineConfiguration['ARGUMENT_VARIABLE'], lineConfiguration['RESOLUTION']))
        self.dataRequestCreated.emit(moduleRequestIndex, self._buildDataRequest(self.configuration['TIME'].copy(), lineConfiguration['MODULE_OBJECT'], lineConfiguration['MODULE_VARIABLE'], lineConfiguration['RESOLUTION']))

    def setConfiguration(self, configuration):
        self.destroyDataRequest()
        for item in self.plotItems:
            self.plot.removePolarItem(item)
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
            argumentIndex, moduleIndex = line.get('ARGUMENT_REQUEST_ID'), line.get('MODULE_REQUEST_ID')
            argumentUpdated, moduleUpdated = argumentIndex in updatedRequestIndices, moduleIndex in updatedRequestIndices
            argumentDefined, moduleDefined = line.get('ARGUMENT_VARIABLE') is not None, line.get('MODULE_VARIABLE') is not None
            plotItem = self.plotItems[i]
            if argumentUpdated and moduleUpdated:
                argumentPlotData, modulePlotData = newPlotData.get(argumentIndex), newPlotData.get(moduleIndex)
                if argumentPlotData is None or modulePlotData is None:
                    self.plot.updatePolar(plotItem, [], [])
                    continue
                argumentValues, moduleValues = argumentPlotData.get("VALUES", []), modulePlotData.get("VALUES", [])
                nbDataPoints = min(len(argumentValues), len(moduleValues))
                if nbDataPoints == 0:
                    self.plot.updatePolar(plotItem, [], [])
                    continue
                argumentValues = np.degrees(argumentValues)
                argumentCleanDataValues, moduleCleanDataValues = [], []
                for argument, module in zip(argumentValues[:nbDataPoints], moduleValues[:nbDataPoints]):
                    if argument is None or module is None:
                        continue
                    argumentCleanDataValues.append(argument)
                    moduleCleanDataValues.append(module)
                self.plot.updatePolar(plotItem, moduleCleanDataValues, argumentCleanDataValues)
            elif argumentUpdated or moduleUpdated:
                self.plot.updatePolar(plotItem, [], [])
            else:
                if argumentDefined and moduleDefined:
                    continue
                else:
                    self.plot.updatePolar(plotItem, [], [])

    @staticmethod
    def _buildDataRequest(timeConfiguration, objectIndex, variable, resolution):
        return {'TIME': timeConfiguration, 'OBJECT': objectIndex, 'VARIABLE': variable, 'RESOLUTION': resolution}

    def createDataRequest(self):
        for line in self.configuration['LINES']:
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('ARGUMENT_OBJECT'), line.get('ARGUMENT_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestCreated.emit(line.get('ARGUMENT_REQUEST_ID'), request)
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('MODULE_OBJECT'), line.get('MODULE_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestCreated.emit(line.get('MODULE_REQUEST_ID'), request)

    def updateDataRequest(self):
        for line in self.configuration['LINES']:
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('ARGUMENT_OBJECT'), line.get('ARGUMENT_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestUpdated.emit(line.get('ARGUMENT_REQUEST_ID'), request)
            request = self._buildDataRequest(self.configuration['TIME'].copy(), line.get('MODULE_OBJECT'), line.get('MODULE_VARIABLE'), line.get('RESOLUTION'))
            self.dataRequestUpdated.emit(line.get('MODULE_REQUEST_ID'), request)

    def destroyDataRequest(self):
        for line in self.configuration['LINES']:
            if line.get('ARGUMENT_REQUEST_ID'):
                self.dataRequestDestroyed.emit(line.get('ARGUMENT_REQUEST_ID'))
            if line.get('MODULE_REQUEST_ID'):
                self.dataRequestDestroyed.emit(line.get('MODULE_REQUEST_ID'))

    def closeEvent(self, event):
        self.destroyDataRequest()
        super().closeEvent(event)


class PolarPlotSettingsWidget(QWidget):
    def __init__(self, polarPlot: PolarPlot, dockWidget=None, parent=None):
        super().__init__(parent)
        self.polarPlot = polarPlot
        self.polarPlot.activeObjectsChanged.connect(self.refreshObjectCombos)
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
        if self.polarPlot.configuration['TIME']['MODE'] == 'REAL':
            self.realTimeRadio.setChecked(True)
        elif self.polarPlot.configuration['TIME']['MODE'] == 'FIXED':
            self.fixedTimeRadio.setChecked(True)
        else:
            self.polarPlot.configuration['TIME']['MODE'] = 'REAL'
            self.realTimeRadio.setChecked(True)
        self.realTimeRadio.toggled.connect(self.setTimeMode)
        timeModeLayout = QHBoxLayout()
        timeModeLayout.addWidget(self.realTimeRadio)
        timeModeLayout.addWidget(self.fixedTimeRadio)
        self.beforeRealTimeSpinBox = QDoubleSpinBox()
        self.beforeRealTimeSpinBox.setRange(0, 1e6)
        self.beforeRealTimeSpinBox.setDecimals(2)
        self.beforeRealTimeSpinBox.setValue(self.polarPlot.configuration['TIME']['BEFORE'])
        self.beforeRealTimeSpinBox.valueChanged.connect(self._beforeChanged)
        self.beforeRealTimeUnitComboBox = QComboBox()
        self.beforeRealTimeUnitComboBox.addItems(['seconds', 'minutes', 'hours', 'days', 'orbital periods'])
        self.beforeRealTimeUnitComboBox.setCurrentText(self.polarPlot.configuration['TIME']['BEFORE_UNIT'])
        self.beforeRealTimeUnitComboBox.currentTextChanged.connect(self._beforeUnitChanged)
        beforeRealTimeLayout = QHBoxLayout()
        beforeRealTimeLayout.addWidget(self.beforeRealTimeSpinBox)
        beforeRealTimeLayout.addWidget(self.beforeRealTimeUnitComboBox)
        self.afterRealTimeSpinBox = QDoubleSpinBox()
        self.afterRealTimeSpinBox.setRange(0, 1e6)
        self.afterRealTimeSpinBox.setDecimals(2)
        self.afterRealTimeSpinBox.setValue(self.polarPlot.configuration['TIME']['AFTER'])
        self.afterRealTimeSpinBox.valueChanged.connect(self._afterChanged)
        self.afterRealTimeUnitComboBox = QComboBox()
        self.afterRealTimeUnitComboBox.addItems(['seconds', 'minutes', 'hours', 'days', 'orbital periods'])
        self.afterRealTimeUnitComboBox.setCurrentText(self.polarPlot.configuration['TIME']['AFTER_UNIT'])
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
        startTimeString = self.polarPlot.configuration['TIME']['START']
        if startTimeString:
            dt = QDateTime.fromString(startTimeString, Qt.ISODate)
            if dt.isValid():
                self.startTimeEdit.setDateTime(dt)
        self.startTimeEdit.dateTimeChanged.connect(self._startChanged)
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setCalendarPopup(True)
        self.endTimeEdit.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        endTimeString = self.polarPlot.configuration['TIME']['END']
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
        self.polarPlot.addLine()
        self.updateLinesList()
        self.polarPlot.updateDataRequest()

    def removeSelectedLine(self):
        row = self.listWidget.currentRow()
        if row < 0 or row >= len(self.polarPlot.plotItems):
            return
        line = self.polarPlot.configuration['LINES'][row]
        if line.get('X_REQUEST_ID'):
            self.polarPlot.dataRequestDestroyed.emit(line.get('X_REQUEST_ID'))
        if line.get('Y_REQUEST_ID'):
            self.polarPlot.dataRequestDestroyed.emit(line.get('Y_REQUEST_ID'))
        self.polarPlot.configuration['LINES'].pop(row)
        item = self.polarPlot.plotItems.pop(row)
        self.polarPlot.plot.removePolarItem(item)
        self.updateLinesList()

    def updateLinesList(self):
        self.listWidget.clear()
        while self.stackedWidget.count() > 0:
            widget = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(widget)
            widget.deleteLater()
        for lineConfiguration in self.polarPlot.configuration['LINES']:
            self.listWidget.addItem(lineConfiguration['NAME'])
            settingsPage = PolarLineSettingsPage(line=lineConfiguration, polarPlot=self.polarPlot, owner=self)
            settingsPage.nameChanged.connect(lambda text, l=lineConfiguration: self.updateLineName(l, text))
            self.stackedWidget.addWidget(settingsPage)

    def updateLineName(self, line, text):
        line['NAME'] = text
        row = self.polarPlot.configuration['LINES'].index(line)
        item = self.polarPlot.plotItems[row]
        plotItem = self.polarPlot.plot.getPlotItem()
        legend = getattr(plotItem, 'legend', None)
        if legend is not None:
            legend.removeItem(item)
            legend.addItem(item, text)
        self.listWidget.item(row).setText(text)

    def refreshObjectCombos(self):
        for i in range(self.stackedWidget.count()):
            page = self.stackedWidget.widget(i)
            if isinstance(page, PolarLineSettingsPage):
                page.fillObjectCombo(page.argumentObjectComboBox)
                page.fillObjectCombo(page.moduleObjectComboBox)

    def setTimeMode(self, mode):
        self.polarPlot.configuration['TIME']['MODE'] = 'REAL' if self.realTimeRadio.isChecked() else 'FIXED'
        self.timeStackedWidget.setCurrentIndex(0 if self.realTimeRadio.isChecked() else 1)
        if self.fixedTimeRadio.isChecked():
            now = datetime.utcnow()
            timeConfiguration = self.polarPlot.configuration['TIME']
            if not timeConfiguration.get('START'):
                start = now - timedelta(minutes=30)
                self.polarPlot.configuration['TIME']['START'] = start.isoformat()
            if not timeConfiguration.get('END'):
                end = now + timedelta(minutes=30)
                self.polarPlot.configuration['TIME']['END'] = end.isoformat()
            self.startTimeEdit.setDateTime(QDateTime.fromString(timeConfiguration['START'], Qt.ISODate))
            self.endTimeEdit.setDateTime(QDateTime.fromString(timeConfiguration['END'], Qt.ISODate))
        self.polarPlot.updateDataRequest()

    def _beforeChanged(self, value):
        self.polarPlot.configuration['TIME']['BEFORE'] = value
        self.polarPlot.updateDataRequest()

    def _beforeUnitChanged(self, text):
        self.polarPlot.configuration['TIME']['BEFORE_UNIT'] = text
        self.polarPlot.updateDataRequest()

    def _afterChanged(self, value):
        self.polarPlot.configuration['TIME']['AFTER'] = value
        self.polarPlot.updateDataRequest()

    def _afterUnitChanged(self, text):
        self.polarPlot.configuration['TIME']['AFTER_UNIT'] = text
        self.polarPlot.updateDataRequest()

    def _startChanged(self, dt):
        self.polarPlot.configuration['TIME']['START'] = dt.toString(Qt.ISODate)
        self.polarPlot.updateDataRequest()

    def _endChanged(self, dt):
        self.polarPlot.configuration['TIME']['END'] = dt.toString(Qt.ISODate)
        self.polarPlot.updateDataRequest()

class PolarLineSettingsPage(QWidget):
    nameChanged = pyqtSignal(str)

    def __init__(self, line: dict, polarPlot: PolarPlot, parent=None, owner=None):
        super().__init__(parent)
        self.line = line
        self.polarPlot = polarPlot
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

        # ARGUMENT & MODULE AXES SETTINGS
        self.argumentGroup = QGroupBox('Argument')
        self.argumentObjectComboBox = QComboBox()
        self.fillObjectCombo(self.argumentObjectComboBox)
        index = self.argumentObjectComboBox.findData(self.line['ARGUMENT_OBJECT'])
        self.argumentObjectComboBox.setCurrentIndex(index if index != -1 else 0)
        self.argumentVariableComboBox = QComboBox()
        self._fillVariableCombo(self.argumentVariableComboBox, self.argumentObjectComboBox)
        index = self.argumentVariableComboBox.findData(self.line['ARGUMENT_VARIABLE'])
        self.argumentVariableComboBox.setCurrentIndex(index if index != -1 else 0)
        self.argumentVariableComboBox.currentTextChanged.connect(self._updateVariableX)
        self.argumentObjectComboBox.currentTextChanged.connect(self._updateObjectX)
        argumentLayout = QFormLayout(self.argumentGroup)
        argumentLayout.addRow('Object:', self.argumentObjectComboBox)
        argumentLayout.addRow('Variable:', self.argumentVariableComboBox)
        self.moduleGroup = QGroupBox('Module')
        self.moduleObjectComboBox = QComboBox()
        self.fillObjectCombo(self.moduleObjectComboBox)
        index = self.moduleObjectComboBox.findData(self.line['MODULE_OBJECT'])
        self.moduleObjectComboBox.setCurrentIndex(index if index != -1 else 0)
        self.moduleVariableComboBox = QComboBox()
        self._fillVariableCombo(self.moduleVariableComboBox, self.moduleObjectComboBox)
        index = self.moduleVariableComboBox.findData(self.line['MODULE_VARIABLE'])
        self.moduleVariableComboBox.setCurrentIndex(index if index != -1 else 0)
        self.moduleVariableComboBox.currentTextChanged.connect(self._updateVariableY)
        self.moduleObjectComboBox.currentTextChanged.connect(self._updateObjectY)
        moduleLayout = QFormLayout(self.moduleGroup)
        moduleLayout.addRow('Object:', self.moduleObjectComboBox)
        moduleLayout.addRow('Variable:', self.moduleVariableComboBox)
        self.axesGroup = QGroupBox('Axes Settings')
        self.resolutionSpinBox = QSpinBox()
        self.resolutionSpinBox.setRange(2, 10000)
        self.resolutionSpinBox.setValue(self.line.get('RESOLUTION', 361))
        self.resolutionSpinBox.setToolTip("Number of points used to compute the line")
        self.resolutionSpinBox.valueChanged.connect(self._updateResolution)
        resolutionLayout = QFormLayout()
        resolutionLayout.addRow("Resolution:", self.resolutionSpinBox)
        axesLayout = QVBoxLayout(self.axesGroup)
        axesLayout.addWidget(self.argumentGroup)
        axesLayout.addWidget(self.moduleGroup)
        axesLayout.addLayout(resolutionLayout)

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
        row = self.polarPlot.configuration['LINES'].index(self.line)
        self.polarPlot.plotItems[row].setPen(pen)

    def _updateStyle(self, index):
        style = self.styleComboBox.itemData(index)
        self.line['STYLE'] = style
        pen = mkPen(QColor(self.line['COLOR']), width=self.line['WIDTH'], style=style)
        row = self.polarPlot.configuration['LINES'].index(self.line)
        self.polarPlot.plotItems[row].setPen(pen)

    def _pickColor(self):
        color = QColorDialog.getColor(QColor(self.line['COLOR']))
        if not color.isValid():
            return
        self._setButtonColor(self.colorButton, color.getRgb()[:3])
        self.colorLabel.setText(color.name().upper())
        self.line['COLOR'] = color.name()
        pen = mkPen(color, width=self.line['WIDTH'], style=self.line['STYLE'])
        row = self.polarPlot.configuration['LINES'].index(self.line)
        self.polarPlot.plotItems[row].setPen(pen)

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
        activeObjects = self.polarPlot.activeObjects
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

    def _updateObjectX(self, text):
        self._fillVariableCombo(self.argumentVariableComboBox, self.argumentObjectComboBox)
        self.line['ARGUMENT_OBJECT'] = self.argumentObjectComboBox.currentData()
        self.argumentVariableComboBox.setEnabled(self.argumentObjectComboBox.currentData() is not None)
        self.polarPlot.updateDataRequest()

    def _updateObjectY(self, text):
        self._fillVariableCombo(self.moduleVariableComboBox, self.moduleObjectComboBox)
        self.line['MODULE_OBJECT'] = self.moduleObjectComboBox.currentData()
        self.moduleVariableComboBox.setEnabled(self.moduleObjectComboBox.currentData() is not None)
        self.polarPlot.updateDataRequest()

    def _updateVariableX(self, text):
        self.line['ARGUMENT_VARIABLE'] = self.argumentVariableComboBox.currentData()
        self.polarPlot.updateDataRequest()

    def _updateVariableY(self, text):
        self.line['MODULE_VARIABLE'] = self.moduleVariableComboBox.currentData()
        self.polarPlot.updateDataRequest()

    def _updateResolution(self, value):
        self.line['RESOLUTION'] = value
        self.polarPlot.updateDataRequest()


class PolarGraph(PlotWidget):
    def __init__(self, parent=None, ringCount=5, angularStep=30, maximumRadius=100.0, bgColor=QColor(0, 0, 0), gridColor=QColor(220, 220, 220), labelColor=QColor(240, 240, 240), shaded=True, shadeColor=QColor(30, 30, 50, 120), zoomFactor=0.85):
        super().__init__(parent)
        self.ringCount, self.angularStep, self.maximumRadius, self.zoomFactor = ringCount, angularStep, maximumRadius, zoomFactor
        self.bgColor, self.gridColor, self.labelColor, self.shaded, self.shadeColor = bgColor, gridColor, labelColor, shaded, shadeColor
        self._polarItems = []
        self._autoScale = True
        self.setBackground(self.bgColor)
        for axis in ('left', 'right', 'top', 'bottom'):
            self.getPlotItem().hideAxis(axis)
        self.getPlotItem().setMenuEnabled(False)
        viewBox = self.getViewBox()
        viewBox.setDefaultPadding(0.0)
        viewBox.setAspectLocked(True, ratio=1.0)
        viewBox.disableAutoRange()
        viewBox.setMouseMode(pg.ViewBox.PanMode)
        self.polarGrid = PolarGridItem(self)
        self.polarGrid.setFlag(self.polarGrid.GraphicsItemFlag.ItemHasNoContents, False)
        self.addItem(self.polarGrid)
        self.getViewBox().addedItems.remove(self.polarGrid)
        self._applyRange()
        viewBox.sigRangeChanged.connect(self._onRangeChanged)
        self.getPlotItem().autoBtn.clicked.connect(self._onAutoScaleClicked)
        polarGraphReference = self
        originalDragEvent = viewBox.mouseDragEvent
        def _dragInterceptor(event, axis=None):
            polarGraphReference._autoScale = False
            originalDragEvent(event, axis)
        viewBox.mouseDragEvent = _dragInterceptor

    def _onAutoScaleClicked(self):
        self._autoScale = True
        validRadii = [float(np.max(arrayRadius)) for _, arrayRadius, _ in self._polarItems if arrayRadius.size > 0]
        maximumRadius = max(validRadii) if validRadii else self.maximumRadius
        self.maximumRadius = upperBoundary(maximumRadius)
        self._applyRange()

    def autoRange(self, *args, **kwargs):
        self._onAutoScaleClicked()

    def _applyRange(self):
        radius = self.maximumRadius * 1.15
        viewBox = self.getViewBox()
        viewBox.setRange(xRange=(-radius, radius), yRange=(-radius, radius), padding=0, disableAutoRange=True)
        self.polarGrid.reDraw()
        self._rePlotAll()
    
    def _rePlotAll(self):
        for plotItem, arrayRadius, arrayAngle in self._polarItems:
            if arrayRadius.size == 0:
                plotItem.setData([], [])
            else:
                xData, yData = self._polarToCartesian(arrayRadius, arrayAngle)
                plotItem.setData(xData, yData)
    
    @staticmethod
    def _polarToCartesian(radiusArray, angleArray):
        angleArray = np.deg2rad(angleArray)
        return radiusArray * np.cos(angleArray), radiusArray * np.sin(angleArray)
    
    def _onRangeChanged(self):
        self.polarGrid.update()

    def wheelEvent(self, event):
        self._autoScale = False
        delta = event.angleDelta().y()
        if delta > 0:
            self.maximumRadius = max(1e-9, self.maximumRadius * self.zoomFactor)
        else:
            self.maximumRadius = max(1e-9, self.maximumRadius / self.zoomFactor)
        self._applyRange()
        event.accept()

    def plotPolar(self, radiusArray, angleArray, **kwargs):
        radiusArray, angleArray = np.asarray(radiusArray, dtype=float), np.asarray(angleArray, dtype=float)
        xData, yData = self._polarToCartesian(radiusArray, angleArray)
        plotDataItem = self.plot(xData, yData, **kwargs)
        self._polarItems.append((plotDataItem, radiusArray, angleArray))
        if self._autoScale:
            self._onAutoScaleClicked()
        return plotDataItem

    def updatePolar(self, item, radiusArray, angleArray):
        radiusArray, angleArray = np.asarray(radiusArray, dtype=float), np.asarray(angleArray, dtype=float)
        xData, yData = self._polarToCartesian(radiusArray, angleArray)
        item.setData(xData, yData)
        for i, (plotDataItem, _, _) in enumerate(self._polarItems):
            if plotDataItem == item:
                self._polarItems[i] = (plotDataItem, radiusArray, angleArray)
                break
        if self._autoScale:
            self._onAutoScaleClicked()

    def autoScalePolar(self):
        self._onAutoScaleClicked()

    def removePolarItem(self, item):
        self._polarItems = [t for t in self._polarItems if t[0] is not item]
        self.removeItem(item)

    def clearPolar(self):
        for item, _, _ in self._polarItems:
            self.removeItem(item)
        self._polarItems.clear()

    def setRadialRange(self, maximumRadius):
        self.maximumRadius = float(maximumRadius)
        self._applyRange()

    def setAngularStep(self, angularStep):
        self.angularStep = angularStep
        self.polarGrid.reDraw()

    def setRingCount(self, ringCount):
        self.ringCount = ringCount
        self.polarGrid.reDraw()

    def setShaded(self, shaded, color=None):
        self.shaded = shaded
        if color is not None:
            self.shadeColor = color
        self.polarGrid.reDraw()


class PolarGridItem(GraphicsObject):
    def __init__(self, polarGraph: PolarGraph):
        super().__init__()
        self._pg = polarGraph
        self.setZValue(-100)

    def boundingRect(self):
        radius = self._pg.maximumRadius
        return QRectF(-1.25 * radius, - 1.25 * radius, 2.5 * radius, 2.5 * radius)

    def reDraw(self):
        self.prepareGeometryChange()
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        pgRef = self._pg
        maximumRadius, ringCount, angleStep, shaded = pgRef.maximumRadius, pgRef.ringCount, pgRef.angularStep, pgRef.shaded
        bgColor, gridColor, labelColor, shadeColor = pgRef.bgColor, pgRef.gridColor, pgRef.labelColor, pgRef.shadeColor
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bgColor))
        painter.drawEllipse(QPointF(0, 0), maximumRadius, maximumRadius)
        if shaded:
            for i in range(0, 360, 2 * angleStep):
                path, startAngle, endAngle, steps = QPainterPath(), np.radians(i), np.radians(i + angleStep), max(8, angleStep)
                path.moveTo(0, 0)
                for s in range(steps + 1):
                    angle = startAngle + s / steps * (endAngle - startAngle)
                    path.lineTo(maximumRadius * np.cos(angle), maximumRadius * np.sin(angle))
                path.closeSubpath()
                painter.setBrush(QBrush(shadeColor))
                painter.setPen(Qt.NoPen)
                painter.drawPath(path)
        pen = QPen(gridColor)
        pen.setCosmetic(True)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        for i in range(1, ringCount + 1):
            radius = i / ringCount * maximumRadius
            painter.drawEllipse(QPointF(0, 0), radius, radius)
        outerPen = QPen(gridColor)
        outerPen.setCosmetic(True)
        outerPen.setWidth(2)
        painter.setPen(outerPen)
        painter.drawEllipse(QPointF(0, 0), maximumRadius, maximumRadius)
        spokePen = QPen(gridColor)
        spokePen.setCosmetic(True)
        spokePen.setWidth(1)
        painter.setPen(spokePen)
        for angleDegrees in range(0, 360, angleStep):
            angle = np.radians(angleDegrees)
            x, y = maximumRadius * np.cos(angle), maximumRadius * np.sin(angle)
            painter.drawLine(QPointF(0, 0), QPointF(x, y))
        painterTransform = painter.transform()
        sx, sy = np.sqrt(painterTransform.m11() ** 2 + painterTransform.m21() ** 2), np.sqrt(painterTransform.m12() ** 2 + painterTransform.m22() ** 2)
        if sx == 0:
            sx = 1.0
        if sy == 0:
            sy = 1.0
        radialFont = QFont()
        radialFont.setPixelSize(12)
        painter.setFont(radialFont)
        painter.setPen(QPen(labelColor))
        fontMetrics = painter.fontMetrics()
        textHeight = fontMetrics.height()
        for i in range(1, ringCount + 1):
            radius = i / ringCount * maximumRadius
            text = str(int(round(radius))) if abs(radius - round(radius)) < 1e-9 else f'{radius:.3g}'
            textWidth = fontMetrics.horizontalAdvance(text)
            dx, dy = radius + maximumRadius * 0.01, 0
            screenPoint = painterTransform.map(QPointF(dx, dy))
            painter.save()
            painter.resetTransform()
            painter.setFont(radialFont)
            painter.setPen(QPen(labelColor))
            painter.drawText(QPointF(screenPoint.x(), screenPoint.y() - textHeight * 0.15), text)
            painter.restore()
        angularLabelRadius = maximumRadius * 1.09
        angularFont = QFont()
        angularFont.setPixelSize(12)
        for angleDegrees in range(0, 360, angleStep):
            dx, dy = angularLabelRadius * np.cos(np.radians(angleDegrees)), angularLabelRadius * np.sin(np.radians(angleDegrees))
            text = f'{angleDegrees}°'
            textWidth = fontMetrics.horizontalAdvance(text)
            screenPoint = painterTransform.map(QPointF(dx, dy))
            painter.save()
            painter.resetTransform()
            painter.setFont(angularFont)
            painter.setPen(QPen(labelColor))
            painter.drawText(QPointF(screenPoint.x() - textWidth / 2, screenPoint.y() + textHeight / 3), text)
            painter.restore()
