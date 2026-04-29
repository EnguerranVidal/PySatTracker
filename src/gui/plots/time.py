from datetime import datetime, timedelta
from pyqtgraph import PlotWidget, mkPen
import pyqtgraph as pg
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
from PyQt5.QtWidgets import *

from src.core.objects import ActiveObjectsModel
from src.core.engine.orbitalEngine import OrbitalMechanicsEngine


class TimeSeriesPlot(QWidget):
    activeObjectsChanged = pyqtSignal()
    dataRequestCreated = pyqtSignal(int, dict)
    dataRequestUpdated = pyqtSignal(int, dict)
    dataRequestDestroyed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot = PlotWidget(axisItems={'bottom': pg.DateAxisItem(orientation='bottom')})
        self.plot.addLegend()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot)
        self.lastPositions = None
        self.activeObjects = None
        self.configuration = {'SERIES': []}
        self.plotItems = []
        self.requestIndexProvider = None

    def addSeries(self, name=None, color='#ffffff', width=3, style=Qt.SolidLine, seriesConfiguration=None):
        if name is None:
            name = f"Series {len(self.configuration['SERIES']) + 1}"
        colorName = QColor(color).name()
        requestIndex = self.requestIndexProvider()
        if seriesConfiguration is None:
            seriesConfiguration = {'NAME': name, 'COLOR': colorName, 'WIDTH': width, 'STYLE': style, 'OBJECT': None, 'VARIABLE': None, 'RESOLUTION': 361, 'REQUEST_ID': requestIndex,
                                 'TIME': {'MODE': 'REAL', 'BEFORE': 30.0, 'BEFORE_UNIT': 'minutes', 'AFTER': 30.0, 'AFTER_UNIT': 'minutes', 'START': None, 'END': None}}
            self.configuration['SERIES'].append(seriesConfiguration)
        seriesConfiguration['REQUEST_ID'] = requestIndex
        pen = mkPen(QColor(colorName), width=width, style=style)
        item = self.plot.plot([], [], pen=pen, name=name)
        self.plotItems.append(item)
        self.dataRequestCreated.emit(requestIndex, self._buildDataRequest(seriesConfiguration['TIME'].copy(), seriesConfiguration['OBJECT'], seriesConfiguration['VARIABLE'], seriesConfiguration['RESOLUTION']))

    def setConfiguration(self, configuration):
        self.destroyDataRequest()
        for item in self.plotItems:
            self.plot.removeItem(item)
        self.plotItems = []
        self.configuration = configuration.copy()
        for seriesConfiguration in self.configuration['SERIES']:
            name = seriesConfiguration.get('NAME', f"Series {len(self.plotItems) + 1}")
            color = seriesConfiguration.get('COLOR', '#ffffff')
            width = seriesConfiguration.get('WIDTH', 1)
            style = seriesConfiguration.get('STYLE', Qt.SolidLine)
            self.addSeries(name=name, color=color, width=width, style=style, seriesConfiguration=seriesConfiguration)

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects
        self.activeObjectsChanged.emit()

    def updateData(self, positions: dict):
        self.lastPositions = positions
        newPlotData = positions.get('PLOT_VIEW', {}).get('REQUESTS', {})
        if not newPlotData:
            return
        self._updatePlotItems(newPlotData)

    def _updatePlotItems(self, newPlotData):
        updatedRequestIndices = set(newPlotData.keys())
        for i, series in enumerate(self.configuration['SERIES']):
            requestId = series.get('REQUEST_ID')
            variableDefined = series.get('VARIABLE') is not None
            plotItem = self.plotItems[i]
            if requestId in updatedRequestIndices:
                plotData = newPlotData.get(requestId)
                if not plotData:
                    plotItem.setData([], [])
                    continue
                times = plotData.get("TIME", [])
                values = plotData.get("VALUES", [])
                nbDataPoints = min(len(times), len(values))
                if nbDataPoints == 0:
                    plotItem.setData([], [])
                    continue
                xClean = []
                yClean = []
                for t, v in zip(times[:nbDataPoints], values[:nbDataPoints]):
                    if t is None or v is None:
                        continue
                    if isinstance(t, datetime):
                        t = t.timestamp()
                    xClean.append(t)
                    yClean.append(v)
                plotItem.setData(xClean, yClean)
            else:
                if variableDefined:
                    continue
                else:
                    plotItem.setData([], [])

    @staticmethod
    def _buildDataRequest(timeConfiguration, objectIndex, variable, resolution):
        return {'TIME': timeConfiguration, 'OBJECT': objectIndex, 'VARIABLE': variable, 'RESOLUTION': resolution}

    def createDataRequest(self):
        for series in self.configuration['SERIES']:
            request = self._buildDataRequest(series['TIME'].copy(), series.get('OBJECT'), series.get('VARIABLE'), series.get('RESOLUTION'))
            self.dataRequestCreated.emit(series.get('REQUEST_ID'), request)

    def updateDataRequest(self):
        for series in self.configuration['SERIES']:
            request = self._buildDataRequest(series['TIME'].copy(), series.get('OBJECT'), series.get('VARIABLE'), series.get('RESOLUTION'))
            self.dataRequestUpdated.emit(series.get('REQUEST_ID'), request)

    def destroyDataRequest(self):
        for series in self.configuration['SERIES']:
            if series.get('REQUEST_ID'):
                self.dataRequestDestroyed.emit(series.get('REQUEST_ID'))

    def closeEvent(self, event):
        self.destroyDataRequest()
        super().closeEvent(event)


class TimeSeriesSettingsWidget(QWidget):
    def __init__(self, timePlot: TimeSeriesPlot, dockWidget=None, parent=None):
        super().__init__(parent)
        self.timePlot = timePlot
        self.timePlot.activeObjectsChanged.connect(self.refreshObjectCombos)
        self.dockWidget = dockWidget

        # PLOT NAME EDITOR
        self.titleEdit = QLineEdit()
        if self.dockWidget is not None:
            self.titleEdit.setText(self.dockWidget.windowTitle())
        self.titleEdit.textChanged.connect(self._updateDockTitle)
        self.titleLayout = QHBoxLayout()
        self.titleLayout.addWidget(QLabel("Plot Name:"))
        self.titleLayout.addWidget(self.titleEdit)

        # SERIES MANAGEMENT
        self.addButton = QPushButton('Add Series')
        self.removeButton = QPushButton('Remove Series')
        self.addButton.clicked.connect(self.addNewSeries)
        self.removeButton.clicked.connect(self.removeSelectedSeries)
        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.addWidget(self.addButton)
        self.buttonLayout.addWidget(self.removeButton)
        self.listWidget = QListWidget(self)
        self.stackedWidget = QStackedWidget(self)
        self.listWidget.currentRowChanged.connect(self.stackedWidget.setCurrentIndex)

        # MAIN LAYOUT
        mainLayout = QVBoxLayout(self)
        mainLayout.addLayout(self.titleLayout)
        mainLayout.addLayout(self.buttonLayout)
        mainLayout.addWidget(self.listWidget)
        mainLayout.addWidget(self.stackedWidget)
        self.updateSeriesList()

    def _updateDockTitle(self):
        if self.dockWidget is not None:
            self.dockWidget.setWindowTitle(self.titleEdit.text())

    def addNewSeries(self):
        self.timePlot.addSeries()
        self.updateSeriesList()
        self.timePlot.updateDataRequest()

    def removeSelectedSeries(self):
        row = self.listWidget.currentRow()
        if row < 0 or row >= len(self.timePlot.plotItems):
            return
        series = self.timePlot.configuration['SERIES'][row]
        if series.get('REQUEST_ID'):
            self.timePlot.dataRequestDestroyed.emit(series.get('REQUEST_ID'))
        self.timePlot.configuration['SERIES'].pop(row)
        item = self.timePlot.plotItems.pop(row)
        self.timePlot.plot.removeItem(item)
        self.updateSeriesList()

    def updateSeriesList(self):
        self.listWidget.clear()
        while self.stackedWidget.count() > 0:
            widget = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(widget)
            widget.deleteLater()
        for seriesConfiguration in self.timePlot.configuration['SERIES']:
            self.listWidget.addItem(seriesConfiguration['NAME'])
            settingsPage = TimeSeriesSettingsPage(owner=self, timeSeries=seriesConfiguration, timePlot=self.timePlot)
            settingsPage.nameChanged.connect(lambda text, l=seriesConfiguration: self.updateSeriesName(l, text))
            self.stackedWidget.addWidget(settingsPage)

    def updateSeriesName(self, series, text):
        series['NAME'] = text
        row = self.timePlot.configuration['SERIES'].index(series)
        item = self.timePlot.plotItems[row]
        plotItem = self.timePlot.plot.getPlotItem()
        legend = getattr(plotItem, 'legend', None)
        if legend is not None:
            legend.removeItem(item)
            legend.addItem(item, text)
        self.listWidget.item(row).setText(text)

    def refreshObjectCombos(self):
        for i in range(self.stackedWidget.count()):
            page = self.stackedWidget.widget(i)
            if isinstance(page, TimeSeriesSettingsPage):
                page.fillObjectCombo(page.objectComboBox)


class TimeSeriesSettingsPage(QWidget):
    nameChanged = pyqtSignal(str)

    def __init__(self, timeSeries: dict, timePlot: TimeSeriesPlot, parent=None, owner=None):
        super().__init__(parent)
        self.timeSeries = timeSeries
        self.timePlot = timePlot
        self.owner = owner if owner is not None else parent
        orbitalEngine = OrbitalMechanicsEngine()
        self.engineVariables = orbitalEngine.getAvailableVariables()
        # GENERAL SERIES SETTINGS
        self.generalGroup = QGroupBox(f"General {self.timeSeries['NAME']} Settings")
        self.nameEdit = QLineEdit(self.timeSeries['NAME'])
        self.nameEdit.textChanged.connect(self._updateName)
        self.colorLabel = QLabel(QColor(self.timeSeries['COLOR']).name().upper())
        self.colorButton = self._colorButton()
        self._setButtonColor(self.colorButton, QColor(self.timeSeries['COLOR']).getRgb()[:3])
        self.colorButton.clicked.connect(self._pickColor)
        colorLayout = QHBoxLayout()
        colorLayout.setContentsMargins(0, 0, 0, 0)
        colorLayout.addWidget(self.colorButton)
        colorLayout.addWidget(self.colorLabel)
        self.widthSpinBox = QSpinBox()
        self.widthSpinBox.setRange(1, 10)
        self.widthSpinBox.setValue(self.timeSeries['WIDTH'])
        self.widthSpinBox.valueChanged.connect(self._updateWidth)
        self.styleComboBox = QComboBox()
        self.styleComboBox.addItem('Solid', Qt.SolidLine)
        self.styleComboBox.addItem('Dash', Qt.DashLine)
        self.styleComboBox.addItem('Dot', Qt.DotLine)
        self.styleComboBox.addItem('Dash Dot', Qt.DashDotLine)
        self.styleComboBox.setCurrentIndex(self.styleComboBox.findData(self.timeSeries['STYLE']))
        self.styleComboBox.currentIndexChanged.connect(self._updateStyle)
        generalLayout = QFormLayout(self.generalGroup)
        generalLayout.addRow('Name:', self.nameEdit)
        generalLayout.addRow('Color:', colorLayout)
        generalLayout.addRow('Width:', self.widthSpinBox)
        generalLayout.addRow('Style:', self.styleComboBox)

        # VARIABLE SETTINGS
        self.variableGroup = QGroupBox('Series Variable')
        self.objectComboBox = QComboBox()
        self.fillObjectCombo(self.objectComboBox)
        index = self.objectComboBox.findData(self.timeSeries['OBJECT'])
        self.objectComboBox.setCurrentIndex(index if index != -1 else 0)
        self.variableComboBox = QComboBox()
        self._fillVariableCombo(self.variableComboBox, self.objectComboBox)
        index = self.variableComboBox.findData(self.timeSeries['VARIABLE'])
        self.variableComboBox.setCurrentIndex(index if index != -1 else 0)
        self.variableComboBox.currentTextChanged.connect(self._updateVariable)
        self.objectComboBox.currentTextChanged.connect(self._updateObject)
        self.resolutionSpinBox = QSpinBox()
        self.resolutionSpinBox.setRange(2, 10000)
        self.resolutionSpinBox.setValue(self.timeSeries.get('RESOLUTION', 361))
        self.resolutionSpinBox.setToolTip("Number of points used to compute the timeSeries")
        self.resolutionSpinBox.valueChanged.connect(self._updateResolution)
        variableLayout = QFormLayout(self.variableGroup)
        variableLayout.addRow('Object:', self.objectComboBox)
        variableLayout.addRow('Variable:', self.variableComboBox)
        variableLayout.addRow('Resolution:', self.resolutionSpinBox)

        # TIME SETTINGS
        self.timeGroup = QGroupBox('Time Settings')
        self.realTimeRadio = QRadioButton('Real Time')
        self.fixedTimeRadio = QRadioButton('Fixed Time')
        if self.timeSeries['TIME']['MODE'] == 'REAL':
            self.realTimeRadio.setChecked(True)
        elif self.timeSeries['TIME']['MODE'] == 'FIXED':
            self.fixedTimeRadio.setChecked(True)
        else:
            self.timeSeries['TIME']['MODE'] = 'REAL'
            self.realTimeRadio.setChecked(True)
        self.realTimeRadio.toggled.connect(self.setTimeMode)
        timeModeLayout = QHBoxLayout()
        timeModeLayout.addWidget(self.realTimeRadio)
        timeModeLayout.addWidget(self.fixedTimeRadio)
        self.beforeRealTimeSpinBox = QDoubleSpinBox()
        self.beforeRealTimeSpinBox.setRange(0, 1e6)
        self.beforeRealTimeSpinBox.setDecimals(2)
        self.beforeRealTimeSpinBox.setValue(self.timeSeries['TIME']['BEFORE'])
        self.beforeRealTimeSpinBox.valueChanged.connect(self._beforeChanged)
        self.beforeRealTimeUnitComboBox = QComboBox()
        self.beforeRealTimeUnitComboBox.addItems(['seconds', 'minutes', 'hours', 'days', 'orbital periods'])
        self.beforeRealTimeUnitComboBox.setCurrentText(self.timeSeries['TIME']['BEFORE_UNIT'])
        self.beforeRealTimeUnitComboBox.currentTextChanged.connect(self._beforeUnitChanged)
        beforeRealTimeLayout = QHBoxLayout()
        beforeRealTimeLayout.addWidget(self.beforeRealTimeSpinBox)
        beforeRealTimeLayout.addWidget(self.beforeRealTimeUnitComboBox)
        self.afterRealTimeSpinBox = QDoubleSpinBox()
        self.afterRealTimeSpinBox.setRange(0, 1e6)
        self.afterRealTimeSpinBox.setDecimals(2)
        self.afterRealTimeSpinBox.setValue(self.timeSeries['TIME']['AFTER'])
        self.afterRealTimeSpinBox.valueChanged.connect(self._afterChanged)
        self.afterRealTimeUnitComboBox = QComboBox()
        self.afterRealTimeUnitComboBox.addItems(['seconds', 'minutes', 'hours', 'days', 'orbital periods'])
        self.afterRealTimeUnitComboBox.setCurrentText(self.timeSeries['TIME']['AFTER_UNIT'])
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
        startTimeString = self.timeSeries['TIME']['START']
        if startTimeString:
            dt = QDateTime.fromString(startTimeString, Qt.ISODate)
            if dt.isValid():
                self.startTimeEdit.setDateTime(dt)
        self.startTimeEdit.dateTimeChanged.connect(self._startChanged)
        self.endTimeEdit = QDateTimeEdit()
        self.endTimeEdit.setCalendarPopup(True)
        self.endTimeEdit.setDisplayFormat('yyyy-MM-dd HH:mm:ss')
        endTimeString = self.timeSeries['TIME']['END']
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

        layout = QVBoxLayout(self)
        layout.addWidget(self.generalGroup)
        layout.addWidget(self.variableGroup)
        layout.addWidget(self.timeGroup)

    def _updateName(self, text):
        self.timeSeries['NAME'] = text
        self.generalGroup.setTitle(f"General {self.timeSeries['NAME']} Settings")
        self.nameChanged.emit(text)

    def _updateWidth(self, value):
        self.timeSeries['WIDTH'] = value
        pen = mkPen(QColor(self.timeSeries['COLOR']), width=value, style=self.timeSeries['STYLE'])
        row = self.timePlot.configuration['SERIES'].index(self.timeSeries)
        self.timePlot.plotItems[row].setPen(pen)

    def _updateStyle(self, index):
        style = self.styleComboBox.itemData(index)
        self.timeSeries['STYLE'] = style
        pen = mkPen(QColor(self.timeSeries['COLOR']), width=self.timeSeries['WIDTH'], style=style)
        row = self.timePlot.configuration['SERIES'].index(self.timeSeries)
        self.timePlot.plotItems[row].setPen(pen)

    def _pickColor(self):
        color = QColorDialog.getColor(QColor(self.timeSeries['COLOR']))
        if not color.isValid():
            return
        self._setButtonColor(self.colorButton, color.getRgb()[:3])
        self.colorLabel.setText(color.name().upper())
        self.timeSeries['COLOR'] = color.name()
        pen = mkPen(color, width=self.timeSeries['WIDTH'], style=self.timeSeries['STYLE'])
        row = self.timePlot.configuration['SERIES'].index(self.timeSeries)
        self.timePlot.plotItems[row].setPen(pen)

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
        activeObjects = self.timePlot.activeObjects
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

    def _updateObject(self, text):
        self._fillVariableCombo(self.variableComboBox, self.objectComboBox)
        self.timeSeries['OBJECT'] = self.objectComboBox.currentData()
        self.variableComboBox.setEnabled(self.objectComboBox.currentData() is not None)
        self.timePlot.updateDataRequest()

    def _updateVariable(self, text):
        self.timeSeries['VARIABLE'] = self.variableComboBox.currentData()
        self.timePlot.updateDataRequest()

    def _updateResolution(self, value):
        self.timeSeries['RESOLUTION'] = value
        self.timePlot.updateDataRequest()

    def setTimeMode(self, mode):
        self.timeSeries['TIME']['MODE'] = 'REAL' if self.realTimeRadio.isChecked() else 'FIXED'
        self.timeStackedWidget.setCurrentIndex(0 if self.realTimeRadio.isChecked() else 1)
        if self.fixedTimeRadio.isChecked():
            now = datetime.utcnow()
            timeConfiguration = self.timeSeries['TIME']
            if not timeConfiguration.get('START'):
                start = now - timedelta(minutes=30)
                self.timeSeries['TIME']['START'] = start.isoformat()
            if not timeConfiguration.get('END'):
                end = now + timedelta(minutes=30)
                self.timeSeries['TIME']['END'] = end.isoformat()
            self.startTimeEdit.setDateTime(QDateTime.fromString(timeConfiguration['START'], Qt.ISODate))
            self.endTimeEdit.setDateTime(QDateTime.fromString(timeConfiguration['END'], Qt.ISODate))
        self.timePlot.updateDataRequest()

    def _beforeChanged(self, value):
        self.timeSeries['TIME']['BEFORE'] = value
        self.timePlot.updateDataRequest()

    def _beforeUnitChanged(self, text):
        self.timeSeries['TIME']['BEFORE_UNIT'] = text
        self.timePlot.updateDataRequest()

    def _afterChanged(self, value):
        self.timeSeries['TIME']['AFTER'] = value
        self.timePlot.updateDataRequest()

    def _afterUnitChanged(self, text):
        self.timeSeries['TIME']['AFTER_UNIT'] = text
        self.timePlot.updateDataRequest()

    def _startChanged(self, dt):
        self.timeSeries['TIME']['START'] = dt.toString(Qt.ISODate)
        self.timePlot.updateDataRequest()

    def _endChanged(self, dt):
        self.timeSeries['TIME']['END'] = dt.toString(Qt.ISODate)
        self.timePlot.updateDataRequest()