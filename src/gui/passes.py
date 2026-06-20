from PyQt5.QtCore import Qt, pyqtSignal, QObject, pyqtSlot
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel


class VisiblePassesWidget(QMainWindow):
    passesRequest = pyqtSignal(list)

    def __init__(self, parent=None, currentDir:str = None):
        super().__init__(parent)
        self.currentDir = currentDir
        self.viewWidget = VisiblePassesViewWidget(self)
        self.setCentralWidget(self.viewWidget)
        self.settingsDockWidget = VisiblePassesSettingsWidget(self)
        self.settingsDockWidget.passesRequest.connect(self._requestPasses)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.settingsDockWidget)

    def _requestPasses(self, settings: dict):
        self.passesRequest.emit(settings)


class VisiblePassesSettingsWidget(QDockWidget):
    passesRequest = pyqtSignal(dict)

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
        self.locationLongitudeLineEdit = QLineEdit()
        self.locationLatitudeLineEdit = QLineEdit()
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
        pass

    def _onSettingsChanged(self):
        pass

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


class VisiblePassesViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)


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

    def _updateCoordinatesFromMap(self, latitude: float, longitude: float):
        self.latitudeLineEdit.setText(f"{latitude:.6f}")
        self.longitudeLineEdit.setText(f"{longitude:.6f}")
        self.selectedLongitude, self.selectedLatitude = longitude, latitude

    def accept(self):
        try:
            latitude = float(self.latitudeLineEdit.text().strip())
            longitude = float(self.longitudeLineEdit.text().strip())
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
            self.selectedLatitude, self.selectedLongitude = latitude, longitude
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
            latitude = float(coordinates.get('lat', 0))
            longitude = float(coordinates.get('lon', 0))
            self.coordinatesChanged.emit(latitude, longitude)
        except Exception:
            pass