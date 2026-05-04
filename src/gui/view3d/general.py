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

from src.gui.view3d.renderers import SunRenderer, EarthRenderer, MoonRenderer, RenderContext
from src.core.objects import ActiveObjectsModel


class Camera:
    def __init__(self):
        self.zoom = 5.0
        self.rotationX = 45.0
        self.rotationY = 225.0
        self.minimumZoom = 1.25
        self.maximumZoom = 1000.0

    def apply(self):
        glLoadIdentity()
        glTranslatef(0, 0, -self.zoom)
        glRotatef(self.rotationX, 1, 0, 0)
        glRotatef(self.rotationY, 0, 1, 0)

    def rotate(self, dx, dy):
        self.rotationY += dx * 0.5
        self.rotationX += dy * 0.5
        self.rotationX = max(-89.0, min(89.0, self.rotationX))

    def zoomBy(self, delta):
        self.zoom *= (0.9 if delta > 0 else 1.1)
        self.zoom = max(self.minimumZoom, min(self.maximumZoom, self.zoom))

    def getPosition(self):
        rotationX = np.deg2rad(self.rotationX)
        rotationY = np.deg2rad(self.rotationY)
        rotationFix = np.deg2rad(-90)
        camera = np.array([0, 0, self.zoom], dtype=float)
        xRotation = np.array([[1, 0, 0], [0, np.cos(-rotationX), -np.sin(-rotationX)], [0, np.sin(-rotationX), np.cos(-rotationX)]])
        yRotation = np.array([[np.cos(-rotationY), 0, np.sin(-rotationY)], [0, 1, 0], [-np.sin(-rotationY), 0, np.cos(-rotationY)]])
        fixRotation = np.array([[1, 0, 0], [0, np.cos(-rotationFix), -np.sin(-rotationFix)], [0, np.sin(-rotationFix), np.cos(-rotationFix)]])
        return fixRotation @ (yRotation @ (xRotation @ camera))


class View3dWidget(QOpenGLWidget):
    objectSelected = pyqtSignal(list)
    cameraChanged = pyqtSignal()
    EARTH_RADIUS = 6371
    EARTH_MOON_DISTANCE = 384400

    def __init__(self, parent=None):
        super().__init__(parent)
        glutInit()
        self.setMouseTracking(True)
        self.camera = Camera()
        self.objectSpotData = {}
        self.objectOrbitData = {}
        self.objectNameData = {}
        self.hoveredObject = None
        self.displayConfiguration = {}
        self.gmstAngle = 0
        self.activeObjects: ActiveObjectsModel | None = None
        self.sunDirectionEcef = np.array([1, 0, 0], dtype=float)
        self.sunDirectionEci = np.array([1, 0, 0], dtype=float)
        self.moonPositionEci = np.array([self.EARTH_MOON_DISTANCE, 0, 0], dtype=float)
        self.moonRotationMatrix = np.eye(3, dtype=float)
        self.sunRenderer = SunRenderer()
        self.earthRenderer = EarthRenderer()
        self.moonRenderer = MoonRenderer()
        self.skyboxTextures = []
        self.lastPosX = 0
        self.lastPosY = 0

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.earthRenderer.initialize()
        self.moonRenderer.initialize()
        self.skyboxTextures = self._loadSkyBoxTextures([
            "src/assets/skybox/posx.png",
            "src/assets/skybox/negx.png",
            "src/assets/skybox/posy.png",
            "src/assets/skybox/negy.png",
            "src/assets/skybox/posz.png",
            "src/assets/skybox/negz.png",
        ])

    def paintGL(self):
        if not self.activeObjects:
            return
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.camera.apply()
        modelView = (GLdouble * 16)()
        glGetDoublev(GL_MODELVIEW_MATRIX, modelView)
        context = {
            "modelView": modelView,
            "sunEci": self.sunDirectionEci,
            "sunEcef": self.sunDirectionEcef,
            "moonRot": self.moonRotationMatrix,
            "moonPos": self.moonPositionEci,
            "gmst": self.gmstAngle,
            "config": self.displayConfiguration.get('3D_VIEW', {})
        }
        self.drawSkybox()
        self.sunRenderer.update(self.sunDirectionEci)
        self.sunRenderer.render(context)
        if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
            self.earthRenderer.render(context)
            self.earthRenderer.drawAxis()
        self.moonRenderer.render(context)
        glUseProgram(0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_LIGHTING)
        if self.displayConfiguration.get('OBJECTS'):
            for noradIndex in self.activeObjects.allNoradIndices():
                if self.displayConfiguration['OBJECTS'].get(str(noradIndex), False):
                    self._drawObject(noradIndex)
        if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_ECI_AXES', False):
            self._drawAxes((1, 0, 0), (0, 1, 0), (0, 0, 1))
        if self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_ECEF_AXES', False):
            glPushMatrix()
            glRotatef(self.gmstAngle, 0, 0, 1)
            self._drawAxes((1, 0, 1), (1, 1, 0), (0, 1, 1))
            glPopMatrix()

    def updateData(self, positions: dict, displayConfiguration: dict):
        if not self.activeObjects:
            return
        self.displayConfiguration = displayConfiguration
        self.gmstAngle = np.rad2deg(positions['3D_VIEW']['GMST'])
        self.sunDirectionEcef = positions['3D_VIEW']['SUN_DIRECTION_ECEF']
        self.sunDirectionEci = positions['3D_VIEW']['SUN_DIRECTION_ECI']
        self.moonPositionEci = positions['3D_VIEW'].get('MOON_DIRECTION_ECI', np.array([self.EARTH_MOON_DISTANCE, 0, 0]))
        self.moonRotationMatrix = positions['3D_VIEW'].get('MOON_ORIENTATION', np.eye(3))
        self.objectSpotData = {str(n): positions['3D_VIEW']['OBJECTS'][n]['POSITION']['R_ECI'] for n in self.activeObjects.allNoradIndices() if n in positions['3D_VIEW']['OBJECTS']}
        self.objectOrbitData = {str(n): positions['3D_VIEW']['OBJECTS'][n]['ORBIT_PATH'] for n in self.activeObjects.allNoradIndices() if n in positions['3D_VIEW']['OBJECTS']}
        self.objectNameData = {str(n): positions['3D_VIEW']['OBJECTS'][n]['NAME'] for n in self.activeObjects.allNoradIndices() if n in positions['3D_VIEW']['OBJECTS']}
        self.update()

    def _getCameraPosition(self):
        return self.camera.getPosition()

    def _isBehindEarth(self, position):
        cameraPosition = self.camera.getPosition()
        direction = position - cameraPosition
        direction /= np.linalg.norm(direction)
        b = 2 * np.dot(cameraPosition, direction)
        c = np.dot(cameraPosition, cameraPosition) - 1
        discriminant = b * b - 4 * c
        if discriminant < 0:
            return False
        t = (-b - np.sqrt(discriminant)) / 2.0
        distanceToObject = np.linalg.norm(position - cameraPosition) - 1e-4
        return 0 < t < distanceToObject

    def mousePressEvent(self, event):
        if not self.activeObjects:
            return
        if event.button() == Qt.LeftButton:
            self.lastPosX = event.x()
            self.lastPosY = event.y()
            xMouse = event.x()
            yMouse = self.height() - event.y()
            self.makeCurrent()
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, self.width() / max(self.height(), 1), 0.1, 1000)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            self.camera.apply()
            viewModel = (GLdouble * 16)()
            viewProjection = (GLdouble * 16)()
            viewPort = (GLint * 4)()
            glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
            glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
            glGetIntegerv(GL_VIEWPORT, viewPort)
            minimumDistance = float('inf')
            selected = None
            threshold = 20.0
            for noradIndex in self.activeObjects.allNoradIndices():
                key = str(noradIndex)
                if key not in self.objectSpotData:
                    continue
                position = self.objectSpotData[key] / self.EARTH_RADIUS
                if self._isBehindEarth(position) and self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
                    continue
                xW, yW, _ = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
                distance = np.sqrt((xW - xMouse) ** 2 + (yW - yMouse) ** 2)
                if distance < minimumDistance and distance < threshold:
                    minimumDistance = distance
                    selected = noradIndex
            if selected is not None:
                self.objectSelected.emit([selected])

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            dx = event.x() - self.lastPosX
            dy = event.y() - self.lastPosY
            self.camera.rotate(dx, dy)
            self.lastPosX = event.x()
            self.lastPosY = event.y()
            self.update()
            self.cameraChanged.emit()

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
        self.camera.apply()
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
            key = str(noradIndex)
            if key not in self.objectSpotData:
                continue
            position = self.objectSpotData[key] / self.EARTH_RADIUS
            if self._isBehindEarth(position) and self.displayConfiguration.get('3D_VIEW', {}).get('SHOW_EARTH', False):
                continue
            xW, yW, _ = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
            distance = np.sqrt((xW - xMouse) ** 2 + (yW - yMouse) ** 2)
            if distance < minimumDistance and distance < threshold:
                minimumDistance = distance
                hovered = noradIndex
        return hovered

    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.camera.zoomBy(delta)
        self.update()
        self.cameraChanged.emit()

    @staticmethod
    def _drawAxes(rx, ry, rz):
        L = 2.5
        glLineWidth(3)
        glBegin(GL_LINES)
        glColor3f(*rx)
        glVertex3f(0, 0, 0)
        glVertex3f(L, 0, 0)
        glColor3f(*ry)
        glVertex3f(0, 0, 0)
        glVertex3f(0, L, 0)
        glColor3f(*rz)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, L)
        glEnd()

    def setActiveObjects(self, activeObjects):
        self.activeObjects = activeObjects
        self.update()

    def resetView(self):
        self.camera = Camera()
        self.update()
        self.cameraChanged.emit()

