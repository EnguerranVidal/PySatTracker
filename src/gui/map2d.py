import numpy as np
import imageio
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.shaders import compileProgram, compileShader
from OpenGL.GLUT import *
from OpenGL.arrays import vbo

from PyQt5.QtCore import Qt, pyqtSignal, QSignalBlocker
from PyQt5.QtWidgets import *


class Map2dWidget(QOpenGLWidget):
    objectSelected = pyqtSignal(list)

    def __init__(self, parent=None, mapImagePath='src/assets/earth/earth.jpg', nightImagePath='src/assets/earth/earth_lights.jpg'):
        super().__init__(parent)
        self.mapImagePath, self.nightImagePath = mapImagePath, nightImagePath
        self.zoom, self.offset, self.lastMousePos = 1.0, np.array([0.0, 0.0]), None
        self.selectedObject, self.hoveredObject, self.hoverRadius = None, None, 20
        self.displayConfiguration = {}
        self.objectPositions, self.groundTracks, self.footprints = {}, {}, {}
        self.sunLongitude, self.sunLatitude = None, None
        self.earthTexture, self.nightTexture, self.earthShader = None, None, None
        self.terminator = None
        self.vernal = None
        self.setMouseTracking(True)
        self._loadEarthTextures()

    def _loadEarthTextures(self):
        if not os.path.exists(self.mapImagePath):
            raise FileNotFoundError(self.mapImagePath)
        mapImage = imageio.imread(self.mapImagePath)
        mapImage = mapImage[::-1]
        self.mapHeight, self.mapWidth = mapImage.shape[:2]
        self.earthTextureData = mapImage.astype(np.uint8)
        if not os.path.exists(self.nightImagePath):
            raise FileNotFoundError(self.nightImagePath)
        nightImage = imageio.imread(self.nightImagePath)
        nightImage = nightImage[::-1]
        self.nightHeight, self.nightWidth = nightImage.shape[:2]
        self.nightTextureData = nightImage.astype(np.uint8)

    def initializeGL(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glutInit()
        # EARTH DAY TEXTURE
        self.earthTexture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.earthTexture)
        mapImage = self.earthTextureData
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, mapImage.shape[1], mapImage.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, mapImage)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # EARTH NIGHT TEXTURE
        self.nightTexture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.nightTexture)
        img = self.nightTextureData
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.shape[1], img.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, img)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # EARTH SHADER LOADING
        try:
            with open("src/assets/earth/map.vert") as f:
                vertSource = f.read()
            with open("src/assets/earth/map.frag") as f:
                fragSource = f.read()
            self.earthShader = compileProgram(compileShader(vertSource, GL_VERTEX_SHADER), compileShader(fragSource, GL_FRAGMENT_SHADER))
        except Exception as e:
            self.earthShader = None
            raise RuntimeError(f"Earth shader failed to compile/link:\n{e}")

    def _lonlatToCartesian(self, longitude, latitude):
        longitude, latitude = np.asarray(longitude), np.asarray(latitude)
        return (longitude + 180) / 360 * self.mapWidth, (latitude + 90) / 180 * self.mapHeight

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

    def _computeViewRect(self):
        widgetAspectRatio = self.width() / self.height()
        mapAspectRatio = self.mapWidth / self.mapHeight
        viewWidth, viewHeight = self.mapWidth * self.zoom, self.mapHeight * self.zoom
        if widgetAspectRatio > mapAspectRatio:
            viewWidth = viewHeight * widgetAspectRatio
        else:
            viewHeight = viewWidth / widgetAspectRatio
        xCenter, yCenter = self.mapWidth / 2 - self.offset[0], self.mapHeight / 2 - self.offset[1]
        left, right, bottom, top = xCenter - viewWidth / 2, xCenter + viewWidth / 2, yCenter - viewHeight / 2, yCenter + viewHeight / 2
        return left, right, bottom, top

    def _screenCoordinateToWorld(self, xScreen, yScreen):
        left, right, bottom, top = self._computeViewRect()
        xWorld, yWorld = left + (xScreen / self.width()) * (right - left), bottom + (1 - yScreen / self.height()) * (top - bottom)
        return xWorld, yWorld

    def _worldCoordinateToScreen(self, xWorld, yWorld):
        left, right, bottom, top = self._computeViewRect()
        nx = (xWorld - left) / (right - left)
        ny = (yWorld - bottom) / (top - bottom)
        xScreen = nx * self.width()
        yScreen = (1 - ny) * self.height()
        return xScreen, yScreen

    def _pixelToWorldDistance(self, pixelDistance):
        left, right, bottom, top = self._computeViewRect()
        worldWidth = right - left
        worldHeight = top - bottom
        return pixelDistance * worldWidth / self.width(), pixelDistance * worldHeight / self.height()

    def _pickSatellite(self, xMouse, yMouse):
        closest = None
        closestDistance = float("inf")
        for noradIndex, pos in self.objectPositions.items():
            lon = pos['POSITION']['LONGITUDE']
            lat = pos['POSITION']['LATITUDE']
            xWorld, yWorld = self._lonlatToCartesian(lon, lat)
            xScreen, yScreen = self._worldCoordinateToScreen(xWorld, yWorld)
            dx = xScreen - xMouse
            dy = yScreen - yMouse
            distance = np.hypot(dx, dy)
            cfg = self.displayConfiguration['OBJECTS'][str(noradIndex)]
            if distance < self.hoverRadius and distance < closestDistance:
                closest = noradIndex
                closestDistance = distance
        return closest

    def paintGL(self):
        glClearColor(0.12, 0.13, 0.14, 1)
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        left, right, bottom, top = self._computeViewRect()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(left, right, bottom, top, -1, 1)
        self._drawEarth()
        if self.displayConfiguration.get('SHOW_TERMINATOR', False):
            self._drawTerminator()
        if self.displayConfiguration.get('SHOW_GROUND_TRACK', False):
            self._drawGroundTracks()
        if self.displayConfiguration.get('SHOW_FOOTPRINT', False):
            self._drawFootprints()
        self._drawObjects()
        if self.displayConfiguration.get('SHOW_SUN', False):
            self._drawSun()
        if self.displayConfiguration.get('SHOW_VERNAL', False):
            self._drawVernal()
        self._drawLabels()

    def _drawEarth(self):
        correctShaderLoading = self.earthShader and self.nightTexture and self.sunLongitude is not None and self.sunLatitude is not None
        if self.displayConfiguration.get('SHOW_NIGHT', False) and correctShaderLoading:
            glUseProgram(self.earthShader)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.earthTexture)
            glUniform1i(glGetUniformLocation(self.earthShader, "dayTexture"), 0)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, self.nightTexture)
            glUniform1i(glGetUniformLocation(self.earthShader, "nightTexture"), 1)
            glUniform1f(glGetUniformLocation(self.earthShader, "sunLongitudeRadians"), np.radians(self.sunLongitude))
            glUniform1f(glGetUniformLocation(self.earthShader, "sunLatitudeRadians"), np.radians(self.sunLatitude))
            glUniform1f(glGetUniformLocation(self.earthShader, "twilightWidth"), 0.15)
        else:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.earthTexture)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(0, 0)
        glTexCoord2f(1, 0)
        glVertex2f(self.mapWidth, 0)
        glTexCoord2f(1, 1)
        glVertex2f(self.mapWidth, self.mapHeight)
        glTexCoord2f(0, 1)
        glVertex2f(0, self.mapHeight)
        glEnd()
        if self.displayConfiguration.get('SHOW_NIGHT', False) and correctShaderLoading:
            glUseProgram(0)
            glActiveTexture(GL_TEXTURE1)
            glDisable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            glActiveTexture(GL_TEXTURE0)
        glDisable(GL_TEXTURE_2D)

    @staticmethod
    def _shouldRender(mode: str, isSelected: bool):
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER

    def _drawGroundTracks(self):
        glColor3f(0.2, 0.8, 1)
        for noradIndex, track in self.groundTracks.items():
            isSelected = (noradIndex == self.selectedObject)
            noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
            if self._shouldRender(noradObjectConfiguration['GROUND_TRACK']['MODE'], isSelected):
                color, width = noradObjectConfiguration['GROUND_TRACK']['COLOR'], noradObjectConfiguration['GROUND_TRACK']['WIDTH']
                glColor3f(color[0] / 255, color[1] / 255, color[2] / 255)
                glLineWidth(width)
                segments = self._splitWrapSegment(track['LONGITUDE'], track['LATITUDE'])
                for segLon, segLat in segments:
                    glBegin(GL_LINE_STRIP)
                    for lon, lat in zip(segLon, segLat):
                        x, y = self._lonlatToCartesian(lon, lat)
                        glVertex2f(x, y)
                    glEnd()
                lastLon, lastLat = segments[-1]
                if len(lastLon) >= 2:
                    x0, y0 = self._lonlatToCartesian(lastLon[-2], lastLat[-2])
                    x1, y1 = self._lonlatToCartesian(lastLon[-1], lastLat[-1])
                    self._drawGroundTrackArrow(x0, y0, x1, y1, color)

    def _drawFootprints(self):
        for noradIndex, footprint in self.footprints.items():
            isSelected = (noradIndex == self.selectedObject)
            noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
            if self._shouldRender(noradObjectConfiguration['FOOTPRINT']['MODE'], isSelected):
                color, width = noradObjectConfiguration['FOOTPRINT']['COLOR'], noradObjectConfiguration['FOOTPRINT']['WIDTH']
                glColor3f(color[0] / 255, color[1] / 255, color[2] / 255)
                glLineWidth(width)
                segments = self._splitWrapSegment(footprint['LONGITUDE'], footprint['LATITUDE'])
                for segLon, segLat in segments:
                    glBegin(GL_LINE_STRIP)
                    for lon, lat in zip(segLon, segLat):
                        x, y = self._lonlatToCartesian(lon, lat)
                        glVertex2f(x, y)
                    glEnd()

    def _drawObjects(self):
        for noradIndex, position in self.objectPositions.items():
            noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
            color, size = noradObjectConfiguration['SPOT']['COLOR'], noradObjectConfiguration['SPOT']['SIZE']
            x, y = self._lonlatToCartesian(position['POSITION']['LONGITUDE'], position['POSITION']['LATITUDE'])
            glPointSize(size)
            if noradIndex == self.selectedObject:
                glColor3f(color[0] / 255, color[1] / 255, color[2] / 255)
            else:
                glColor3f(1, 1, 1)
            glBegin(GL_POINTS)
            glVertex2f(x, y)
            glEnd()

    def _drawLabels(self):
        viewPort = (GLint * 4)()
        glGetIntegerv(GL_VIEWPORT, viewPort)
        for noradIndex, position in self.objectPositions.items():
            isSelected = (noradIndex == self.selectedObject)
            isHovered = (noradIndex == self.hoveredObject)
            isActive = isSelected or isHovered
            if not isActive:
                continue
            xWorld, yWorld = self._lonlatToCartesian(position['POSITION']['LONGITUDE'], position['POSITION']['LATITUDE'])
            xScreen, yScreen = self._worldCoordinateToScreen(xWorld, yWorld)
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, viewPort[2], 0, viewPort[3], -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()
            glActiveTexture(GL_TEXTURE1)
            glDisable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            glActiveTexture(GL_TEXTURE0)
            glDisable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            glColor4f(1, 1, 1, 1)
            glRasterPos2f(xScreen + 5, viewPort[3] - yScreen + 5)
            objectName = position.get("NAME", str(noradIndex))
            for char in objectName:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()

    def _drawGroundTrackArrow(self, x0, y0, x1, y1, color):
        xDifference, yDifference = x1 - x0, y1 - y0
        length = np.hypot(xDifference, yDifference)
        if length < 1e-9:
            return
        ux, uy = xDifference / length, yDifference / length
        xPixels, yPixels = -uy, ux
        arrowLength, arrowWidth, maxLen = 1.2 * length, 0.7 * length, 0.04 * self.mapWidth
        arrowLength, arrowWidth = min(arrowLength, maxLen), min(arrowWidth, maxLen * 0.6)
        xArrowTip, yArrowTip = x1, y1
        xArrowBase, yArrowBase = x1 - ux * arrowLength, y1 - uy * arrowLength
        xLeft, yLeft = xArrowBase + xPixels * arrowWidth, yArrowBase + yPixels * arrowWidth
        xRight, yRight = xArrowBase - xPixels * arrowWidth, yArrowBase - yPixels * arrowWidth
        glColor3f(color[0] / 255, color[1] / 255, color[2] / 255)
        glBegin(GL_TRIANGLES)
        glVertex2f(xArrowTip, yArrowTip)
        glVertex2f(xLeft, yLeft)
        glVertex2f(xRight, yRight)
        glEnd()

    def _drawSun(self):
        x, y = self._lonlatToCartesian(self.sunLongitude, self.sunLatitude)
        innerRadiusPx = 6
        outerRadiusPx = 9
        innerRadiusX, innerRadiusY = self._pixelToWorldDistance(innerRadiusPx)
        outerRadiusX, outerRadiusY = self._pixelToWorldDistance(outerRadiusPx)
        segments = 32
        glColor3f(1.0, 0.7, 0.0)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(x, y)
        for a in np.linspace(0, 2 * np.pi, segments):
            glVertex2f(x + outerRadiusX * np.cos(a), y + outerRadiusY * np.sin(a))
        glEnd()
        glColor3f(1.0, 1.0, 0.2)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(x, y)
        for a in np.linspace(0, 2 * np.pi, segments):
            glVertex2f(x + innerRadiusX * np.cos(a), y + innerRadiusY * np.sin(a))
        glEnd()

    def _drawVernal(self):
        x, y = self._lonlatToCartesian(self.vernal['LONGITUDE'], self.vernal['LATITUDE'])
        sizePx = 10
        sizeX, sizeY = self._pixelToWorldDistance(sizePx)
        glLineWidth(2)
        glColor3f(0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex2f(x - sizeX, y)
        glVertex2f(x + sizeX, y)
        glVertex2f(x, y - sizeY)
        glVertex2f(x, y + sizeY)
        glEnd()

    def _drawTerminator(self):
        if self.terminator is None:
            return
        longitudes, latitudes = np.array(self.terminator['LONGITUDE']), np.array(self.terminator['LATITUDE'])
        longitudes = (longitudes + 180) % 360 - 180
        segments = self._splitWrapSegment(longitudes, latitudes)
        glColor4f(1.0, 0.0, 0.0, 0.5)
        glLineWidth(2.0)
        for segLon, segLat in segments:
            glBegin(GL_LINE_STRIP)
            for lon, lat in zip(segLon, segLat):
                x, y = self._lonlatToCartesian(lon, lat)
                glVertex2f(x, y)
            glEnd()

    def updateMap(self, positions, visibleNorads, selectedNorad, displayConfiguration):
        self.selectedObject = selectedNorad
        self.displayConfiguration = displayConfiguration
        mapData = positions['2D_MAP']
        self.sunLongitude, self.sunLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
        self.vernal = mapData['VERNAL']
        self.terminator = mapData['NIGHT']
        self.objectPositions.clear()
        self.groundTracks.clear()
        self.footprints.clear()
        for noradIndex in visibleNorads:
            if noradIndex not in mapData['OBJECTS']:
                continue
            obj = mapData['OBJECTS'][noradIndex]
            self.objectPositions[noradIndex] = obj
            if 'GROUND_TRACK' in obj:
                self.groundTracks[noradIndex] = obj['GROUND_TRACK']
            if 'VISIBILITY' in obj:
                self.footprints[noradIndex] = obj['VISIBILITY']
        self.update()

    def wheelEvent(self, event):
        xBefore, yBefore = self._screenCoordinateToWorld(event.x(), event.y())
        if event.angleDelta().y() > 0:
            self.zoom *= 0.9
        else:
            self.zoom *= 1.1
        xAfter, yAfter = self._screenCoordinateToWorld(event.x(), event.y())
        self.offset[0] += xAfter - xBefore
        self.offset[1] += yAfter - yBefore
        self.update()

    def mousePressEvent(self, event):
        self.lastMousePos = event.pos()

    def mouseMoveEvent(self, event):
        hovered = self._pickSatellite(event.x(), event.y())
        if hovered != self.hoveredObject:
            self.hoveredObject = hovered
            self.update()
        if self.lastMousePos is None:
            return
        dx = (event.x() - self.lastMousePos.x()) / self.width() * self.mapWidth
        dy = (event.y() - self.lastMousePos.y()) / self.height() * self.mapHeight
        self.offset[0] += dx * self.zoom
        self.offset[1] -= dy * self.zoom
        self.lastMousePos = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        picked = self._pickSatellite(event.x(), event.y())
        if picked is not None:
            self.selectedObject = picked
            self.objectSelected.emit([picked])
            self.update()
        self.lastMousePos = None


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
        colorButton = QPushButton()
        colorButton.setFixedSize(24, 24)
        colorButton.setStyleSheet("border: 1px solid #666;")
        return colorButton

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
    def _setButtonColor(colorButton, color):
        colorButton.setStyleSheet(f"background-color: rgb({color[0]},{color[1]},{color[2]}); border: 1px solid #666;")

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
        colorButton = {'SPOT': self.spotColorButton, 'GROUND_TRACK': self.groundTrackColorButton, 'FOOTPRINT': self.footprintColorButton}[section]
        self._currentConfig[section]['COLOR'] = (color.red(), color.green(), color.blue())
        self._setButtonColor(colorButton, self._currentConfig[section]['COLOR'])
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