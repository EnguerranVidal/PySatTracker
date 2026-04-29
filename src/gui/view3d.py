import copy

from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GL.shaders import compileProgram, compileShader

from PIL import Image
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import *
from OpenGL.GL import *

from src.core.objects import ActiveObjectsModel


class View3dWidget(QOpenGLWidget):
    objectSelected = pyqtSignal(list)
    cameraChanged = pyqtSignal()
    EARTH_RADIUS = 6371
    EARTH_MOON_DISTANCE = 384400
    EARTH_SUN_DISTANCE = 149600000
    SUN_RADIUS = 696340

    def __init__(self, parent=None):
        super().__init__(parent)
        glutInit()
        self.setMouseTracking(True)
        self.minZoom, self.maxZoom = 1.25, self.EARTH_MOON_DISTANCE / self.EARTH_RADIUS * 1.15
        self.activeObjects: ActiveObjectsModel | None = None
        self.objectSpotData, self.objectOrbitData, self.objectNameData = {}, {}, {}
        self.hoveredObject, self.displayConfiguration = None, {}
        self.lastPosX, self.lastPosY = 0, 0
        self.zoom, self.rotX, self.rotY = 5, 45, 225
        self.earthShader = None
        self.earthTextureIndex, self.lightsTextureIndex, self.skyboxTextures = 0, 0, []
        self.gmstAngle = 0
        self.sunDirectionEcef, self.sunDirectionEci = np.array([1, 0, 0], dtype=float), np.array([1, 0, 0], dtype=float)
        self.sphere = None

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # LOADING EARTH MODEL
        glShadeModel(GL_SMOOTH)
        glClearDepth(1)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)
        try:
            img = Image.open("src/assets/earth/earth.jpg")
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            imageData = np.array(img.convert("RGB"), dtype=np.uint8)
            width, height = img.size
            self.earthTextureIndex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.earthTextureIndex)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, imageData)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            print("Earth earthTexture loaded successfully")
        except Exception as e:
            print("Failed to load earth.jpg:", e)
            self.earthTextureIndex = 0
        try:
            img = Image.open("src/assets/earth/earth_lights.jpg")
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            imageData = np.array(img.convert("RGB"), dtype=np.uint8)
            width, height = img.size
            self.lightsTextureIndex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.lightsTextureIndex)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, imageData)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            print("Earth lights earthTexture loaded successfully")
        except Exception as e:
            print("Failed to load earth_lights.jpg:", e)
            self.lightsTextureIndex = 0
        # LOADING EARTH SHADER
        try:
            with open("src/assets/earth/earth.vert") as f:
                vertSource = f.read()
            with open("src/assets/earth/earth.frag") as f:
                fragSource = f.read()
            self.earthShader = compileProgram(compileShader(vertSource, GL_VERTEX_SHADER), compileShader(fragSource, GL_FRAGMENT_SHADER))
        except Exception as e:
            raise RuntimeError(f"Earth shader failed to compile/link:\n{e}")
        # LOADING SKYBOX TEXTURES
        self.skyboxTextures = self._loadSkyBoxTextures([
            "src/assets/skybox/posx.png",
            "src/assets/skybox/negx.png",
            "src/assets/skybox/posy.png",
            "src/assets/skybox/negy.png",
            "src/assets/skybox/posz.png",
            "src/assets/skybox/negz.png",
        ])

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / max(h, 1), 0.1, 1000)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if not self.activeObjects:
            return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(0)
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glLoadIdentity()

        # CAMERA
        glTranslatef(0, 0, -self.zoom)
        glRotatef(self.rotX, 1, 0, 0)
        glRotatef(self.rotY, 0, 1, 0)
        if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH_GRID', False):
            glPushMatrix()
            glRotatef(-90, 1, 0, 0)
            glRotatef(self.gmstAngle, 0, 0, 1)
            glRotatef(90, 1, 0, 0)
            self._drawEarthGrid()
            glPopMatrix()

        glRotatef(-90, 1, 0, 0)
        glActiveTexture(GL_TEXTURE1)
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        glActiveTexture(GL_TEXTURE0)
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        modelView = (GLdouble * 16)()
        glGetDoublev(GL_MODELVIEW_MATRIX, modelView)
        originalModelView = list(modelView)
        modelView[12] = modelView[13] = modelView[14] = 0.0
        glLoadMatrixd(modelView)
        self.drawSkybox(size=500)
        self.drawSun()
        glLoadMatrixd(originalModelView)
        try:
            glUseProgram(0)
            glDisable(GL_LIGHTING)
            glDisable(GL_TEXTURE_2D)
            glColor4f(1, 1, 1, 1)
            # DRAWING OBJECTS AND AXES
            if self.displayConfiguration.get('OBJECTS'):
                for noradIndex in self.activeObjects.allNoradIndices():
                    if self.displayConfiguration['OBJECTS'].get(str(noradIndex), False):
                        self._drawObject(noradIndex)
            if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_ECI_AXES', False):
                redColor, greenColor, blueColor = (1, 0, 0), (0, 1, 0), (0, 0, 1)
                self._drawAxes(redColor, greenColor, blueColor)
            if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_ECEF_AXES', False):
                glPushMatrix()
                glRotatef(self.gmstAngle, 0, 0, 1)
                redColor, greenColor, blueColor = (1, 0, 1), (1, 1, 0), (0, 1, 1)
                self._drawAxes(redColor, greenColor, blueColor)
                glPopMatrix()
        finally:
            if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
                self._drawNorthSouthAxis()
                glPushMatrix()
                glRotatef(self.gmstAngle, 0, 0, 1)
                glRotatef(90, 0, 0, 1)
                glEnable(GL_TEXTURE_2D)
                if not self.earthShader:
                    glPopMatrix()
                    return
                glUseProgram(self.earthShader)
                glActiveTexture(GL_TEXTURE0)
                glBindTexture(GL_TEXTURE_2D, self.earthTextureIndex)
                glUniform1i(glGetUniformLocation(self.earthShader, "earthDay"), 0)
                glActiveTexture(GL_TEXTURE1)
                glBindTexture(GL_TEXTURE_2D, self.lightsTextureIndex)
                glUniform1i(glGetUniformLocation(self.earthShader, "earthNight"), 1)
                sunEcef = self.sunDirectionEcef / np.linalg.norm(self.sunDirectionEcef)
                glUniform3f(glGetUniformLocation(self.earthShader, "sunDirectionEcef"), sunEcef[1], -sunEcef[0], sunEcef[2])
                glUniform1f(glGetUniformLocation(self.earthShader, "twilightWidth"), 0.15)
                glUniform1f(glGetUniformLocation(self.earthShader, "nightIntensity"), 1.0)
                gluQuadricTexture(self.sphere, GL_TRUE)
                gluSphere(self.sphere, 1.0, 96, 64)
                glUseProgram(0)
                glDisable(GL_LIGHTING)
                glActiveTexture(GL_TEXTURE1)
                glDisable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, 0)
                glActiveTexture(GL_TEXTURE0)
                glDisable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, 0)
                glPopMatrix()

    @staticmethod
    def _drawAxes(redColor, greenColor, blueColor):
        L = 2.5
        glLineWidth(3)
        glBegin(GL_LINES)
        # X – VERNAL EQUINOX
        glColor3f(*redColor)
        glVertex3f(0, 0, 0)
        glVertex3f(L, 0, 0)
        # Y – NORTH POLE
        glColor3f(*greenColor)
        glVertex3f(0, 0, 0)
        glVertex3f(0, L, 0)
        # Z – EAST
        glColor3f(*blueColor)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, L)
        glEnd()

    @staticmethod
    def _drawNorthSouthAxis():
        glLineWidth(1.5)
        glColor4f(0.6, 0.6, 0.6, 0.8)
        glPushMatrix()
        glRotatef(90, 1, 0, 0)
        glBegin(GL_LINES)
        glVertex3f(0.0, -1.2, 0.0)
        glVertex3f(0.0, 1.2, 0.0)
        glEnd()
        glPopMatrix()

    def _drawEarthGrid(self, radius=1.003):
        glColor4f(0.5, 1.0, 1.0, 1.0)
        glLineWidth(1)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        gluQuadricTexture(self.sphere, GL_FALSE)
        glPushMatrix()
        glRotatef(90, 1, 0, 0)
        gluSphere(self.sphere, radius, 48, 24)
        glPopMatrix()
        gluQuadricTexture(self.sphere, GL_TRUE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def _getObjectRenderConfiguration(self, noradIndex):
        groupName = self.activeObjects.getGroupForNoradIndex(noradIndex)
        isInSelectedGroup = (self.activeObjects.isGroupSelected and groupName == self.activeObjects.selectedGroupName)
        if isInSelectedGroup and groupName:
            group = self.activeObjects.objectGroups.get(groupName)
            if group:
                groupConfig = group.renderRules.get('3D_VIEW', {})
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

    def _drawObject(self, noradIndex):
        isSelected = noradIndex in [obj.noradIndex for obj in self.activeObjects.selectedObjects]
        isHovered = (noradIndex == self.hoveredObject)
        isActive = isSelected or isHovered
        configuration = self._getObjectRenderConfiguration(noradIndex)
        # ORBITAL PATH
        orbitColor, orbitWidth = configuration['ORBIT_PATH']['COLOR'], configuration['ORBIT_PATH']['WIDTH']
        isToggled = self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_ORBIT_PATHS', False)
        if self._shouldRender(configuration['ORBIT_PATH']['MODE'], isSelected, isToggled):
            glLineWidth(orbitWidth)
            orbitColor = (orbitColor[0] / 255, orbitColor[1] / 255, orbitColor[2] / 255, 1) if isActive else (1, 1, 1, 1)
            glColor4f(*orbitColor)
            points = self.objectOrbitData[str(noradIndex)] / self.EARTH_RADIUS
            glBegin(GL_LINE_STRIP)
            for point in points:
                glVertex3f(point[0], point[1], point[2])
            glEnd()
        # OBJECT SPOT
        spotColor = configuration['SPOT']['COLOR']
        spotColor = (spotColor[0] / 255, spotColor[1] / 255, spotColor[2] / 255, 1) if isActive else (1, 1, 1, 1)
        glPointSize(configuration['SPOT']['SIZE'])
        glColor4f(*spotColor)
        glBegin(GL_POINTS)
        position = self.objectSpotData[str(noradIndex)] / self.EARTH_RADIUS
        glVertex3f(position[0], position[1], position[2])
        glEnd()
        # OBJECT LABEL
        if isActive:
            objectName = self.objectNameData[str(noradIndex)]
            viewModel = (GLdouble * 16)()
            viewProjection = (GLdouble * 16)()
            viewPort = (GLint * 4)()
            glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
            glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
            glGetIntegerv(GL_VIEWPORT, viewPort)
            xWindow, yWindow, zWindow = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
            if zWindow <= 0.0 or zWindow >= 1.0:
                return
            if self._isBehindEarth(position) and self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
                return
            try:
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
                glRasterPos2f(xWindow + 5, yWindow + 5)
                for char in objectName:
                    glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
            finally:
                glMatrixMode(GL_PROJECTION)
                glPopMatrix()
                glMatrixMode(GL_MODELVIEW)
                glPopMatrix()

    @staticmethod
    def _shouldRender(mode: str, isSelected: bool, isToggled: bool):
        if not isToggled:
            return False
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER

    def updateData(self, positions: dict, displayConfiguration: dict):
        if not self.activeObjects:
            return
        self.displayConfiguration = displayConfiguration
        self.gmstAngle = np.rad2deg(positions['3D_VIEW']['GMST'])
        self.sunDirectionEcef = positions['3D_VIEW']['SUN_DIRECTION_ECEF']
        self.sunDirectionEci = positions['3D_VIEW']['SUN_DIRECTION_ECI']
        self.objectSpotData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['POSITION']['R_ECI'] for noradIndex in self.activeObjects.allNoradIndices() if noradIndex in positions['3D_VIEW']['OBJECTS']}
        self.objectOrbitData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['ORBIT_PATH'] for noradIndex in self.activeObjects.allNoradIndices() if noradIndex in positions['3D_VIEW']['OBJECTS']}
        self.objectNameData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['NAME'] for noradIndex in self.activeObjects.allNoradIndices() if noradIndex in positions['3D_VIEW']['OBJECTS']}
        self.update()

    def _getCameraPosition(self):
        rotX, rotY, rotFix = np.deg2rad(self.rotX), np.deg2rad(self.rotY), np.deg2rad(-90)
        cameraPosition = np.array([0, 0, 0], dtype=float)
        cameraPosition = cameraPosition + np.array([0, 0, self.zoom])
        xRotation = np.array([[1, 0, 0], [0, np.cos(-rotX), -np.sin(-rotX)], [0, np.sin(-rotX), np.cos(-rotX)]])
        yRotation = np.array([[np.cos(-rotY), 0, np.sin(-rotY)], [0, 1, 0], [-np.sin(-rotY), 0, np.cos(-rotY)]])
        invRotation = np.array([[1, 0, 0], [0, np.cos(-rotFix), -np.sin(-rotFix)], [0, np.sin(-rotFix), np.cos(-rotFix)]])
        return invRotation @ (yRotation @ (xRotation @ cameraPosition))

    def _isBehindEarth(self, position):
        cameraPosition = self._getCameraPosition()
        directionVector = position - cameraPosition
        directionVector /= np.linalg.norm(directionVector)
        b = 2 * np.dot(cameraPosition, directionVector)
        c = np.dot(cameraPosition, cameraPosition) - 1
        discriminant = b * b - 4 * c
        if discriminant < 0:
            return False
        t = (-b - np.sqrt(discriminant)) / 2.0
        distanceToObject = np.linalg.norm(position - cameraPosition) - 1e-4
        return 0 < t < distanceToObject

    def _detectHover(self, event):
        if not self.activeObjects:
            return None
        xMouse = event.x()
        yMouse = self.height() - event.y()
        self.makeCurrent()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width() / max(self.height(), 1), 0.1, 1000)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, -self.zoom)
        glRotatef(self.rotX, 1, 0, 0)
        glRotatef(self.rotY, 0, 1, 0)
        glRotatef(-90, 1, 0, 0)

        viewModel = (GLdouble * 16)()
        viewProjection = (GLdouble * 16)()
        viewPort = (GLint * 4)()
        glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
        glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
        glGetIntegerv(GL_VIEWPORT, viewPort)
        minimumDistance = float('inf')
        hovered = None
        threshold = 20.0
        for noradIndex in self.activeObjects.allNoradIndices():
            objectKey = str(noradIndex)
            if objectKey not in self.objectSpotData:
                continue
            position = self.objectSpotData[objectKey] / self.EARTH_RADIUS
            if self._isBehindEarth(position) and self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
                continue
            xWindow, yWindow, _ = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
            distance = np.sqrt((xWindow - xMouse) ** 2 + (yWindow - yMouse) ** 2)
            if distance < minimumDistance and distance < threshold:
                minimumDistance = distance
                hovered = noradIndex
        return hovered

    def mousePressEvent(self, event: QMouseEvent):
        if not self.activeObjects:
            return
        if event.button() == Qt.LeftButton:
            self.lastPosX = event.x()
            self.lastPosY = event.y()
            xMouse, yMouse = event.x(), self.height() - event.y()
            self.makeCurrent()
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, self.width() / max(self.height(), 1), 0.1, 1000)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glTranslatef(0, 0, -self.zoom)
            glRotatef(self.rotX, 1, 0, 0)
            glRotatef(self.rotY, 0, 1, 0)
            glRotatef(-90, 1, 0, 0)

            viewModel = (GLdouble * 16)()
            viewProjection = (GLdouble * 16)()
            viewPort = (GLint * 4)()
            glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
            glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
            glGetIntegerv(GL_VIEWPORT, viewPort)
            minimumDistance = float('inf')
            selectedObject = None
            threshold = 20.0
            for noradIndex in self.activeObjects.allNoradIndices():
                position = self.objectSpotData[str(noradIndex)] / self.EARTH_RADIUS
                if self._isBehindEarth(position) and self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
                    continue
                xWindow, yWindow, zWindow = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
                distance = np.sqrt((xWindow - xMouse) ** 2 + (yWindow - yMouse) ** 2)
                if distance < minimumDistance and distance < threshold:
                    minimumDistance = distance
                    selectedObject = noradIndex
            if selectedObject is not None:
                self.objectSelected.emit([selectedObject])

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton:
            dx, dy = event.x() - self.lastPosX, event.y() - self.lastPosY
            self.rotY += dx * 0.5
            self.rotX += dy * 0.5
            self.rotX = max(-89.0, min(89.0, self.rotX))
            self.lastPosX, self.lastPosY = event.x(), event.y()
            self.update()
            self.cameraChanged.emit()
            return
        # HOVER DETECTION
        hovered = self._detectHover(event)
        self.hoveredObject = hovered
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120.0
        self.zoom *= (0.9 if delta > 0 else 1.1)
        self.zoom = max(float(self.minZoom), min(float(self.maxZoom), self.zoom))
        self.update()
        self.cameraChanged.emit()

    @staticmethod
    def _loadSkyBoxTextures(faces, resolution=2048):
        textures = []
        for i, face in enumerate(faces):
            try:
                img = Image.open(face).convert("RGB")
                img = img.rotate(180).resize((resolution, resolution)) if i in [1, 5] else img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT).resize((resolution, resolution))
                imageData = np.array(img, dtype=np.uint8)
                width, height = img.size
                textureIndex = glGenTextures(1)
                glBindTexture(GL_TEXTURE_2D, textureIndex)
                glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, imageData)
                glBindTexture(GL_TEXTURE_2D, 0)
                textures.append(textureIndex)
                print(f"Skybox face {face} loaded successfully")
            except Exception as e:
                print(f"Failed to load {face}:", e)
                textures.append(0)
        return textures

    def drawSun(self):
        simulationSunDistance = 400.0
        sunRadius = simulationSunDistance * (self.SUN_RADIUS / self.EARTH_SUN_DISTANCE)
        sunDirection = self.sunDirectionEci / np.linalg.norm(self.sunDirectionEci)
        sunPosition = sunDirection * simulationSunDistance
        glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        modelView = (GLdouble * 16)()
        glGetDoublev(GL_MODELVIEW_MATRIX, modelView)
        originalModelView = list(modelView)
        modelView[12] = modelView[13] = modelView[14] = 0.0
        glLoadMatrixd(modelView)
        right = np.array([modelView[0], modelView[4], modelView[8]])
        up = np.array([modelView[1], modelView[5], modelView[9]])
        glPushMatrix()
        glTranslatef(sunPosition[0], sunPosition[1], sunPosition[2])
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)

        def drawDisk(radius, color):
            glColor4f(*color)
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(0.0, 0.0, 0.0)
            segments = 64
            for i in range(segments + 1):
                angle = 2.0 * np.pi * i / segments
                offset = (np.cos(angle) * right + np.sin(angle) * up) * radius
                glVertex3f(offset[0], offset[1], offset[2])
            glEnd()

        drawDisk(sunRadius, (1.0, 0.98, 0.9, 1.0))
        drawDisk(sunRadius * 1.5, (1.0, 0.94, 0.75, 0.5))
        drawDisk(sunRadius * 2.0, (1.0, 0.9, 0.6, 0.2))
        drawDisk(sunRadius * 2.5, (1.0, 0.7, 0.3, 0.08))
        drawDisk(sunRadius * 5.0, (1.0, 0.5, 0.2, 0.03))
        drawDisk(sunRadius * 8.0, (1.0, 0.3, 0.1, 0.01))
        glDepthMask(GL_TRUE)
        glPopMatrix()
        glLoadMatrixd(originalModelView)
        glPopAttrib()

    def drawSkybox(self, size=500.0):
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)
        glUseProgram(0)
        glEnable(GL_TEXTURE_2D)
        glColor4f(1, 1, 1, 0.5)

        # +X (right)
        glBindTexture(GL_TEXTURE_2D, self.skyboxTextures[0])
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(size, -size, -size)
        glTexCoord2f(1, 0)
        glVertex3f(size, -size, size)
        glTexCoord2f(1, 1)
        glVertex3f(size, size, size)
        glTexCoord2f(0, 1)
        glVertex3f(size, size, -size)
        glEnd()

        # -X (left)
        glBindTexture(GL_TEXTURE_2D, self.skyboxTextures[1])
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(-size, -size, size)
        glTexCoord2f(1, 0)
        glVertex3f(-size, -size, -size)
        glTexCoord2f(1, 1)
        glVertex3f(-size, size, -size)
        glTexCoord2f(0, 1)
        glVertex3f(-size, size, size)
        glEnd()

        # +Y (top)
        glBindTexture(GL_TEXTURE_2D, self.skyboxTextures[2])
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(-size, size, -size)
        glTexCoord2f(1, 0)
        glVertex3f(size, size, -size)
        glTexCoord2f(1, 1)
        glVertex3f(size, size, size)
        glTexCoord2f(0, 1)
        glVertex3f(-size, size, size)
        glEnd()

        # -Y (bottom)
        glBindTexture(GL_TEXTURE_2D, self.skyboxTextures[3])
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(-size, -size, size)
        glTexCoord2f(1, 0)
        glVertex3f(size, -size, size)
        glTexCoord2f(1, 1)
        glVertex3f(size, -size, -size)
        glTexCoord2f(0, 1)
        glVertex3f(-size, -size, -size)
        glEnd()

        # +Z (front)
        glBindTexture(GL_TEXTURE_2D, self.skyboxTextures[4])
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(-size, -size, size)
        glTexCoord2f(1, 0)
        glVertex3f(size, -size, size)
        glTexCoord2f(1, 1)
        glVertex3f(size, size, size)
        glTexCoord2f(0, 1)
        glVertex3f(-size, size, size)
        glEnd()

        # -Z (back)
        glBindTexture(GL_TEXTURE_2D, self.skyboxTextures[5])
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex3f(size, -size, -size)
        glTexCoord2f(1, 0)
        glVertex3f(-size, -size, -size)
        glTexCoord2f(1, 1)
        glVertex3f(-size, size, -size)
        glTexCoord2f(0, 1)
        glVertex3f(size, size, -size)
        glEnd()

        glBindTexture(GL_TEXTURE_2D, 0)
        glEnable(GL_DEPTH_TEST)

    def __del__(self):
        try:
            if self.isValid():
                self.makeCurrent()
                if self.earthTextureIndex:
                    glDeleteTextures([self.earthTextureIndex])
                if self.lightsTextureIndex:
                    glDeleteTextures([self.lightsTextureIndex])
                if self.sphere:
                    gluDeleteQuadric(self.sphere)
                if self.earthShader:
                    glDeleteProgram(self.earthShader)
                if self.skyboxTextures:
                    glDeleteTextures([self.skyboxTextures])
                self.doneCurrent()
        except RuntimeError:
            pass

    def setActiveObjects(self, activeObjects: ActiveObjectsModel):
        self.activeObjects = activeObjects
        self.update()

    def resetView(self):
        self.zoom, self.rotX, self.rotY = 5, 45, 225
        self.update()
        self.cameraChanged.emit()
