from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GL.shaders import compileProgram, compileShader

from PIL import Image
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QOpenGLWidget
from OpenGL.GL import *



class View3dWidget(QOpenGLWidget):
    objectSelected = pyqtSignal(list)
    EARTH_RADIUS = 6371
    EARTH_MOON_DISTANCE = 384400

    def __init__(self, parent=None):
        super().__init__(parent)
        glutInit()
        self.setMouseTracking(True)
        self.minZoom, self.maxZoom = 1.15, self.EARTH_MOON_DISTANCE / self.EARTH_RADIUS * 1.15
        self.objectSpotData, self.objectOrbitData, self.objectNameData = {}, {}, {}
        self.selectedObject, self.hoveredObject, self.visibleNorads, self.displayConfiguration = None, None, [], {}
        self.lastPosX, self.lastPosY = 0, 0
        self.zoom, self.rotX, self.rotY = 5, 45, 225
        self.earthShader = None
        self.earthTextureIndex, self.lightsTextureIndex, self.skyboxTexture = 0, 0, None
        self.gmstAngle = 0
        self.sunDirection = np.array([1, 0, 0], dtype=float)
        self.sphere = None

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # EARTH MODEL
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
            img_data = np.array(img.convert("RGB"), dtype=np.uint8)
            width, height = img.size
            self.earthTextureIndex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.earthTextureIndex)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            print("Earth texture loaded successfully")
        except Exception as e:
            print("Failed to load earth.jpg:", e)
            self.earthTextureIndex = 0
        try:
            img = Image.open("src/assets/earth/earth_lights.jpg")
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img_data = np.array(img.convert("RGB"), dtype=np.uint8)
            width, height = img.size
            self.lightsTextureIndex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.lightsTextureIndex)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            print("Earth lights texture loaded successfully")
        except Exception as e:
            print("Failed to load earth_lights.jpg:", e)
            self.lightsTextureIndex = 0
        try:
            with open("src/assets/earth/earth.vert") as f:
                vertSource = f.read()
            with open("src/assets/earth/earth.frag") as f:
                fragSource = f.read()
            self.earthShader = compileProgram(compileShader(vertSource, GL_VERTEX_SHADER), compileShader(fragSource, GL_FRAGMENT_SHADER),)
        except Exception as e:
            raise RuntimeError(f"Earth shader failed to compile/link:\n{e}")
        self.skyboxTexture = self._loadCubeMap([
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
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(0)
        glDisable(GL_LIGHTING)
        glDisable(GL_TEXTURE_2D)
        glLoadIdentity()

        # CAMERA
        glTranslatef(0, 0, -self.zoom)
        glRotatef(self.rotX, 1, 0, 0)
        glRotatef(self.rotY, 0, 1, 0)

        glRotatef(-90, 1, 0, 0)
        glActiveTexture(GL_TEXTURE1)
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        glActiveTexture(GL_TEXTURE0)
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        self.drawSkybox(size=500)
        try:
            glUseProgram(0)
            glDisable(GL_LIGHTING)
            glDisable(GL_TEXTURE_2D)
            glColor4f(1, 1, 1, 1)
            # DRAWING OBJECTS AND AXES
            for noradIndex in self.visibleNorads:
                if self.displayConfiguration['OBJECTS'].get(str(noradIndex), False):
                    self._drawObject(noradIndex)
            if self.displayConfiguration.get('SHOW_AXES', False):
                self.drawAxes()
        finally:
            if self.displayConfiguration.get('SHOW_EARTH', False):
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
                sunEcef = self.sunDirection / np.linalg.norm(self.sunDirection)
                glUniform3f(glGetUniformLocation(self.earthShader, "sunDirection"), sunEcef[1], -sunEcef[0], sunEcef[2])
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
    def drawAxes():
        L = 2.5
        glLineWidth(3)
        glBegin(GL_LINES)
        # X – VERNAL EQUINOX
        glColor3f(1, 0, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(L, 0, 0)
        # Y – NORTH POLE
        glColor3f(0, 1, 0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, L, 0)
        # Z – EAST
        glColor3f(0, 0, 1)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, L)
        glEnd()

    def _drawObject(self, noradIndex):
        isSelected = (noradIndex == self.selectedObject)
        isHovered = (noradIndex == self.hoveredObject)
        isActive = isSelected or isHovered
        noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
        # ORBITAL PATH
        orbitColor, orbitWidth = noradObjectConfiguration['ORBIT']['COLOR'] if isActive else (1, 1, 1, 1), noradObjectConfiguration['ORBIT']['WIDTH']
        if self._shouldRender(noradObjectConfiguration['ORBIT']['MODE'], isSelected, self.displayConfiguration['SHOW_ORBITS']):
            glLineWidth(orbitWidth)
            glColor4f(*orbitColor)
            glBegin(GL_LINE_STRIP)
            for point in self.objectOrbitData[str(noradIndex)]:
                point = point / self.EARTH_RADIUS
                glVertex3f(point[0], point[1], point[2])
            glEnd()
        # OBJECT SPOT
        spotColor = tuple(noradObjectConfiguration['SPOT']['COLOR']) if isActive else (1, 1, 1, 1)
        glPointSize(noradObjectConfiguration['SPOT']['SIZE'])
        glColor4f(*spotColor)
        glBegin(GL_POINTS)
        position = self.objectSpotData[str(noradIndex)] / self.EARTH_RADIUS
        glVertex3f(position[0], position[1], position[2])
        glEnd()
        # OBJECT LABEL
        if isActive:
            objectName = self.objectNameData.get(str(noradIndex), 'NONE')
            viewModel = (GLdouble * 16)()
            viewProjection = (GLdouble * 16)()
            viewPort = (GLint * 4)()
            glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
            glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
            glGetIntegerv(GL_VIEWPORT, viewPort)
            xWindow, yWindow, zWindow = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
            if zWindow <= 0.0 or zWindow >= 1.0:
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
    def _shouldRender(mode: str, isSelected: bool, isToggled: bool = True):
        if not isToggled:
            return False
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER

    def updateData(self, positions: dict, visibleNorads: set[int], selectedNorad: int | None, displayConfiguration: dict):
        self.selectedObject, self.displayConfiguration, self.visibleNorads = selectedNorad, displayConfiguration, visibleNorads
        self.gmstAngle = np.rad2deg(positions['3D_VIEW']['GMST'])
        self.sunDirection = positions['3D_VIEW']['SUN_DIRECTION_ECEF']
        self.objectSpotData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['POSITION']['R_ECI'] for noradIndex in visibleNorads}
        self.objectOrbitData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['ORBIT_PATH'] for noradIndex in visibleNorads}
        self.objectNameData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['NAME'] for noradIndex in visibleNorads}
        self.update()

    def _detectHover(self, event):
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
        for noradIndex in self.visibleNorads:
            position = self.objectSpotData[str(noradIndex)] / self.EARTH_RADIUS
            xWindow, yWindow, _ = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
            distance = np.sqrt((xWindow - xMouse) ** 2 + (yWindow - yMouse) ** 2)
            if distance < minimumDistance and distance < threshold:
                minimumDistance = distance
                hovered = noradIndex
        return hovered

    def mousePressEvent(self, event: QMouseEvent):
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
            for noradIndex in self.visibleNorads:
                position = self.objectSpotData[str(noradIndex)] / self.EARTH_RADIUS
                xWindow, yWindow, zWindow = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
                distance = np.sqrt((xWindow - xMouse) ** 2 + (yWindow - yMouse) ** 2)
                if distance < minimumDistance and distance < threshold:
                    minimumDistance = distance
                    selectedObject = noradIndex
            if selectedObject is not None:
                self.selectedObject = selectedObject
                self.objectSelected.emit([selectedObject])
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton:
            dx, dy = event.x() - self.lastPosX, event.y() - self.lastPosY
            self.rotY += dx * 0.5
            self.rotX += dy * 0.5
            self.rotX = max(-89.0, min(89.0, self.rotX))
            self.lastPosX, self.lastPosY = event.x(), event.y()
            self.update()
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

    @staticmethod
    def _loadCubeMap(faces):
        textIndex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, textIndex)
        for i, face in enumerate(faces):
            img = Image.open(face).convert("RGB")
            img_data = np.array(img, dtype=np.uint8)
            width, height = img.size
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)
        return textIndex

    def drawSkybox(self, size=50.0):
        glDepthMask(GL_FALSE)
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)

        glUseProgram(0)
        glEnable(GL_TEXTURE_CUBE_MAP)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.skyboxTexture)
        glColor4f(1, 1, 1, 0.2)
        glBegin(GL_QUADS)

        # +X
        glTexCoord3f(1, -1, -1)
        glVertex3f(size, -size, -size)
        glTexCoord3f(1, -1, 1)
        glVertex3f(size, -size, size)
        glTexCoord3f(1, 1, 1)
        glVertex3f(size, size, size)
        glTexCoord3f(1, 1, -1)
        glVertex3f(size, size, -size)

        # -X
        glTexCoord3f(-1, -1, 1)
        glVertex3f(-size, -size, size)
        glTexCoord3f(-1, -1, -1)
        glVertex3f(-size, -size, -size)
        glTexCoord3f(-1, 1, -1)
        glVertex3f(-size, size, -size)
        glTexCoord3f(-1, 1, 1)
        glVertex3f(-size, size, size)

        # +Y
        glTexCoord3f(-1, 1, -1)
        glVertex3f(-size, size, -size)
        glTexCoord3f(1, 1, -1)
        glVertex3f(size, size, -size)
        glTexCoord3f(1, 1, 1)
        glVertex3f(size, size, size)
        glTexCoord3f(-1, 1, 1)
        glVertex3f(-size, size, size)

        # -Y
        glTexCoord3f(-1, -1, 1)
        glVertex3f(-size, -size, size)
        glTexCoord3f(1, -1, 1)
        glVertex3f(size, -size, size)
        glTexCoord3f(1, -1, -1)
        glVertex3f(size, -size, -size)
        glTexCoord3f(-1, -1, -1)
        glVertex3f(-size, -size, -size)

        # +Z
        glTexCoord3f(-1, -1, 1)
        glVertex3f(-size, -size, size)
        glTexCoord3f(1, -1, 1)
        glVertex3f(size, -size, size)
        glTexCoord3f(1, 1, 1)
        glVertex3f(size, size, size)
        glTexCoord3f(-1, 1, 1)
        glVertex3f(-size, size, size)

        # -Z
        glTexCoord3f(1, -1, -1)
        glVertex3f(size, -size, -size)
        glTexCoord3f(-1, -1, -1)
        glVertex3f(-size, -size, -size)
        glTexCoord3f(-1, 1, -1)
        glVertex3f(-size, size, -size)
        glTexCoord3f(1, 1, -1)
        glVertex3f(size, size, -size)

        glEnd()

        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)
        glDisable(GL_TEXTURE_CUBE_MAP)
        glDepthMask(GL_TRUE)

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
                self.doneCurrent()
        except RuntimeError:
            pass
