from OpenGL.GLU import *
from OpenGL.GLUT import *
from PIL import Image
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QOpenGLWidget
from OpenGL.GL import *



class View3dWidget(QOpenGLWidget):
    objectSelected = pyqtSignal(list)
    EARTH_RADIUS = 6371
    def __init__(self, parent=None):
        super().__init__(parent)
        glutInit()
        self.objectSpotData, self.objectOrbitData, self.objectNameData = {}, {}, {}
        self.selectedObject, self.hoveredObject, self.visibleNorads, self.displayConfiguration = None, None, [], {}
        self.lastPosX, self.lastPosY = 0, 0
        self.zoom, self.rotX, self.rotY = 5, 45, 225
        self.texture_id = 0
        self.gmstAngle = 0
        self.sunDirection = np.array([1, 0, 0], dtype=float)
        self.sphere = None

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_POINT_SMOOTH)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # LIGHTING
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.05, 0.05, 0.05, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (1, 1, 1, 1))

        # EARTH MODEL
        glEnable(GL_TEXTURE_2D)
        glShadeModel(GL_SMOOTH)
        glClearColor(0, 0, 0, 0)
        glClearDepth(1)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)
        try:
            img = Image.open("src/assets/earth.jpg")
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img_data = np.array(img.convert("RGB"), dtype=np.uint8)
            width, height = img.size
            self.texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, img_data)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glGenerateMipmap(GL_TEXTURE_2D)
            print("Earth texture loaded successfully")
        except Exception as e:
            print("Failed to load earth.jpg:", e)
            self.texture_id = 0

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / max(h, 1), 0.1, 1000)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # CAMERA
        glTranslatef(0, 0, -self.zoom)
        glRotatef(self.rotX, 1, 0, 0)
        glRotatef(self.rotY, 0, 1, 0)

        # SUN DIRECTION
        lightDirection = self.sunDirection / np.linalg.norm(self.sunDirection)
        glLightfv(GL_LIGHT0, GL_POSITION, (lightDirection[0], lightDirection[2], -lightDirection[1], 0))
        glPushMatrix()
        glRotatef(-90, 1, 0, 0)
        try:
            # DRAWING OBJECTS AND AXES
            for noradIndex in self.visibleNorads:
                self._drawObject(noradIndex)
            if self.displayConfiguration['SHOW_AXES']:
                self.drawAxes()
            glRotatef(self.gmstAngle, 0, 0, 1)
            glRotatef(90, 0, 0, 1)

        finally:
            if self.displayConfiguration['SHOW_EARTH']:
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, self.texture_id)
                gluQuadricTexture(self.sphere, GL_TRUE)
                glColor3f(1, 1, 1)
                gluSphere(self.sphere, 1.0, 96, 64)
                glDisable(GL_TEXTURE_2D)
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
            try:
                glMatrixMode(GL_PROJECTION)
                glPushMatrix()
                glLoadIdentity()
                glOrtho(0, viewPort[2], 0, viewPort[3], -1, 1)
                glMatrixMode(GL_MODELVIEW)
                glPushMatrix()
                glLoadIdentity()
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
        self.sunDirection = positions['3D_VIEW']['SUN_DIRECTION_ECI']
        self.objectSpotData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['POSITION']['R_ECI'] for noradIndex in visibleNorads}
        self.objectOrbitData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['ORBIT_PATH'] for noradIndex in visibleNorads}
        self.objectNameData = {str(noradIndex): positions['3D_VIEW']['OBJECTS'][noradIndex]['NAME'] for noradIndex in visibleNorads}
        self.update()

    def _detectHover(self, event):
        xMouse = event.x()
        yMouse = event.y()
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
        threshold = 15.0
        for noradIndex in self.visibleNorads:
            position = self.objectSpotData[str(noradIndex)] / self.EARTH_RADIUS
            xWindow, yWindow, _ = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewPort)
            distance = np.hypot(xWindow - xMouse, yWindow - yMouse)
            if distance < threshold and distance < minimumDistance:
                minimumDistance = distance
                hovered = noradIndex
        return hovered

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.lastPosX = event.x()
            self.lastPosY = event.y()
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

            xMouse, yMouse = event.x(), self.height() - event.y()
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
                dist = np.sqrt((xWindow - xMouse) ** 2 + (yWindow - yMouse) ** 2)
                if dist < minimumDistance and dist < threshold:
                    minimumDistance = dist
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
        if hovered != self.hoveredObject:
            self.hoveredObject = hovered
            if hovered is not None:
                print(f"Hovering NORAD: {hovered}")
            self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120.0
        self.zoom *= (0.9 if delta > 0 else 1.1)
        self.zoom = max(0.5, min(30.0, self.zoom))
        self.update()

    def __del__(self):
        try:
            if self.isValid():
                self.makeCurrent()
                if self.texture_id:
                    glDeleteTextures([self.texture_id])
                if self.sphere:
                    gluDeleteQuadric(self.sphere)
                self.doneCurrent()
        except RuntimeError:
            pass