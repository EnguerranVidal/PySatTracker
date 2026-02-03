from OpenGL.GLU import *
from PIL import Image
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent, QWheelEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QOpenGLWidget
from OpenGL.GL import *



class View3dWidget(QWidget):
    EARTH_RADIUS = 6371

    def __init__(self, parent=None):
        super().__init__(parent)
        self.objectSpots, self.objectOrbits = {}, {}
        self.selectedObject, self.displayConfiguration = None, {}
        self._setupUi()

    def _setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = GLViewWidget(self)
        layout.addWidget(self.view)

    def updateView(self, positions: dict, visibleNorads: set[int], selectedNorad: int | None, displayConfiguration: dict):
        self.selectedObject, self.displayConfiguration = selectedNorad, displayConfiguration
        self.view.gmstAngle = np.rad2deg(positions['3D_VIEW']['GMST'])
        self.view.sunDirection = positions['3D_VIEW']['SUN_DIRECTION_ECI']
        self.view.update()


class GLViewWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lastPosX, self.lastPosY = 0, 0
        self.zoom = 5
        self.texture_id = 0
        self.rotX, self.rotY = 0, 0
        self.gmstAngle = 0
        self.sunDirection = np.array([1, 0, 0], dtype=float)
        self.sphere = None

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)

        # LIGHTING
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
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
        light_dir = self.sunDirection / np.linalg.norm(self.sunDirection)
        glLightfv(GL_LIGHT0, GL_POSITION, (light_dir[0], light_dir[2], -light_dir[1], 0))
        self.drawAxes()
        glPushMatrix()

        # EARTH GMST ROTATION
        glRotatef(-90, 1, 0, 0)
        glRotatef(self.gmstAngle, 0, 0, 1)
        glRotatef(90, 0, 0, 1)

        # DRAW EARTH
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        gluQuadricTexture(self.sphere, GL_TRUE)
        glColor3f(1, 1.0, 1.0)
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

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.lastPosX = event.x()
            self.lastPosY = event.y()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.LeftButton):
            return
        dx, dy = event.x() - self.lastPosX, event.y() - self.lastPosY
        self.rotY += dx * 0.5
        self.rotX += dy * 0.5
        self.rotX = max(-89.0, min(89.0, self.rotX))
        self.lastPosX, self.lastPosY = event.x(), event.y()
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