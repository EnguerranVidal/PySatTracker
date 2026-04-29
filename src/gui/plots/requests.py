from datetime import datetime, timedelta
import numpy as np
from PyQt5.QtCore import Qt, QObject, QTimer, pyqtSignal, pyqtSlot, QMetaObject, Q_ARG, QThreadPool, QRunnable
from PyQt5.QtWidgets import *

from src.core.engine.orbitalEngine import OrbitalMechanicsEngine


class PlotRequestManager(QObject):
    resultReady = pyqtSignal(dict)  # aggregated results

    def __init__(self, tleDatabase, variableRegistry):
        super().__init__()
        self.tleDatabase, self.variableRegistry = tleDatabase, variableRegistry
        self.requests, self.results = {}, {}
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(4)

    def create(self, requestId: int, request: dict):
        self.requests[requestId] = request
        if self._isFixed(request):
            self._submitTask(requestId, datetime.utcnow())

    def update(self, requestId: int, request: dict):
        self.requests[requestId] = request
        if self._isFixed(request):
            self._submitTask(requestId, datetime.utcnow())

    def submitAllFixed(self):
        for requestId in self.requests:
            if self._isFixed(self.requests[requestId]):
                self._submitTask(requestId, datetime.utcnow())

    def remove(self, requestId: int):
        self.requests.pop(requestId, None)
        self.results.pop(requestId, None)

    def tick(self, simulationTime: datetime):
        for requestId, request in self.requests.items():
            if self._isReal(request):
                self._submitTask(requestId, simulationTime)

    def _submitTask(self, requestId, simulationTime):
        request = self.requests[requestId]
        task = PlotCalculationTask(requestId, request, self.tleDatabase, self.variableRegistry, simulationTime, self._handleResultThreadSafe)
        self.pool.start(task)

    def _handleResultThreadSafe(self, requestId, result):
        QMetaObject.invokeMethod(self, "_onWorkerResult", Qt.QueuedConnection, Q_ARG(int, requestId), Q_ARG(dict, result))

    @pyqtSlot(int, dict)
    def _onWorkerResult(self, requestId: int, result: dict):
        self.results[requestId] = result
        self.resultReady.emit({"REQUESTS": self.results.copy()})

    @staticmethod
    def _isFixed(request):
        return request.get("TIME", {}).get("MODE") == "FIXED"

    @staticmethod
    def _isReal(request):
        return request.get("TIME", {}).get("MODE") == "REAL"

    def getAllItems(self):
        return self.requests.items()


class PlotCalculationTask(QRunnable):
    def __init__(self, requestId: int, request: dict, tleDatabase, variableRegistry, simulationTime, callback):
        super().__init__()
        self.requestId = requestId
        self.request = request
        self.tleDatabase, self.variableRegistry = tleDatabase, variableRegistry
        self.simulationTime = simulationTime
        self.callback = callback
        self.engine = OrbitalMechanicsEngine()

    def run(self):
        if not self._isValidRequest() or self.tleDatabase is None:
            return
        julianDates, fractions = self.buildRequestTimeArray(self.simulationTime)
        values = self._computeValues(julianDates, fractions)
        fullJulianDates = julianDates + fractions
        times = self.engine.julianDateArrayToDatetimeArray(fullJulianDates)
        result = {"TIME": times, "VALUES": values}
        self.callback(self.requestId, result)

    def buildRequestTimeArray(self, simulationTime: datetime):
        if self.request['OBJECT'] is None:
            satObject = None
        else:
            satObject = self.tleDatabase.getSatrec(self.request['OBJECT'])
        timeScales = {'seconds': 1, 'minutes': 60, 'hours': 3600, 'days': 86400, 'orbital periods': self.engine.orbitalPeriod(satObject) if satObject else 1}
        if self.request['TIME']['MODE'] == 'FIXED':
            startDateTime, endDateTime = self.request['TIME'].get('START'), self.request['TIME'].get('END')
            if isinstance(startDateTime, str):
                startDateTime = datetime.fromisoformat(startDateTime)
            if isinstance(endDateTime, str):
                endDateTime = datetime.fromisoformat(endDateTime)
        else:
            beforeDuration, beforeDurationUnit = self.request['TIME']['BEFORE'], self.request['TIME']['BEFORE_UNIT']
            afterDuration, afterDurationUnit = self.request['TIME']['AFTER'], self.request['TIME']['AFTER_UNIT']
            startDateTime = simulationTime - timedelta(seconds=beforeDuration * timeScales[beforeDurationUnit])
            endDateTime = simulationTime + timedelta(seconds=afterDuration * timeScales[afterDurationUnit])
        return self.engine.datetimeToJulianDateArray(startDateTime, endDateTime, resolution=self.request["RESOLUTION"])

    def _isValidRequest(self):
        objectIndex, variableName, timeConfiguration = self.request.get('OBJECT'), self.request.get('VARIABLE'), self.request.get('TIME', {})
        if objectIndex is None or variableName is None:
            return False
        if timeConfiguration.get("MODE") == "FIXED":
            if not timeConfiguration.get("START") or not timeConfiguration.get("END"):
                return False
        return True

    def _computeValues(self, julianDates, fractions):
        satObject = None
        if self.request.get('OBJECT') is not None:
            satObject = self.tleDatabase.getSatrec(self.request['OBJECT'])
        variableName = self.request.get('VARIABLE').upper()
        fullJulianDates = julianDates + fractions
        state = self.engine.satelliteState(satObject, fullJulianDates)
        variable = self.variableRegistry.getVariable(variableName)
        if variable is None:
            return None
        values = variable.compute(self.engine, state, fullJulianDates)
        return values

class PlotRequestRegistryWindow(QTableWidget):
    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self.setWindowTitle("Plot Request Registry")
        self.resize(800, 300)
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels(["Request ID", "Object", "Variable", "Mode", "Before", "After", "Start", "End"])
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setAlternatingRowColors(True)
        self.refreshRegistryDisplay()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refreshRegistryDisplay)
        self.timer.start(1000)

    def refreshRegistryDisplay(self):
        self.setUpdatesEnabled(False)
        self.setRowCount(0)
        items = list(self.registry.getAllItems())
        for row, (requestId, request) in enumerate(items):
            self.insertRow(row)
            objectName, variableName, timeConfiguration = request.get("OBJECT"), request.get("VARIABLE"), request.get("TIME", {})
            beforeTime, afterTime = f"{timeConfiguration.get('BEFORE')} {timeConfiguration.get('BEFORE_UNIT')}", f"{timeConfiguration.get('AFTER')} {timeConfiguration.get('AFTER_UNIT')}"
            startTime, endTime = timeConfiguration.get("START"), timeConfiguration.get("END")
            values = [str(requestId), str(objectName), str(variableName), str(timeConfiguration.get("MODE")), beforeTime, afterTime, str(startTime), str(endTime)]
            for column, value in enumerate(values):
                self.setItem(row, column, QTableWidgetItem(value))
        self.setUpdatesEnabled(True)
        self.resizeRowsToContents()
