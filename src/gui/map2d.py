import os

import numpy as np
import imageio
import pyqtgraph as pg
from pyqtgraph import GraphicsLayoutWidget

from PyQt5.QtCore import Qt, pyqtSignal, QSignalBlocker
from PyQt5.QtWidgets import *


class Map2dWidget(QWidget):
    objectSelected = pyqtSignal(list)
    ELEMENTS_Z_VALUES = {'SPOT': 30, 'LABEL': 40, 'FOOTPRINT': 20, 'GROUND_TRACK': 10, 'SUN': 50, 'NIGHT': 5, 'VERNAL': 100}

    def __init__(self, parent=None, mapImagePath='src/assets/earth/world_map.png'):
        super().__init__(parent)
        self.mapImagePath = mapImagePath
        self.objectSpots, self.objectGroundTracks, self.objectFootprints, self.objectArrows = {}, {}, {}, {}
        self.objectLabels = {}
        self._lastMouseScenePos = None
        self.selectedObject, self.hoveredObject, self.hoverRadius, self.displayConfiguration = None, None, 15, {}
        self.sunIndicator, self.nightLayer, self.vernalIndicator = None, None, None
        self._setupMap()

    def _setupMap(self):
        if not os.path.exists(self.mapImagePath):
            raise FileNotFoundError(f'Map image not found at {self.mapImagePath}')
        img = imageio.imread(self.mapImagePath)
        img = np.rot90(img, k=-1)
        self.mapImage = pg.ImageItem(img)
        self.mapWidth, self.mapHeight = self.mapImage.width(), self.mapImage.height()
        # SETUP WORLD MAP VIEW
        self.view = GraphicsLayoutWidget()
        self.view.setBackground('#202124')
        self.plot = self.view.addPlot()
        self.plot.addItem(self.mapImage)
        self.plot.setAspectLocked(True)
        self.plot.hideAxis('bottom')
        self.plot.hideAxis('left')
        self.plot.scene().sigMouseMoved.connect(self._onMouseMoved)
        self.view.setMouseTracking(True)
        self.view.viewport().setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)

    def _lonlatToCartesian(self, longitude, latitude):
        longitude, latitude = np.asarray(longitude), np.asarray(latitude)
        return (longitude + 180) / 360 * self.mapWidth, (latitude + 90) / 180 * self.mapHeight

    @staticmethod
    def _arrowAngle(x0, y0, x1, y1):
        return np.degrees(np.arctan2(y1 - y0, x1 - x0)) + 180

    @staticmethod
    def _splitWrapSegment(longitudes, latitudes, threshold=180):
        longitudes, latitudes = np.asarray(longitudes), np.asarray(latitudes)
        if longitudes.size < 2:
            return [(longitudes, latitudes)]
        diffLongitudes = np.diff(longitudes)
        jumps = np.abs(diffLongitudes) > threshold
        if not np.any(jumps):
            return [(longitudes, latitudes)]
        splitIndices = np.where(jumps)[0] + 1
        longitudeSegments = np.split(longitudes, splitIndices)
        latitudeSegments = np.split(latitudes, splitIndices)
        for k, index in enumerate(splitIndices):
            # LINEAR INTERPOLATION
            previousLongitude, nextLongitude = longitudes[index - 1], longitudes[index]
            previousLatitude, nextLatitude = latitudes[index - 1], latitudes[index]
            if previousLongitude > nextLongitude:
                longitudeA, longitudeB = previousLongitude, nextLongitude + 360
                latitudeA, latitudeB = previousLatitude, nextLatitude
                borderA, borderB = 180, -180
            else:
                longitudeA, longitudeB = nextLongitude + 360, previousLongitude
                latitudeA, latitudeB = nextLatitude, previousLatitude
                borderA, borderB = -180, 180
            a = (latitudeB - latitudeA) / (longitudeB - longitudeA)
            b = latitudeA - a * longitudeA
            latitudeBorder = a * 180 + b
            # ADDING BORDER POINTS TO SEGMENTS
            longitudeSegments[k] = np.append(longitudeSegments[k], borderA)
            latitudeSegments[k] = np.append(latitudeSegments[k], latitudeBorder)
            longitudeSegments[k + 1] = np.insert(longitudeSegments[k + 1], 0, borderB)
            latitudeSegments[k + 1] = np.insert(latitudeSegments[k + 1], 0, latitudeBorder)
        return list(zip(longitudeSegments, latitudeSegments))

    @staticmethod
    def _shouldRender(mode: str, isSelected: bool, isToggled: bool = True):
        if not isToggled:
            return False
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER

    def _updateSunAndNight(self, mapData, showSun=True, showNight=True, showVernal=True):
        if showNight:
            subPointLongitude, subPointLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
            longitudes, latitudes = mapData['NIGHT']['LONGITUDE'], mapData['NIGHT']['LATITUDE']
            x, y = self._lonlatToCartesian(longitudes, latitudes)
            fillLevel = 0 if subPointLatitude > 0 else self.mapHeight
            if self.nightLayer is None:
                self.nightLayer = pg.PlotCurveItem(x, y, pen=None, fillLevel=fillLevel, brush=pg.mkBrush(0, 0, 0, 120))
                self.nightLayer.setZValue(self.ELEMENTS_Z_VALUES['NIGHT'])
                self.plot.addItem(self.nightLayer)
            else:
                self.nightLayer.setData(x, y)
                self.nightLayer.setFillLevel(fillLevel)

        else:
            if self.nightLayer is not None:
                self.plot.removeItem(self.nightLayer)
                self.nightLayer = None
        if showSun:
            subPointLongitude, subPointLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
            xSun, ySun = self._lonlatToCartesian(subPointLongitude, subPointLatitude)
            if self.sunIndicator is None:
                self.sunIndicator = pg.ScatterPlotItem(size=14, brush=pg.mkBrush(255, 215, 0), pen=pg.mkPen(255, 200, 0, width=2), symbol="o",)
                self.sunIndicator.setZValue(self.ELEMENTS_Z_VALUES['SUN'])
                self.plot.addItem(self.sunIndicator)
            self.sunIndicator.setData([xSun], [ySun])
        else:
            if self.sunIndicator is not None:
                self.plot.removeItem(self.sunIndicator)
                self.sunIndicator = None
        if showVernal:
            vernalLongitude, vernalLatitude = mapData['VERNAL']['LONGITUDE'], mapData['VERNAL']['LATITUDE']
            xVernal, yVernal = self._lonlatToCartesian(vernalLongitude, vernalLatitude)
            if self.vernalIndicator is None:
                self.vernalIndicator = pg.ScatterPlotItem(size=15, brush=pg.mkBrush(0, 200, 0), pen=pg.mkPen(0, 255, 0, width=2), symbol="+",)
                self.vernalIndicator.setZValue(self.ELEMENTS_Z_VALUES['VERNAL'])
                self.plot.addItem(self.vernalIndicator)
            self.vernalIndicator.setData([xVernal], [yVernal])
        else:
            if self.vernalIndicator is not None:
                self.plot.removeItem(self.vernalIndicator)
                self.vernalIndicator = None

    def updateMap(self, positions: dict, visibleNorads: set[int], selectedNorad: int | None, displayConfiguration: dict):
        self.selectedObject, self.displayConfiguration = selectedNorad, displayConfiguration
        # REMOVING EVERYTHING NOT VISIBLE
        for noradIndex in list(self.objectSpots.keys()):
            if noradIndex not in visibleNorads:
                self._removeItems(self.objectSpots.pop(noradIndex))
                self._removeItems(self.objectGroundTracks.pop(noradIndex, None))
                self._removeItems(self.objectFootprints.pop(noradIndex, None))
                self._removeItems(self.objectArrows.pop(noradIndex, None))
                self._removeItems(self.objectLabels.pop(noradIndex, None))
        # NIGHT LAYER AND SUN POSITION
        self._updateSunAndNight(positions['2D_MAP'], self.displayConfiguration['SHOW_SUN'], self.displayConfiguration['SHOW_NIGHT'], self.displayConfiguration['SHOW_VERNAL'])
        # UPDATING/ADDING VISIBLE OBJECTS
        for noradIndex in visibleNorads:
            if noradIndex not in positions['2D_MAP']['OBJECTS']:
                continue
            self._updateObjectDisplay(noradIndex, positions['2D_MAP']['OBJECTS'][noradIndex])

    def _updateObjectDisplay(self, noradIndex, noradPosition):
        isSelected = (noradIndex == self.selectedObject)
        isHovered = (noradIndex == self.hoveredObject)
        isActive = isSelected or isHovered
        noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
        # GROUND TRACKS
        groundTrackColor, groundTrackWidth = noradObjectConfiguration['GROUND_TRACK']['COLOR'], noradObjectConfiguration['GROUND_TRACK']['WIDTH']
        if self._shouldRender(noradObjectConfiguration['GROUND_TRACK']['MODE'], isSelected, self.displayConfiguration['SHOW_GROUND_TRACK']):
            groundLongitudes, groundLatitudes = noradPosition['GROUND_TRACK']['LONGITUDE'], noradPosition['GROUND_TRACK']['LATITUDE']
            groundSegments = self._splitWrapSegment(groundLongitudes, groundLatitudes)
            for item in self.objectGroundTracks.get(noradIndex, []):
                self.plot.removeItem(item)
            self.objectGroundTracks[noradIndex] = []
            for segmentLongitudes, segmentLatitudes in groundSegments:
                gx, gy = self._lonlatToCartesian(segmentLongitudes, segmentLatitudes)
                curve = pg.PlotCurveItem(gx, gy, pen=pg.mkPen(groundTrackColor, width=groundTrackWidth))
                curve.setZValue(self.ELEMENTS_Z_VALUES['GROUND_TRACK'])
                self.objectGroundTracks[noradIndex].append(curve)
                self.plot.addItem(self.objectGroundTracks[noradIndex][-1])
            # GROUND TRACK ARROW
            lastLongitude, lastLatitude = groundSegments[-1]
            x0, y0 = self._lonlatToCartesian(lastLongitude[-2], lastLatitude[-2])
            x1, y1 = self._lonlatToCartesian(lastLongitude[-1], lastLatitude[-1])
            length = np.hypot(x1 - x0, y1 - y0)
            angle = self._arrowAngle(x0, y0, x1, y1)
            if noradIndex not in self.objectArrows:
                arrow = pg.ArrowItem(angle=angle, tipAngle=30, headLen=length, tailLen=0, tailWidth=0, pen=pg.mkPen(groundTrackColor), brush=pg.mkBrush(groundTrackColor), pxMode=False)
                arrow.setZValue(self.ELEMENTS_Z_VALUES['GROUND_TRACK'])
                self.objectArrows[noradIndex] = arrow
                self.plot.addItem(self.objectArrows[noradIndex])
            self.objectArrows[noradIndex].setStyle(angle=angle)
            self.objectArrows[noradIndex].setPos(x1, y1)
        else:
            self._removeItems(self.objectGroundTracks.get(noradIndex))
            self._removeItems(self.objectArrows.get(noradIndex))
            self.objectGroundTracks.pop(noradIndex, None)
            self.objectArrows.pop(noradIndex, None)
        # VISIBILITY FOOTPRINT
        footColor, footWidth = noradObjectConfiguration['FOOTPRINT']['COLOR'], noradObjectConfiguration['FOOTPRINT']['WIDTH']
        if self._shouldRender(noradObjectConfiguration['FOOTPRINT']['MODE'], isSelected, self.displayConfiguration['SHOW_FOOTPRINT']):
            footLongitudes, footLatitudes = noradPosition['VISIBILITY']['LONGITUDE'], noradPosition['VISIBILITY']['LATITUDE']
            footSegments = self._splitWrapSegment(footLongitudes, footLatitudes)
            for item in self.objectFootprints.get(noradIndex, []):
                self.plot.removeItem(item)
            self.objectFootprints[noradIndex] = []
            for segmentLongitudes, segmentLatitudes in footSegments:
                fx, fy = self._lonlatToCartesian(segmentLongitudes, segmentLatitudes)
                curve = pg.PlotCurveItem(fx, fy, pen=pg.mkPen(footColor, width=footWidth))
                curve.setZValue(self.ELEMENTS_Z_VALUES['FOOTPRINT'])
                self.objectFootprints[noradIndex].append(curve)
                self.plot.addItem(self.objectFootprints[noradIndex][-1])
        else:
            self._removeItems(self.objectFootprints.get(noradIndex))
            self.objectFootprints.pop(noradIndex, None)
        # OBJECT POSITIONS
        spotColor = tuple(noradObjectConfiguration['SPOT']['COLOR']) if isActive else (150, 150, 150)
        x, y = self._lonlatToCartesian(noradPosition['POSITION']['LONGITUDE'], noradPosition['POSITION']['LATITUDE'])
        if noradIndex not in self.objectSpots:
            spot = pg.ScatterPlotItem(size=noradObjectConfiguration['SPOT']['SIZE'], brush=pg.mkBrush(*spotColor))
            spot.sigClicked.connect(self._onObjectClicked)
            spot.setZValue(self.ELEMENTS_Z_VALUES['SPOT'])
            self.objectSpots[noradIndex] = spot
            self.plot.addItem(self.objectSpots[noradIndex])
        self.objectSpots[noradIndex].setData([{'pos': (x, y), 'data': noradIndex}], brush=pg.mkBrush(*spotColor), pen=None)
        self.objectSpots[noradIndex].setSize(noradObjectConfiguration['SPOT']['SIZE'])
        if noradIndex not in self.objectLabels:
            label = pg.TextItem(text=noradPosition['NAME'], anchor=(0.5, 1.2), color=(255, 255, 255))
            label.setZValue(self.ELEMENTS_Z_VALUES['LABEL'])
            label.hide()
            self.objectLabels[noradIndex] = label
            self.plot.addItem(label)
        self.objectLabels[noradIndex].setPos(x, y)
        if isActive:
            self.objectLabels[noradIndex].show()
        else:
            self.objectLabels[noradIndex].hide()
        if self._lastMouseScenePos is not None:
            self._onMouseMoved(self._lastMouseScenePos)

    def _onObjectClicked(self, plot, points):
        if not points:
            return
        noradIndex = points[0].data()
        if noradIndex is None:
            return
        self.objectSelected.emit([noradIndex])

    def _onMouseMoved(self, scenePos):
        self._lastMouseScenePos = scenePos
        self.hoverRadius = 15 * self.plot.vb.viewPixelSize()[0]
        if not self.objectSpots:
            return
        closestNorad, closestDist = None, float("inf")
        mouseViewPos = self.plot.vb.mapSceneToView(scenePos)
        for noradIndex, spot in self.objectSpots.items():
            pts = spot.points()
            if not pts:
                continue
            spotViewPos = pts[0].pos()
            dist = np.sqrt((spotViewPos.x() - mouseViewPos.x()) ** 2 + (spotViewPos.y() - mouseViewPos.y()) ** 2)
            if dist < self.hoverRadius and dist < closestDist:
                closestNorad, closestDist = noradIndex, dist
        if closestNorad is not None and self.hoveredObject is None:
            self.hoveredObject = closestNorad
            if closestNorad in self.objectLabels:
                self.objectLabels[closestNorad].show()
        elif closestNorad is None and self.hoveredObject is not None:
            if self.hoveredObject in self.objectLabels and self.hoveredObject != self.selectedObject:
                self.objectLabels[self.hoveredObject].hide()
            self.hoveredObject = None
        elif closestNorad is not None and closestNorad != self.hoveredObject:
            if self.hoveredObject in self.objectLabels and self.hoveredObject != self.selectedObject:
                self.objectLabels[self.hoveredObject].hide()
            self.hoveredObject = closestNorad
            if closestNorad in self.objectLabels:
                self.objectLabels[closestNorad].show()

    def _removeItems(self, items):
        if not items:
            return
        if isinstance(items, list):
            for item in items:
                self.plot.removeItem(item)
        else:
            self.plot.removeItem(items)


class Object2dMapConfigDockWidget(QDockWidget):
    configChanged = pyqtSignal(int, dict)
    MODES = {'Always': "ALWAYS", 'When Selected': "WHEN_SELECTED", 'Never': "NEVER"}

    def __init__(self, parent=None):
        super().__init__("Object Map Configuration", parent)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.noradIndex = None
        self._currentConfig = None
        self._setupUi()

    def _setupUi(self):
        self.editorWidget = QWidget()
        self.editorWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        mainLayout = QVBoxLayout(self.editorWidget)
        mainLayout.setSpacing(10)
        mainLayout.setContentsMargins(6, 6, 6, 6)

        # SPOT CONFIGURATION
        self.spotGroup = self._groupBox("Spot")
        self.spotColorButton = self._colorButton()
        self.spotSizeSpin = QSpinBox()
        self.spotSizeSpin.setRange(4, 30)
        self.spotSizeSpin.setToolTip("Size")

        self.spotGroup.layout().addWidget(self.spotColorButton, 0, 0)
        self.spotGroup.layout().addWidget(self.spotSizeSpin, 0, 1)
        mainLayout.addWidget(self.spotGroup)

        # GROUND TRACK CONFIGURATION
        self.groundTrackGroup = self._groupBox("Ground Track")
        self.groundTrackModeCombo = QComboBox()
        self.groundTrackModeCombo.addItems(list(self.MODES.keys()))
        self.groundTrackColorButton = self._colorButton()
        self.groundTrackWidthSpin = QSpinBox()
        self.groundTrackWidthSpin.setRange(1, 5)
        self.groundTrackWidthSpin.setToolTip("Width")

        self.groundTrackGroup.layout().addWidget(self.groundTrackModeCombo, 0, 0)
        self.groundTrackGroup.layout().addWidget(self.groundTrackColorButton, 0, 1)
        self.groundTrackGroup.layout().addWidget(self.groundTrackWidthSpin, 0, 2)
        mainLayout.addWidget(self.groundTrackGroup)

        # VISIBILITY CONFIGURATION
        self.footprintGroup = self._groupBox("Visibility Footprint")
        self.footprintModeCombo = QComboBox()
        self.footprintModeCombo.addItems(list(self.MODES.keys()))
        self.footprintColorButton = self._colorButton()
        self.footprintWidthSpin = QSpinBox()
        self.footprintWidthSpin.setRange(1, 5)
        self.footprintWidthSpin.setToolTip("Width")

        self.footprintGroup.layout().addWidget(self.footprintModeCombo, 0, 0)
        self.footprintGroup.layout().addWidget(self.footprintColorButton, 0, 1)
        self.footprintGroup.layout().addWidget(self.footprintWidthSpin, 0, 2)
        mainLayout.addWidget(self.footprintGroup)

        self.editorWidget.setEnabled(False)
        self.setWidget(self.editorWidget)
        self.spotSizeSpin.valueChanged.connect(self._emitConfig)
        self.groundTrackModeCombo.currentIndexChanged.connect(self._emitConfig)
        self.groundTrackWidthSpin.valueChanged.connect(self._emitConfig)
        self.footprintModeCombo.currentIndexChanged.connect(self._emitConfig)
        self.footprintWidthSpin.valueChanged.connect(self._emitConfig)

        self.spotColorButton.clicked.connect(lambda: self._pickColor('SPOT'))
        self.groundTrackColorButton.clicked.connect(lambda: self._pickColor('GROUND_TRACK'))
        self.footprintColorButton.clicked.connect(lambda: self._pickColor('FOOTPRINT'))

    @staticmethod
    def _colorButton():
        btn = QPushButton()
        btn.setFixedSize(24, 24)
        btn.setStyleSheet("border: 1px solid #666;")
        return btn

    @staticmethod
    def _groupBox(title: str):
        box = QGroupBox(title)
        box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = QGridLayout(box)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)
        layout.setContentsMargins(8, 12, 8, 8)
        return box

    @staticmethod
    def _setButtonColor(btn, color):
        btn.setStyleSheet(f"background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;")

    def _modeToLabel(self, mode):
        for label, value in self.MODES.items():
            if value == mode:
                return label
        return "Never"

    def setSelectedObject(self, noradIndex: int | None, config: dict):
        self.noradIndex = noradIndex
        if noradIndex is None:
            self.clear()
            return
        self.editorWidget.setEnabled(True)
        self._currentConfig = config[str(noradIndex)]
        blockers = [
            QSignalBlocker(self.spotSizeSpin),
            QSignalBlocker(self.groundTrackModeCombo),
            QSignalBlocker(self.groundTrackWidthSpin),
            QSignalBlocker(self.footprintModeCombo),
            QSignalBlocker(self.footprintWidthSpin),
        ]
        self.spotSizeSpin.setValue(self._currentConfig['SPOT'].get('SIZE', 10))
        self.groundTrackModeCombo.setCurrentText(self._modeToLabel(self._currentConfig['GROUND_TRACK']['MODE']))
        self.groundTrackWidthSpin.setValue(self._currentConfig['GROUND_TRACK'].get('WIDTH', 1))
        self.footprintModeCombo.setCurrentText(self._modeToLabel(self._currentConfig['FOOTPRINT']['MODE']))
        self.footprintWidthSpin.setValue(self._currentConfig['FOOTPRINT'].get('WIDTH', 1))
        self._setButtonColor(self.spotColorButton, self._currentConfig['SPOT']['COLOR'])
        self._setButtonColor(self.groundTrackColorButton, self._currentConfig['GROUND_TRACK']['COLOR'])
        self._setButtonColor(self.footprintColorButton, self._currentConfig['FOOTPRINT']['COLOR'])
        del blockers

    def enableFootprintConfig(self, enabled: bool):
        self.footprintGroup.setEnabled(enabled)

    def enableGroundTrackConfig(self, enabled: bool):
        self.groundTrackGroup.setEnabled(enabled)

    def clear(self):
        self.noradIndex = None
        self._currentConfig = None
        self.editorWidget.setEnabled(False)

    def _pickColor(self, section):
        if self._currentConfig is None:
            return
        color = QColorDialog.getColor()
        if not color.isValid():
            return
        button = {'SPOT': self.spotColorButton, 'GROUND_TRACK': self.groundTrackColorButton, 'FOOTPRINT': self.footprintColorButton}[section]
        self._currentConfig[section]['COLOR'] = (color.red(), color.green(), color.blue())
        self._setButtonColor(button, self._currentConfig[section]['COLOR'])
        self._emitConfig()

    def _emitConfig(self, *_):
        if not self.editorWidget.isEnabled():
            return
        if self.noradIndex is None or self._currentConfig is None:
            return
        self._currentConfig['SPOT']['SIZE'] = self.spotSizeSpin.value()
        self._currentConfig['GROUND_TRACK']['MODE'] = self.MODES[self.groundTrackModeCombo.currentText()]
        self._currentConfig['GROUND_TRACK']['WIDTH'] = self.groundTrackWidthSpin.value()
        self._currentConfig['FOOTPRINT']['MODE'] = self.MODES[self.footprintModeCombo.currentText()]
        self._currentConfig['FOOTPRINT']['WIDTH'] = self.footprintWidthSpin.value()
        self.configChanged.emit(self.noradIndex, self._currentConfig)