from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image
import numpy as np


class RenderContext:
    def __init__(self):
        self.modelView = None
        self.sunEci = None
        self.sunEcef = None
        self.moonRotation = None
        self.moonPosition = None
        self.gmst = 0.0
        self.config = {}

class BaseRenderer:
    EARTH_RADIUS = 6371
    def initialize(self):
        pass

    def render(self, context):
        pass


class ObjectRenderer(BaseRenderer):
    def __init__(self):
        self.vaos = {}
        self.vbos = {}
        self.orbitCounts = {}
        self.shader = None
        self.useVaos = False

    def initialize(self):
        with open("src/assets/objects/object.vert") as f:
            vert = f.read()
        with open("src/assets/objects/object.frag") as f:
            frag = f.read()
        vertexShader = compileShader(vert, GL_VERTEX_SHADER)
        fragmentShader = compileShader(frag, GL_FRAGMENT_SHADER)
        self.shader = glCreateProgram()
        glAttachShader(self.shader, vertexShader)
        glAttachShader(self.shader, fragmentShader)
        glBindAttribLocation(self.shader, 0, "aPos")
        glLinkProgram(self.shader)
        if glGetProgramiv(self.shader, GL_LINK_STATUS) != GL_TRUE:
            log = glGetProgramInfoLog(self.shader)
            raise RuntimeError(f"Object shader failed to link:\n{log}")
        glDeleteShader(vertexShader)
        glDeleteShader(fragmentShader)
        self.useVaos = bool(glGenVertexArrays) and bool(glBindVertexArray)

    def updateObject(self, noradIndex, position, orbit):
        position = (np.asarray(position, dtype=np.float32) / self.EARTH_RADIUS).reshape(1, 3)
        orbit = (np.asarray(orbit, dtype=np.float32) / self.EARTH_RADIUS).reshape(-1, 3)
        if noradIndex not in self.vbos:
            self.vbos[noradIndex] = {"point": glGenBuffers(1), "orbit": glGenBuffers(1)}
            if self.useVaos:
                self.vaos[noradIndex] = {"point": glGenVertexArrays(1), "orbit": glGenVertexArrays(1)}
                self._configureVertexArray(self.vaos[noradIndex]["point"], self.vbos[noradIndex]["point"])
                self._configureVertexArray(self.vaos[noradIndex]["orbit"], self.vbos[noradIndex]["orbit"])
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[noradIndex]["point"])
        glBufferData(GL_ARRAY_BUFFER, position.nbytes, position, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[noradIndex]["orbit"])
        glBufferData(GL_ARRAY_BUFFER, orbit.nbytes, orbit, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.orbitCounts[noradIndex] = len(orbit)

    def renderObject(self, noradId, configuration, isSelected, isHovered, displayConfiguration):
        if noradId not in self.vbos:
            return
        isActive = isSelected or isHovered
        glUseProgram(self.shader)
        # ORBITAL PATH RENDER
        orbitPathConfig = configuration['ORBIT_PATH']
        showOrbits = displayConfiguration.get('SHOW_ORBIT_PATHS', False)
        if self._shouldRender(orbitPathConfig['MODE'], isSelected, showOrbits):
            color = orbitPathConfig['COLOR']
            color = (color[0] / 255, color[1] / 255, color[2] / 255, 1.0) if isActive else (1, 1, 1, 1)
            glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
            glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), 1.0)
            glLineWidth(orbitPathConfig['WIDTH'])
            self._bindObjectBuffer(noradId, "orbit")
            glDrawArrays(GL_LINE_STRIP, 0, self.orbitCounts[noradId])
        # OBJECT SPOT RENDER
        spotCfg = configuration['SPOT']
        color = spotCfg['COLOR']
        color = ( color[0] / 255, color[1] / 255, color[2] / 255, 1.0) if isActive else (1, 1, 1, 1)
        glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
        glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), spotCfg['SIZE'])
        self._bindObjectBuffer(noradId, "point")
        glDrawArrays(GL_POINTS, 0, 1)
        self._unbindObjectBuffer()
        glUseProgram(0)

    @staticmethod
    def _configureVertexArray(vao, vbo):
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def _bindObjectBuffer(self, noradId, bufferName):
        if self.useVaos:
            glBindVertexArray(self.vaos[noradId][bufferName])
            return
        glBindBuffer(GL_ARRAY_BUFFER, self.vbos[noradId][bufferName])
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)

    def _unbindObjectBuffer(self):
        if self.useVaos:
            glBindVertexArray(0)
            return
        glDisableVertexAttribArray(0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    @staticmethod
    def _shouldRender(mode: str, isSelected: bool, isToggled: bool):
        if not isToggled:
            return False
        if mode == "ALWAYS":
            return True
        if mode == "WHEN_SELECTED":
            return isSelected
        return False  # NEVER


class SunRenderer(BaseRenderer):
    SUN_RADIUS = 696340
    EARTH_SUN_DISTANCE = 149600000

    def __init__(self, simulationSunDistance: float = 400.0):
        self.simulationSunDistance = simulationSunDistance
        self.sunRadius = self.simulationSunDistance * (self.SUN_RADIUS / self.EARTH_SUN_DISTANCE)
        self.sunDirection = np.array([1, 0, 0], dtype=float)
        self.sunPosition = self.sunDirection * self.simulationSunDistance

    def update(self, sunDirection: np.ndarray):
        self.sunDirection = sunDirection / np.linalg.norm(sunDirection)
        self.sunPosition = self.sunDirection * self.simulationSunDistance

    def render(self, context):
        modelView = context["modelView"]
        glPushMatrix()
        mv = list(modelView)
        mv[12] = mv[13] = mv[14] = 0.0
        glLoadMatrixd(mv)
        glTranslatef(*self.sunPosition)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glDepthMask(GL_FALSE)
        right, up = np.array([mv[0], mv[4], mv[8]]), np.array([mv[1], mv[5], mv[9]])
        self._drawDisk(self.sunRadius, (1.0, 0.98, 0.9, 1.0), right, up)
        self._drawDisk(self.sunRadius * 1.5, (1.0, 0.94, 0.75, 0.5), right, up)
        self._drawDisk(self.sunRadius * 2.0, (1.0, 0.9, 0.6, 0.2), right, up)
        self._drawDisk(self.sunRadius * 2.5, (1.0, 0.7, 0.3, 0.08), right, up)
        self._drawDisk(self.sunRadius * 5.0, (1.0, 0.5, 0.2, 0.03), right, up)
        self._drawDisk(self.sunRadius * 8.0, (1.0, 0.3, 0.1, 0.01), right, up)
        glDepthMask(GL_TRUE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glPopMatrix()

    @staticmethod
    def _drawDisk(radius, color, right, up):
        glColor4f(*color)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(0,0,0)
        for i in range(65):
            angle = 2*np.pi*i/64
            offset = (np.cos(angle)*right + np.sin(angle)*up)*radius
            glVertex3f(*offset)
        glEnd()


class EarthRenderer(BaseRenderer):
    def __init__(self):
        self.dayEarthTexture = 0
        self.nightEarthTexture = 0
        self.shader = None
        self.sphere = None

    def initialize(self):
        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)
        gluQuadricTexture(self.sphere, GL_TRUE)
        self.dayEarthTexture = self._loadTexture("src/assets/earth/earth.jpg")
        self.nightEarthTexture = self._loadTexture("src/assets/earth/earth_lights.jpg")
        with open("src/assets/earth/earth.vert") as f:
            vert = f.read()
        with open("src/assets/earth/earth.frag") as f:
            frag = f.read()
        self.shader = compileProgram(compileShader(vert, GL_VERTEX_SHADER), compileShader(frag, GL_FRAGMENT_SHADER))

    def render(self, context):
        if not context["config"].get("SHOW_EARTH", False):
            return
        gmstAngle = context["gmst"]
        sunDirectionEcef = context["sunEcef"]
        glPushMatrix()
        try:
            glRotatef(gmstAngle, 0, 0, 1)
            glRotatef(90, 0, 0, 1)
            glEnable(GL_TEXTURE_2D)
            glUseProgram(self.shader)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.dayEarthTexture)
            glUniform1i(glGetUniformLocation(self.shader, "earthDay"), 0)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, self.nightEarthTexture)
            glUniform1i(glGetUniformLocation(self.shader, "earthNight"), 1)
            sun = sunDirectionEcef / np.linalg.norm(sunDirectionEcef)
            glUniform3f(glGetUniformLocation(self.shader, "sunDirectionEcef"), sun[1], -sun[0], sun[2])
            glUniform1f(glGetUniformLocation(self.shader, "twilightWidth"), 0.15)
            glUniform1f(glGetUniformLocation(self.shader, "nightIntensity"), 1.0)
            gluSphere(self.sphere, 1.0, 96, 64)
            glUseProgram(0)
            glDisable(GL_TEXTURE_2D)
        finally:
            glPopMatrix()

    def drawGrid(self, context):
        gmstAngle = context["gmst"]
        glPushMatrix()
        try:
            glRotatef(gmstAngle, 0, 0, 1)
            glColor4f(0.5, 1.0, 1.0, 1.0)
            glLineWidth(1)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            gluQuadricTexture(self.sphere, GL_FALSE)
            glPushMatrix()
            gluSphere(self.sphere, 1.003, 48, 24)
            glPopMatrix()
            gluQuadricTexture(self.sphere, GL_TRUE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        finally:
            glPopMatrix()

    @staticmethod
    def drawAxis():
        glPushMatrix()
        try:
            glLineWidth(1.5)
            glColor4f(0.6, 0.6, 0.6, 0.8)
            glRotatef(90, 1, 0, 0)
            glBegin(GL_LINES)
            glVertex3f(0.0, -1.2, 0.0)
            glVertex3f(0.0, 1.2, 0.0)
            glEnd()
        finally:
            glPopMatrix()

    @staticmethod
    def _loadTexture(path):
        image = Image.open(path).transpose(Image.FLIP_TOP_BOTTOM)
        data = np.array(image.convert("RGB"), dtype=np.uint8)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.width, image.height, 0, GL_RGB, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glGenerateMipmap(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        return texture


class MoonRenderer(BaseRenderer):
    MOON_RADIUS = 1737
    EARTH_RADIUS = 6371

    def __init__(self):
        self.moonTexture = 0
        self.moonRadius = self.MOON_RADIUS / self.EARTH_RADIUS
        self.shader = None
        self.sphere = None

    def initialize(self):
        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)
        gluQuadricTexture(self.sphere, GL_TRUE)
        self.moonTexture = self._loadTexture("src/assets/moon/moon.jpg")
        with open("src/assets/moon/moon.vert") as f:
            vert = f.read()
        with open("src/assets/moon/moon.frag") as f:
            frag = f.read()
        self.shader = compileProgram(compileShader(vert, GL_VERTEX_SHADER), compileShader(frag, GL_FRAGMENT_SHADER))

    def render(self, context):
        moonRotationMatrix = context["moonRot"]
        sunDirectionEci = context["sunEci"]
        moonPosition = context["moonPos"] / self.EARTH_RADIUS
        sunDirectionMoonFixed = moonRotationMatrix.T @ (sunDirectionEci / np.linalg.norm(sunDirectionEci))
        glPushMatrix()
        try:
            glTranslatef(*moonPosition)
            mat = np.eye(4, dtype=np.float32)
            mat[:3, :3] = moonRotationMatrix
            glMultMatrixf(mat.T.flatten())
            glUseProgram(self.shader)
            glUniform3f(glGetUniformLocation(self.shader, "sunDirectionMoonFixed"), *sunDirectionMoonFixed)
            glUniform1f(glGetUniformLocation(self.shader, "ambient"), 0.05)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.moonTexture)
            glUniform1i(glGetUniformLocation(self.shader, "moonTexture"), 0)
            glEnable(GL_TEXTURE_2D)
            gluSphere(self.sphere, self.moonRadius, 64, 64)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glUseProgram(0)
        finally:
            glPopMatrix()

    @staticmethod
    def _loadTexture(path):
        image = Image.open(path).transpose(Image.FLIP_TOP_BOTTOM)
        data = np.array(image.convert("RGB"), dtype=np.uint8)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.width, image.height, 0, GL_RGB, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glGenerateMipmap(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        return texture
