from PyQt5.QtCore import Qt, pyqtSignal, QObject, pyqtSlot, QThreadPool
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel

from src.gui.passes.requests import VisiblePassesRequest, VisiblePassesCalculationTask


class VisiblePassesWidget(QMainWindow):
    def __init__(self, parent=None, currentDir:str = None, tleDatabase=None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.tleDatabase = tleDatabase
        self.threadPool = QThreadPool.globalInstance()
        self.threadPool.setMaxThreadCount(4)
        self.viewWidget = VisiblePassesViewWidget(self)
        self.setCentralWidget(self.viewWidget)
        self.settingsDockWidget = VisiblePassesSettingsWidget(self)
        self.settingsDockWidget.passesRequest.connect(self._requestPasses)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.settingsDockWidget)
        self.viewWidget.showDefault()

    def setTleDatabase(self, tleDatabase=None):
        self.tleDatabase = tleDatabase if tleDatabase is not None else self.tleDatabase

    def _requestPasses(self, passRequest: VisiblePassesRequest):
        total = 0
        if self.tleDatabase is not None and self.tleDatabase.dataFrame is not None:
            total = len(self.tleDatabase.dataFrame)
        self.viewWidget.showProgress(total=max(total, 1))
        task = VisiblePassesCalculationTask(passRequest, self.tleDatabase)
        task.signals.progress.connect(self.viewWidget.updateProgress)
        task.signals.result.connect(self._onCalculationsDone)
        self.threadPool.start(task)

    def _onCalculationsDone(self, results: list):
        self.settingsDockWidget.resetFindButton()
        if results:
            self.viewWidget.showResults(results)
        else:
            self.viewWidget.showDefault()
            QMessageBox.information(self, "Result", "No passes found.")


class VisiblePassesSettingsWidget(QDockWidget):
    passesRequest = pyqtSignal(VisiblePassesRequest)

    def __init__(self, parent=None):
        super().__init__("Pass Request Settings", parent)
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
        mainLayout.addWidget(self.timeSpanGroupBox)
        mainLayout.addWidget(self.findVisiblePassesButton)
        mainLayout.addStretch()
        self.setWidget(content)

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

    def _getRequest(self):
        request = VisiblePassesRequest(
            longitude=float(self.locationLongitudeLineEdit.text() or -74.0060),
            latitude=float(self.locationLatitudeLineEdit.text() or 40.7128),
            timeSpan=self.timeSpanButtonGroup.checkedButton().text() if self.timeSpanButtonGroup.checkedButton() else "Tonight"
        )
        return request


class VisiblePassesViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stackedWidget = QStackedWidget(self)
        self.defaultPage = QWidget()
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

        # VISIBLE PASSES RESULTS PAGE
        self.resultsPage = QWidget()
        self.resultsLabel = QLabel("Results will appear here...")
        self.resultsLabel.setAlignment(Qt.AlignCenter)
        resultsLayout = QVBoxLayout(self.resultsPage)
        resultsLayout.addWidget(self.resultsLabel)
        self.stackedWidget.addWidget(self.resultsPage)

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
        self.stackedWidget.setCurrentIndex(2)


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
