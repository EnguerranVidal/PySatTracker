import copy
import numpy as np
import imageio

from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import *

from src.core.objects import ActiveObjectsModel


class Map2dWidget(QOpenGLWidget):
    objectSelected = pyqtSignal(list)

    def __init__(self, parent=None, mapImagePath='src/assets/earth/earth.jpg', nightImagePath='src/assets/earth/earth_lights.jpg'):
        super().__init__(parent)
        glutInit()
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)
        self.mapHeight, self.mapWidth, self.nightHeight, self.nightWidth = 0, 0, 0, 0
        self.mapImagePath, self.nightImagePath = mapImagePath, nightImagePath
        self.zoom, self.offset, self.lastMousePos = 1.0, np.array([0.0, 0.0]), None
        self.activeObjects: ActiveObjectsModel | None = None
        self.hoveredObject, self.hoverRadius = None, 20
        self.displayConfiguration = {}
        self.objectPositions, self.groundTracks, self.footprints = {}, {}, {}
        self.sunLongitude, self.sunLatitude = None, None
        self.earthTexture, self.nightTexture, self.earthShader = None, None, None
        self._loadEarthTextures()
        self.terminatorItem = None
        self.vernalItem = None

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
        print('Initializing 2D map OpenGL context...')
        # INITIALIZING OPENGL MAP RENDERING
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        self.earthTexture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.earthTexture)
        mapImage = self.earthTextureData
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, mapImage.shape[1], mapImage.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, mapImage)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        self.nightTexture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.nightTexture)
        img = self.nightTextureData
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.shape[1], img.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, img)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
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
        for noradIndex, position in self.objectPositions.items():
            longitude, latitude = position['POSITION']['LONGITUDE'], position['POSITION']['LATITUDE']
            xWorld, yWorld = self._lonlatToCartesian(longitude, latitude)
            xScreen, yScreen = self._worldCoordinateToScreen(xWorld, yWorld)
            distance = np.hypot(xScreen - xMouse, yScreen - yMouse)
            if distance < self.hoverRadius and distance < closestDistance:
                closest = noradIndex
                closestDistance = distance
        return closest

    def paintGL(self):
        if not self.activeObjects:
            return
        glClearColor(0.12, 0.13, 0.14, 1)
        glClear(GL_COLOR_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        left, right, bottom, top = self._computeViewRect()
        glOrtho(left, right, bottom, top, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self._drawEarth()
        if self.displayConfiguration.get('2D_MAP', {}).get('SHOW_GRID', False):
            self._drawGrid()
        if self.displayConfiguration.get('2D_MAP', {}).get('SHOW_TERMINATOR', False):
            self._drawTerminator()
        self._drawGroundTracks()
        self._drawFootprints()
        self._drawObjects()
        if self.displayConfiguration.get('2D_MAP', {}).get('SHOW_SUN', False):
            self._drawSun()
        if self.displayConfiguration.get('2D_MAP', {}).get('SHOW_VERNAL', False):
            self._drawVernal()
        self._drawLabels()

    def _drawEarth(self):
        correctShaderLoading = self.earthShader and self.nightTexture and self.sunLongitude is not None and self.sunLatitude is not None
        if self.displayConfiguration.get('2D_MAP', {}).get('SHOW_NIGHT', False) and correctShaderLoading:
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
        if self.displayConfiguration.get('2D_MAP', {}).get('SHOW_NIGHT', False) and correctShaderLoading:
            glUseProgram(0)
            glActiveTexture(GL_TEXTURE1)
            glDisable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            glActiveTexture(GL_TEXTURE0)
        glDisable(GL_TEXTURE_2D)

    def _drawGrid(self):
        glColor4f(0.6, 0.6, 0.6, 0.3)
        glLineWidth(1)
        for longitude in range(-180, 181, 30):
            glBegin(GL_LINE_STRIP)
            for latitude in range(-90, 91, 5):
                x, y = self._lonlatToCartesian(longitude, latitude)
                glVertex2f(x, y)
            glEnd()
        for latitude in range(-90, 91, 30):
            glBegin(GL_LINE_STRIP)
            for longitude in range(-180, 181, 5):
                x, y = self._lonlatToCartesian(longitude, latitude)
                glVertex2f(x, y)
            glEnd()

    @staticmethod
    def _shouldRender(mode: str, isSelected: bool, isToggled: bool):
        if not isToggled:
            return False
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER

    def _getObjectRenderConfiguration(self, noradIndex):
        groupName = self.activeObjects.getGroupForNoradIndex(noradIndex)
        isInSelectedGroup = (self.activeObjects.isGroupSelected and groupName == self.activeObjects.selectedGroupName)
        if isInSelectedGroup and groupName:
            group = self.activeObjects.objectGroups.get(groupName)
            if group:
                groupConfig = group.renderRules.get('2D_MAP', {})
                if groupConfig.get('SHARED'):
                    source = groupConfig.get('SOURCE', 'CUSTOM')
                    if source == 'CUSTOM':
                        config = groupConfig.get('CONFIG')
                        if config:
                            return copy.deepcopy(config)
                    elif source == 'OBJECT':
                        sourceNorad = groupConfig.get('SOURCE_OBJECT')
                        if sourceNorad and str(sourceNorad) in self.displayConfiguration['OBJECTS']:
                            return copy.deepcopy(self.displayConfiguration['OBJECTS'][str(sourceNorad)])
        return copy.deepcopy(self.displayConfiguration['OBJECTS'][str(noradIndex)])

    def _drawGroundTracks(self):
        glColor3f(0.2, 0.8, 1)
        for noradIndex, track in self.groundTracks.items():
            isSelected = noradIndex in [obj.noradIndex for obj in self.activeObjects.selectedObjects]
            noradObjectConfiguration = self._getObjectRenderConfiguration(noradIndex)
            isToggled = self.displayConfiguration.get('2D_MAP', {}).get('SHOW_GROUND_TRACKS', False)
            if self._shouldRender(noradObjectConfiguration['GROUND_TRACK']['MODE'], isSelected, isToggled):
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
            isSelected = noradIndex in [obj.noradIndex for obj in self.activeObjects.selectedObjects]
            noradObjectConfiguration = self._getObjectRenderConfiguration(noradIndex)
            isToggled = self.displayConfiguration.get('2D_MAP', {}).get('SHOW_FOOTPRINTS', False)
            if self._shouldRender(noradObjectConfiguration['FOOTPRINT']['MODE'], isSelected, isToggled):
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
            noradObjectConfiguration = self._getObjectRenderConfiguration(noradIndex)
            color, size = noradObjectConfiguration['SPOT']['COLOR'], noradObjectConfiguration['SPOT']['SIZE']
            x, y = self._lonlatToCartesian(position['POSITION']['LONGITUDE'], position['POSITION']['LATITUDE'])
            glPointSize(size)
            if noradIndex in [obj.noradIndex for obj in self.activeObjects.selectedObjects]:
                glColor4f(color[0] / 255, color[1] / 255, color[2] / 255, 1)
            else:
                glColor4f(1, 1, 1, 1)
            glBegin(GL_POINTS)
            glVertex2f(x, y)
            glEnd()

    def _drawLabels(self):
        viewPort = (GLint * 4)()
        glGetIntegerv(GL_VIEWPORT, viewPort)
        for noradIndex, position in self.objectPositions.items():
            isSelected = noradIndex in [obj.noradIndex for obj in self.activeObjects.selectedObjects]
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
            objectName = self.objectPositions[noradIndex]['NAME']
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
        x, y = self._lonlatToCartesian(self.vernalItem['LONGITUDE'], self.vernalItem['LATITUDE'])
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
        if self.terminatorItem is None:
            return
        longitudes, latitudes = np.array(self.terminatorItem['LONGITUDE']), np.array(self.terminatorItem['LATITUDE'])
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

    def updateMap(self, positions, displayConfiguration):
        self.displayConfiguration = displayConfiguration
        mapData = positions['2D_MAP']
        self.sunLongitude, self.sunLatitude = mapData['SUN']['LONGITUDE'], mapData['SUN']['LATITUDE']
        self.vernalItem = mapData['VERNAL']
        self.terminatorItem = mapData['NIGHT']
        self.objectPositions.clear()
        self.groundTracks.clear()
        self.footprints.clear()
        for noradIndex in self.activeObjects.allNoradIndices():
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
            self.objectSelected.emit([picked])
        self.lastMousePos = None

    def resetView(self):
        self.zoom = 1.0
        self.offset = np.array([0.0, 0.0])
        self.update()

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects
        self.update()