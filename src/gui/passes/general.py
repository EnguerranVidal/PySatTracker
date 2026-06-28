import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QThreadPool
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel

from src.gui.passes.plot import VisiblePassSkyPlot
from src.gui.passes.requests import VisiblePassesRequest, VisiblePassesCalculationTask


class VisiblePassesWidget(QMainWindow):
    passesConfigChanged = pyqtSignal()

    def __init__(self, parent=None, currentDir:str = None, tleDatabase=None, passesConfig=None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.tleDatabase = tleDatabase
        self.passesConfig = passesConfig
        self.threadPool = QThreadPool.globalInstance()
        self.threadPool.setMaxThreadCount(4)
        self.viewWidget = VisiblePassesViewWidget(self)
        self.setCentralWidget(self.viewWidget)
        self.settingsDockWidget = VisiblePassesSettingsWidget(self, passesConfig=self.passesConfig)
        self.settingsDockWidget.passesRequest.connect(self._requestPasses)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.settingsDockWidget)
        self.viewWidget.showDefault()

    def setTleDatabase(self, tleDatabase=None):
        self.tleDatabase = tleDatabase if tleDatabase is not None else self.tleDatabase

    def setPassesConfig(self, passesConfig):
        self.passesConfig = passesConfig
        self.settingsDockWidget.passesConfig = passesConfig
        self.settingsDockWidget.applyConfig(passesConfig)

    def _requestPasses(self, passRequest: VisiblePassesRequest):
        total = 0
        if self.tleDatabase is not None and self.tleDatabase.dataFrame is not None:
            total = len(self.tleDatabase.dataFrame)
        self.viewWidget.showProgress(total=max(total, 1))
        task = VisiblePassesCalculationTask(passRequest, self.tleDatabase)
        task.signals.progress.connect(self.viewWidget.updateProgress)
        task.signals.result.connect(self._onCalculationsDone)
        self.threadPool.start(task)
        self.passesConfigChanged.emit()

    def _onCalculationsDone(self, results: list):
        self.settingsDockWidget.resetFindButton()
        if results:
            self.viewWidget.showResults(results)
        else:
            self.viewWidget.showDefault()
            QMessageBox.information(self, "Result", "No passes found.")


class VisiblePassCard(QFrame):
    clicked = pyqtSignal(object)

    def __init__(self, visiblePass, parent=None):
        super().__init__(parent)
        self.visiblePass = visiblePass
        self.setCursor(Qt.PointingHandCursor)
        self.setFrameShape(QFrame.StyledPanel)
        title = QLabel(visiblePass.objectName)
        title.setStyleSheet("font-weight: bold;")
        subtitle = QLabel(f"{visiblePass.startTime:%Y-%m-%d %H:%M:%S} UTC - "f"{visiblePass.endTime:%H:%M:%S} UTC")
        details = QLabel(
            f"Max elevation: {visiblePass.maxElevation:.1f} deg | "
            f"Avg mag: {visiblePass.magnitude:.1f} | "
            f"Duration: {visiblePass.duration // 60}m {visiblePass.duration % 60:02d}s"
        )
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(title)
        mainLayout.addWidget(subtitle)
        mainLayout.addWidget(details)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.visiblePass)
        super().mousePressEvent(event)


class VisiblePassesSettingsWidget(QDockWidget):
    passesRequest = pyqtSignal(VisiblePassesRequest)

    def __init__(self, parent=None, passesConfig=None):
        super().__init__("Pass Request Settings", parent)
        self.passesConfig = passesConfig
        self.setFeatures(QDockWidget.DockWidgetMovable)  # No floating, no closing
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.findVisiblePassesButton = QPushButton("Find Visible Passes")
        self.findVisiblePassesButton.setMinimumHeight(50)
        self.findVisiblePassesButton.clicked.connect(self._onFindClicked)
        # LOCATION GROUP BOX
        self.locationGroupBox = QGroupBox("Location")
        self.setLocationButton = QPushButton("Set Location")
        self.setLocationButton.setMinimumWidth(110)
        self.setLocationButton.clicked.connect(self._openLocationDialog)
        self.locationLongitudeLineEdit = QLineEdit("-74.0060")
        self.locationLatitudeLineEdit = QLineEdit("40.7128")
        locationLayout = QHBoxLayout()
        locationLayout.addWidget(self.setLocationButton)
        locationLayout.addWidget(self.locationLongitudeLineEdit)
        locationLayout.addWidget(self.locationLatitudeLineEdit)
        self.locationGroupBox.setLayout(locationLayout)
        # LOCATION TYPE GROUP BOX
        self.locationTypeGroupBox = QGroupBox("Location Type")
        self.locationTypeButtonGroup = QButtonGroup()
        self.locationTypeButtonGroup.setExclusive(True)
        self.cityButton = QPushButton("City")
        self.countrysideButton = QPushButton("Countryside")
        self.cityButton.setCheckable(True)
        self.countrysideButton.setCheckable(True)
        self.cityButton.setChecked(True)
        self.locationTypeButtonGroup.addButton(self.cityButton)
        self.locationTypeButtonGroup.addButton(self.countrysideButton)
        locationTypeLayout = QHBoxLayout()
        locationTypeLayout.addWidget(self.cityButton)
        locationTypeLayout.addWidget(self.countrysideButton)
        self.locationTypeGroupBox.setLayout(locationTypeLayout)
        # TIME SPAN GROUP BOX
        self.timeSpanGroupBox = QGroupBox("Time Span")
        self.timeSpanButtonGroup = QButtonGroup()
        self.timeSpanButtonGroup.setExclusive(True)
        self.tonightButton = QPushButton("Tonight")
        self.oneDayButton = QPushButton("Next 24 hours")
        self.twoDayButton = QPushButton("Next 48 hours")
        self.tonightButton.setCheckable(True)
        self.oneDayButton.setCheckable(True)
        self.twoDayButton.setCheckable(True)
        self.timeSpanButtonGroup.addButton(self.tonightButton)
        self.timeSpanButtonGroup.addButton(self.oneDayButton)
        self.timeSpanButtonGroup.addButton(self.twoDayButton)
        self.tonightButton.setChecked(True)
        timeLayout = QHBoxLayout()
        timeLayout.addWidget(self.tonightButton)
        timeLayout.addWidget(self.oneDayButton)
        timeLayout.addWidget(self.twoDayButton)
        self.timeSpanGroupBox.setLayout(timeLayout)
        # MAIN LAYOUT
        content = QWidget()
        mainLayout = QVBoxLayout(content)
        mainLayout.addWidget(self.locationGroupBox)
        mainLayout.addWidget(self.locationTypeGroupBox)
        mainLayout.addWidget(self.timeSpanGroupBox)
        mainLayout.addWidget(self.findVisiblePassesButton)
        mainLayout.addStretch()
        self.setWidget(content)
        self.applyConfig(self.passesConfig)

    def applyConfig(self, config):
        if config is None:
            return
        self.locationLongitudeLineEdit.setText(f"{config.lastLongitude:.6f}")
        self.locationLatitudeLineEdit.setText(f"{config.lastLatitude:.6f}")
        if config.locationType == "Countryside":
            self.countrysideButton.setChecked(True)
        else:
            self.cityButton.setChecked(True)
        for button in self.timeSpanButtonGroup.buttons():
            if button.text() == config.lastTimeSpan:
                button.setChecked(True)
                break

    def updateConfigFromUi(self):
        if self.passesConfig is None:
            return
        self.passesConfig.lastLongitude = float(self.locationLongitudeLineEdit.text() or -74.0060)
        self.passesConfig.lastLatitude = float(self.locationLatitudeLineEdit.text() or 40.7128)
        self.passesConfig.lastTimeSpan = self.timeSpanButtonGroup.checkedButton().text() if self.timeSpanButtonGroup.checkedButton() else "Tonight"
        self.passesConfig.locationType = "City" if self.cityButton.isChecked() else "Countryside"
        self.passesConfig.minMagnitude = 3.0 if self.cityButton.isChecked() else 6.0

    def _onFindClicked(self):
        try:
            request = self._getRequest()
            self.findVisiblePassesButton.setEnabled(False)
            self.findVisiblePassesButton.setText("Computing...")
            self.passesRequest.emit(request)
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Request", str(e))

    def resetFindButton(self):
        self.findVisiblePassesButton.setEnabled(True)
        self.findVisiblePassesButton.setText("Find Visible Passes")

    def _openLocationDialog(self):
        try:
            initialLatitude = float(self.locationLatitudeLineEdit.text() or 40.7128)
            initialLongitude = float(self.locationLongitudeLineEdit.text() or -74.0060)
        except ValueError:
            initialLatitude, initialLongitude = 40.7128, -74.0060
        dialog = SetLocationDialog(initialLatitude, initialLongitude, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.locationLatitudeLineEdit.setText(f"{dialog.selectedLatitude:.6f}")
            self.locationLongitudeLineEdit.setText(f"{dialog.selectedLongitude:.6f}")
            self.updateConfigFromUi()

    def _getRequest(self):
        self.updateConfigFromUi()
        if self.passesConfig is not None:
            return self.passesConfig.toRequest()
        minMagnitude = 3 if self.cityButton.isChecked() else 6
        request = VisiblePassesRequest(
            longitude=float(self.locationLongitudeLineEdit.text() or -74.0060),
            latitude=float(self.locationLatitudeLineEdit.text() or 40.7128),
            timeSpan=self.timeSpanButtonGroup.checkedButton().text() if self.timeSpanButtonGroup.checkedButton() else "Tonight",
            minMagnitude=minMagnitude,
            maxPasses=100,
        )
        return request


class VisiblePassesViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.results = []
        self.stackedWidget = QStackedWidget(self)

        # DEFAULT PAGE
        self.defaultPage = QLabel("No visible passes computed.")
        self.defaultPage.setAlignment(Qt.AlignCenter)
        self.stackedWidget.addWidget(self.defaultPage)

        # CALCULATION TASK PROGRESS BAR
        self.progressPage = QWidget()
        self.progressLabel = QLabel("Computing visible passes...")
        self.progressLabel.setAlignment(Qt.AlignCenter)
        self.progressLabel.setStyleSheet("font-size: 16px;")
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setMinimumHeight(25)
        progressLayout = QVBoxLayout(self.progressPage)
        progressLayout.setAlignment(Qt.AlignCenter)
        progressLayout.addWidget(self.progressLabel)
        progressLayout.addWidget(self.progressBar)
        progressLayout.addStretch()
        self.stackedWidget.addWidget(self.progressPage)

        # RESULTS CARDS PAGE
        self.resultsPage = QWidget()
        self.cardsContainer = QWidget()
        self.cardsLayout = QVBoxLayout(self.cardsContainer)
        self.cardsLayout.setContentsMargins(8, 8, 8, 8)
        self.cardsLayout.setSpacing(8)
        self.cardsLayout.addStretch()
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.cardsContainer)
        resultsLayout = QVBoxLayout(self.resultsPage)
        resultsLayout.setContentsMargins(0, 0, 0, 0)
        resultsLayout.addWidget(self.scrollArea)
        self.stackedWidget.addWidget(self.resultsPage)

        # GRAPH PAGE
        self.graphPage = QWidget()
        self.backButton = QPushButton("Back to passes")
        self.backButton.clicked.connect(self.showResultsPage)
        self.passInfoLabel = QLabel()
        self.passInfoLabel.setAlignment(Qt.AlignCenter)
        self.skyPlot = VisiblePassSkyPlot()
        graphHeaderLayout = QHBoxLayout()
        graphHeaderLayout.addWidget(self.backButton, 0)
        graphHeaderLayout.addWidget(self.passInfoLabel, 1)
        graphLayout = QVBoxLayout(self.graphPage)
        graphLayout.addLayout(graphHeaderLayout)
        graphLayout.addWidget(self.skyPlot, 1)
        self.stackedWidget.addWidget(self.graphPage)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(self.stackedWidget)

    def showDefault(self):
        self.stackedWidget.setCurrentIndex(0)

    def showProgress(self, total: int = 100):
        self.stackedWidget.setCurrentIndex(1)
        self.progressBar.setRange(0, total)
        self.progressBar.setValue(0)

    def updateProgress(self, value: int):
        self.progressBar.setValue(value)

    def showResults(self, results: list = None):
        self.results = results or []
        self._clearPassCards()
        for visiblePass in self.results:
            card = VisiblePassCard(visiblePass)
            card.clicked.connect(self.showPassGraph)
            self.cardsLayout.insertWidget(self.cardsLayout.count() - 1, card)
        self.showResultsPage()

    def showResultsPage(self):
        self.stackedWidget.setCurrentWidget(self.resultsPage)

    def showPassGraph(self, visiblePass):
        self._plotPass(visiblePass)
        self.stackedWidget.setCurrentWidget(self.graphPage)

    def _clearPassCards(self):
        while self.cardsLayout.count() > 1:
            item = self.cardsLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _plotPass(self, visiblePass):
        self.skyPlot.setPass(visiblePass.azimuths, visiblePass.elevations)
        self.passInfoLabel.setText(
            f"{visiblePass.objectName} | "
            f"{visiblePass.startTime:%H:%M:%S} - {visiblePass.endTime:%H:%M:%S} UTC | "
            f"Max Elevation {visiblePass.maxElevation:.1f} deg | "
            f"Avg Magnitude {visiblePass.magnitude:.1f}"
        )


class SetLocationDialog(QDialog):
    def __init__(self, initialLatitude=40.7128, initialLongitude=-74.0060, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Location")
        self.setFixedSize(850, 650)
        self.selectedLongitude, self.selectedLatitude = initialLongitude, initialLatitude
        self.mapHandler = MapHandler()
        self.mapHandler.coordinatesChanged.connect(self._updateCoordinatesFromMap)
        self.mapView = QWebEngineView()
        self.mapView.setMinimumHeight(550)
        self.latitudeLineEdit = QLineEdit(str(self.selectedLatitude))
        self.longitudeLineEdit = QLineEdit(str(self.selectedLongitude))
        coordinatesLayout = QGridLayout()
        coordinatesLayout.addWidget(QLabel("Longitude"), 0, 0)
        coordinatesLayout.addWidget(self.longitudeLineEdit, 1, 0, 1, 1)
        coordinatesLayout.addWidget(QLabel("Latitude"), 0, 1, 1, 1)
        coordinatesLayout.addWidget(self.latitudeLineEdit, 1, 1, 1, 1)
        self.acceptButton = QPushButton("Ok")
        self.cancelButton = QPushButton("Cancel")
        self.acceptButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        bottomButtonLayout = QHBoxLayout()
        bottomButtonLayout.addWidget(self.acceptButton)
        bottomButtonLayout.addWidget(self.cancelButton)
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(self.mapView)
        mainLayout.addLayout(coordinatesLayout)
        mainLayout.addLayout(bottomButtonLayout)
        self._loadMap()

    def _loadMap(self):
        html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
                    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
                    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
                    <style>
                        html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
                    </style>
                </head>
                <body>
                    <div id="map"></div>
                    <script>
                        var map, marker;

                        function initMap() {{
                            map = L.map('map', {{ zoomControl: true }}).setView([{self.selectedLatitude}, {self.selectedLongitude}], 8);

                            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                                attribution: '&copy; OpenStreetMap contributors',
                                maxZoom: 19
                            }}).addTo(map);

                            marker = L.marker([{self.selectedLatitude}, {self.selectedLongitude}])
                                .addTo(map)
                                .bindPopup("Click anywhere on the map").openPopup();

                            map.on('click', function(e) {{
                                var lat = e.latlng.lat.toFixed(6);
                                var lon = e.latlng.lng.toFixed(6);
                                marker.setLatLng([lat, lon]);

                                // Send to Python via WebChannel
                                if (window.qtHandler) {{
                                    window.qtHandler.setCoordinates(JSON.stringify({{lat: lat, lon: lon}}));
                                }}
                            }});
                        }}

                        // Setup Qt WebChannel
                        new QWebChannel(qt.webChannelTransport, function(channel) {{
                            window.qtHandler = channel.objects.mapHandler;
                            initMap();
                        }});
                    </script>
                </body>
                </html>
                """
        self.mapView.setHtml(html)
        self.channel = QWebChannel()
        self.channel.registerObject("mapHandler", self.mapHandler)
        self.mapView.page().setWebChannel(self.channel)

    def _updateCoordinatesFromMap(self, longitude: float, latitude: float):
        self.longitudeLineEdit.setText(f"{longitude:.6f}")
        self.latitudeLineEdit.setText(f"{latitude:.6f}")
        self.selectedLongitude, self.selectedLatitude = longitude, latitude

    def accept(self):
        try:
            longitude, latitude = float(self.longitudeLineEdit.text().strip()), float(self.latitudeLineEdit.text().strip())
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                raise ValueError
            self.selectedLongitude, self.selectedLatitude = longitude, latitude
            super().accept()
        except ValueError:
            QMessageBox.warning(self, "Invalid Coordinates", "Please enter valid latitude (-90 to 90) and longitude (-180 to 180).")


class MapHandler(QObject):
    coordinatesChanged = pyqtSignal(float, float)

    @pyqtSlot(str)
    def setCoordinates(self, data: str):
        try:
            import json
            coordinates = json.loads(data)
            longitude, latitude = float(coordinates.get('lon', 0)), float(coordinates.get('lat', 0))
            self.coordinatesChanged.emit(longitude, latitude)
        except Exception:
            pass
