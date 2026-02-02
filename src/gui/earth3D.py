import imageio
import sys
from OpenGL.GLU import *
from PIL import Image
from typing import Optional

import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QMouseEvent, QWheelEvent, QSurfaceFormat
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader



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

        # GMST in degrees
        self.view.gmstAngle = np.rad2deg(positions['3D_VIEW']['GMST'])
        self.view.sunDirection = positions['3D_VIEW']['SUN_DIRECTION_ECI']
        self.view.update()


class GLViewWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.lastPosX = 0
        self.lastPosY = 0
        self.zoom = 5.0
        self.texture_id = 0

        self.rotX = 0.0
        self.rotY = 0.0
        self.gmstAngle = 0.0

        self.sunDirection = np.array([1.0, 0.0, 0.0], dtype=float)

        self.sphere = None

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)

        # Lighting: low ambient → strong day/night contrast
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, 0.95, 0.8, 1.0))
        glLightfv(GL_LIGHT0, GL_SPECULAR, (0.4, 0.4, 0.4, 1.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.03, 0.03, 0.05, 1.0))  # dim ambient

        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)

        # Load Earth texture
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
        gluPerspective(45.0, w / max(h, 1.0), 0.1, 1000.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        glTranslatef(0.0, 0.0, -self.zoom)

        # User camera orbit
        glRotatef(self.rotX, 1, 0, 0)
        glRotatef(self.rotY, 0, 1, 0)

        # Draw fixed ECI axes BEFORE any Earth rotation
        self.draw_axes()

        # Earth GMST rotation around its polar axis (Y after alignment)
        glRotatef(self.gmstAngle, 0, 1, 0)

        # Align texture so north pole points along +Y (green axis)
        glRotatef(-90.0, 1.0, 0.0, 0.0)

        # Set directional light from Sun (incoming = opposite to sunDirection)
        light_dir = self.sunDirection
        glLightfv(GL_LIGHT0, GL_POSITION, (light_dir[0], light_dir[1], light_dir[2], 0.0))

        # Draw textured Earth
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        gluQuadricTexture(self.sphere, GL_TRUE)
        glColor3f(1.0, 1.0, 1.0)
        gluSphere(self.sphere, 1.0, 96, 64)
        glDisable(GL_TEXTURE_2D)

    def draw_axes(self):
        AXIS_LENGTH = 2.5
        glLineWidth(3.0)
        glBegin(GL_LINES)
        glColor3f(1, 0, 0);
        glVertex3f(0, 0, 0);
        glVertex3f(AXIS_LENGTH, 0, 0)  # X - vernal equinox
        glColor3f(0, 1, 0);
        glVertex3f(0, 0, 0);
        glVertex3f(0, AXIS_LENGTH, 0)  # Y - north pole
        glColor3f(0, 0, 1);
        glVertex3f(0, 0, 0);
        glVertex3f(0, 0, AXIS_LENGTH)  # Z
        glEnd()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.lastPosX = event.x()
            self.lastPosY = event.y()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.LeftButton):
            return

        dx = event.x() - self.lastPosX
        dy = event.y() - self.lastPosY

        self.rotY += dx * 0.5
        self.rotX += dy * 0.5
        self.rotX = max(-89.0, min(89.0, self.rotX))

        self.lastPosX = event.x()
        self.lastPosY = event.y()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() / 120.0
        self.zoom *= (0.9 if delta > 0 else 1.1)
        self.zoom = max(0.5, min(30.0, self.zoom))
        self.update()

    def __del__(self):
        # Safe cleanup – avoid RuntimeError if context already gone
        try:
            if self.isValid():
                self.makeCurrent()
                if self.texture_id:
                    glDeleteTextures([self.texture_id])
                if self.sphere:
                    gluDeleteQuadric(self.sphere)
                self.doneCurrent()
        except RuntimeError:
            pass  # context already destroyed – safe to ignore