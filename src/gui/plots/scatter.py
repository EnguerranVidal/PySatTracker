from datetime import datetime, timedelta

import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, GraphicsObject
from PyQt5.QtGui import QColor, QPainter, QBrush, QPainterPath, QPen, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QRectF, QPointF
from PyQt5.QtWidgets import *

from src.core.objects import ActiveObjectsModel
from src.core.quantities import AngleQuantity
from src.gui.utilities import upperBoundary

from src.gui.plots.line import LinePlot, LinePlotSettingsWidget, LineSettingsPage


class ScatterPlot(LinePlot):
    def addLine(self, name=None, color='#ffffff', width=6, style=Qt.SolidLine, lineConfiguration=None):
        if name is None:
            name = f"Scatter {len(self.configuration['LINES']) + 1}"
        colorName = QColor(color).name()
        xRequestIndex = self.requestIndexProvider()
        yRequestIndex = self.requestIndexProvider()
        if lineConfiguration is None:
            lineConfiguration = {'NAME': name, 'COLOR': colorName, 'WIDTH': width, 'STYLE': style, 'X_OBJECT': None, 'X_VARIABLE': None, 'X_UNIT': None, 'Y_OBJECT': None, 'Y_VARIABLE': None, 'Y_UNIT': None, 'RESOLUTION': 361, 'X_REQUEST_ID': xRequestIndex, 'Y_REQUEST_ID': yRequestIndex}
            self.configuration['LINES'].append(lineConfiguration)
        else:
            lineConfiguration.setdefault('X_UNIT', self._defaultUnitKey(lineConfiguration.get('X_VARIABLE')))
            lineConfiguration.setdefault('Y_UNIT', self._defaultUnitKey(lineConfiguration.get('Y_VARIABLE')))
        lineConfiguration['X_REQUEST_ID'] = xRequestIndex
        lineConfiguration['Y_REQUEST_ID'] = yRequestIndex
        item = self.plot.plot([], [], pen=None, symbol='o', symbolSize=lineConfiguration.get('WIDTH', width), symbolBrush=QColor(lineConfiguration.get('COLOR', colorName)), symbolPen=mkPen(QColor(lineConfiguration.get('COLOR', colorName)), width=1), name=lineConfiguration.get('NAME', name))
        self.plotItems.append(item)
        self.dataRequestCreated.emit(xRequestIndex, self._buildDataRequest(self.configuration['TIME'].copy(), lineConfiguration.get('X_OBJECT'), lineConfiguration.get('X_VARIABLE'), lineConfiguration.get('RESOLUTION'), lineConfiguration.get('X_UNIT')))
        self.dataRequestCreated.emit(yRequestIndex, self._buildDataRequest(self.configuration['TIME'].copy(), lineConfiguration.get('Y_OBJECT'), lineConfiguration.get('Y_VARIABLE'), lineConfiguration.get('RESOLUTION'), lineConfiguration.get('Y_UNIT')))


class ScatterPlotSettingsWidget(LinePlotSettingsWidget):
    def __init__(self, scatterPlot: ScatterPlot, dockWidget=None, parent=None):
        super().__init__(scatterPlot, dockWidget=dockWidget, parent=parent)
        self.addButton.setText('Add Scatter')
        self.removeButton.setText('Remove Scatter')

    def updateLinesList(self):
        self.listWidget.clear()
        while self.stackedWidget.count() > 0:
            widget = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(widget)
            widget.deleteLater()
        for lineConfiguration in self.linePlot.configuration['LINES']:
            self.listWidget.addItem(lineConfiguration['NAME'])
            settingsPage = ScatterSettingsPage(owner=self, line=lineConfiguration, linePlot=self.linePlot,)
            settingsPage.nameChanged.connect(lambda text, l=lineConfiguration: self.updateLineName(l, text))
            self.stackedWidget.addWidget(settingsPage)


class ScatterSettingsPage(LineSettingsPage):
    def __init__(self, line: dict, linePlot: ScatterPlot, parent=None, owner=None):
        super().__init__(line=line, linePlot=linePlot, parent=parent, owner=owner)
        self.generalGroup.setTitle(f"General {self.line['NAME']} Scatter Settings")
        self.widthSpinBox.setRange(1, 40)
        self.widthSpinBox.setToolTip("Marker size")
        self.styleComboBox.setEnabled(False)

    def _updateWidth(self, value):
        self.line['WIDTH'] = value
        row = self.linePlot.configuration['LINES'].index(self.line)
        item = self.linePlot.plotItems[row]
        item.setSymbolSize(value)

    def _updateStyle(self, index):
        self.line['STYLE'] = self.styleComboBox.itemData(index)

    def _pickColor(self):
        color = QColorDialog.getColor(QColor(self.line['COLOR']))
        if not color.isValid():
            return
        self._setButtonColor(self.colorButton, color.getRgb()[:3])
        self.colorLabel.setText(color.name().upper())
        self.line['COLOR'] = color.name()
        row = self.linePlot.configuration['LINES'].index(self.line)
        item = self.linePlot.plotItems[row]
        item.setSymbolBrush(color)
        item.setSymbolPen(mkPen(color, width=1))
