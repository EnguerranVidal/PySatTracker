from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GL import *
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


class ObjectRenderer(BaseRenderer):
    def __init__(self):
        self.vaos = {}
        self.vbos = {}
        self.counts = {}
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

    def updateObject(self, noradIndex, position, orbit, groundTrack=None, footprint=None, subPoint=None):
        position = (np.asarray(position, dtype=np.float32) / self.EARTH_RADIUS).reshape(1, 3)
        orbit = (np.asarray(orbit, dtype=np.float32) / self.EARTH_RADIUS).reshape(-1, 3)
        groundTrack = np.empty((0, 3), dtype=np.float32) if groundTrack is None else (np.asarray(groundTrack, dtype=np.float32) / self.EARTH_RADIUS).reshape(-1, 3)
        footprint = np.empty((0, 3), dtype=np.float32) if footprint is None else (np.asarray(footprint, dtype=np.float32) / self.EARTH_RADIUS).reshape(-1, 3)
        subPoint = np.empty((0, 3), dtype=np.float32) if subPoint is None else (np.asarray(subPoint, dtype=np.float32) / self.EARTH_RADIUS).reshape(-1, 3)
        if noradIndex not in self.vbos:
            self.vbos[noradIndex] = {"point": glGenBuffers(1), "orbit": glGenBuffers(1), "ground": glGenBuffers(1), "footprint": glGenBuffers(1), "subPoint": glGenBuffers(1)}
            if self.useVaos:
                self.vaos[noradIndex] = {"point": glGenVertexArrays(1), "orbit": glGenVertexArrays(1), "ground": glGenVertexArrays(1), "footprint": glGenVertexArrays(1), "subPoint": glGenVertexArrays(1)}
                for bufferName in self.vbos[noradIndex]:
                    self._configureVertexArray(self.vaos[noradIndex][bufferName], self.vbos[noradIndex][bufferName])
        uploads = {"point": position, "orbit": orbit, "ground": groundTrack, "footprint": footprint, "subPoint": subPoint}
        for bufferName, data in uploads.items():
            glBindBuffer(GL_ARRAY_BUFFER, self.vbos[noradIndex][bufferName])
            glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self.counts[noradIndex] = {"point": len(position), "orbit": len(orbit), "ground": len(groundTrack), "footprint": len(footprint), "subPoint": len(subPoint)}

    def renderObject(self, noradIndex, cameraPosition, configuration, isSelected, isHovered, displayConfiguration, objectPosition=None, objectName=""):
        if noradIndex not in self.vbos or self.shader is None:
            return
        isActive = isSelected or isHovered
        glUseProgram(self.shader)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # GROUND TRACK RENDER
        groundTrackConfig = configuration.get('GROUND_TRACK', {})
        showGroundTracks = displayConfiguration.get('SHOW_GROUND_TRACKS', True)
        if self.counts[noradIndex].get("ground", 0) > 0 and self._shouldRender(groundTrackConfig.get('MODE', 'NEVER'), isSelected, showGroundTracks):
            color = groundTrackConfig.get('COLOR', (255, 255, 255))
            color = (color[0] / 255, color[1] / 255, color[2] / 255, 0.75 if isActive else 0.35)
            glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
            glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), 1.0)
            glLineWidth(groundTrackConfig.get('WIDTH', 1))
            glEnable(GL_LINE_STIPPLE)
            glLineStipple(2, 0x00FF)
            self._bindObjectBuffer(noradIndex, "ground")
            glDrawArrays(GL_LINE_STRIP, 0, self.counts[noradIndex]["ground"])
            glDisable(GL_LINE_STIPPLE)
        # SUB-POINT CROSS RENDER
        if self.counts[noradIndex].get("subPoint", 0) > 0 and self._shouldRender(groundTrackConfig.get('MODE', 'NEVER'), isSelected, showGroundTracks):
            spotConfig = configuration.get('SPOT', {})
            color = spotConfig.get('COLOR', (255, 255, 255))
            color = (color[0] / 255, color[1] / 255, color[2] / 255, 0.95 if isActive else 0.65)
            glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
            glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), 1.0)
            glLineWidth(max(2, int(spotConfig.get('SIZE', 6) / 4)))
            self._bindObjectBuffer(noradIndex, "subPoint")
            glDrawArrays(GL_LINES, 0, self.counts[noradIndex]["subPoint"])
        # VISIBILITY FOOTPRINT RENDER
        footprintConfig = configuration.get('FOOTPRINT', {})
        showFootprints = displayConfiguration.get('SHOW_FOOTPRINTS', True)
        if self.counts[noradIndex].get("footprint", 0) > 0 and self._shouldRender(footprintConfig.get('MODE', 'NEVER'), isSelected, showFootprints):
            color = footprintConfig.get('COLOR', (255, 255, 255))
            color = (color[0] / 255, color[1] / 255, color[2] / 255, 0.95 if isActive else 0.75)
            glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
            glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), 1.0)
            glLineWidth(max(2, footprintConfig.get('WIDTH', 1)))
            glDepthFunc(GL_LEQUAL)
            self._bindObjectBuffer(noradIndex, "footprint")
            glDrawArrays(GL_LINE_LOOP, 0, self.counts[noradIndex]["footprint"])
        # ORBITAL PATH RENDER
        orbitPathConfig = configuration['ORBIT_PATH']
        showOrbits = displayConfiguration.get('SHOW_ORBIT_PATHS', False)
        if self._shouldRender(orbitPathConfig['MODE'], isSelected, showOrbits):
            color = orbitPathConfig['COLOR']
            color = (color[0] / 255, color[1] / 255, color[2] / 255, 0.8) if isActive else (1, 1, 1, 0.4)
            glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
            glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), 1.0)
            glLineWidth(orbitPathConfig['WIDTH'])
            self._bindObjectBuffer(noradIndex, "orbit")
            glDrawArrays(GL_LINE_STRIP, 0, self.counts[noradIndex]["orbit"])
            glDepthMask(GL_TRUE)
        # OBJECT SPOT RENDER
        spotCfg = configuration['SPOT']
        color = spotCfg['COLOR']
        color = ( color[0] / 255, color[1] / 255, color[2] / 255, 0.8) if isActive else (1, 1, 1, 0.4)
        glUniform4f(glGetUniformLocation(self.shader, "uColor"), *color)
        glUniform1f(glGetUniformLocation(self.shader, "uPointSize"), spotCfg['SIZE'] if isActive else 5)
        self._bindObjectBuffer(noradIndex, "point")
        glDrawArrays(GL_POINTS, 0, 1)
        self._unbindObjectBuffer()
        glUseProgram(0)
        if isActive and objectPosition is not None and objectName:
            self._renderObjectLabel(objectPosition, objectName, cameraPosition, displayConfiguration)

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

    def _renderObjectLabel(self, position, objectName, cameraPosition, displayConfiguration):
        position = np.asarray(position, dtype=float) / self.EARTH_RADIUS
        viewModel = (GLdouble * 16)()
        viewProjection = (GLdouble * 16)()
        viewport = (GLint * 4)()
        glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
        glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
        glGetIntegerv(GL_VIEWPORT, viewport)
        xWindow, yWindow, zWindow = gluProject(position[0], position[1], position[2], viewModel, viewProjection, viewport)
        if zWindow <= 0.0 or zWindow >= 1.0:
            return
        if displayConfiguration.get('SHOW_EARTH', False):
            alpha = self._earthOcclusionAlpha(position, cameraPosition, fadeWidth=0.08)
            if alpha <= 0.01:
                return
        else:
            alpha = 1.0
        self._drawScreenLabel(xWindow + 5, yWindow + 5, objectName, alpha)

    @staticmethod
    def _drawScreenLabel(xWindow, yWindow, text, alpha=1.0):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        viewport = (GLint * 4)()
        glGetIntegerv(GL_VIEWPORT, viewport)
        glOrtho(0, viewport[2], 0, viewport[3], -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        try:
            glUseProgram(0)
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(1.0, 1.0, 1.0, alpha)
            glRasterPos2f(xWindow, yWindow)
            for char in text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
        finally:
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)

    @staticmethod
    def _earthOcclusionAlpha(position, cameraPosition, fadeWidth=0.08):
        if cameraPosition is None:
            return 1.0
        position = np.asarray(position, dtype=float)
        cameraPosition = np.asarray(cameraPosition, dtype=float)
        ray = position - cameraPosition
        rayLength = np.linalg.norm(ray)
        if rayLength <= 0:
            return 1.0
        direction = ray / rayLength
        closestT = -np.dot(cameraPosition, direction)
        closestT = max(0.0, min(rayLength, closestT))
        closestPoint = cameraPosition + direction * closestT
        closestDistance = np.linalg.norm(closestPoint)
        if closestT <= 0.0 or closestT >= rayLength:
            return 1.0
        alpha = (closestDistance - 1) / fadeWidth
        return max(0.0, min(1.0, alpha))


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
        right = np.array([mv[0], mv[4], mv[8]])
        up = np.array([mv[1], mv[5], mv[9]])
        self._drawDisk(self.sunRadius * 0.85, (1.0, 0.98, 0.86, 0.75), right, up)
        self._drawDisk(self.sunRadius * 1.35, (1.0, 0.88, 0.50, 0.30), right, up)
        self._drawDisk(self.sunRadius * 2.20, (1.0, 0.62, 0.24, 0.12), right, up)
        self._drawDisk(self.sunRadius * 3.80, (1.0, 0.36, 0.12, 0.045), right, up)
        self._drawDisk(self.sunRadius * 7.00, (1.0, 0.18, 0.06, 0.018), right, up)
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
    EARTH_RADIUS = 6371
    ATMOSPHERE_THICKNESS = 50

    def __init__(self):
        self.dayEarthTexture = 0
        self.nightEarthTexture = 0
        self.cloudTexture = 0
        self.earthShader = None
        self.cloudShader = None
        self.atmosphereThickness = self.ATMOSPHERE_THICKNESS / self.EARTH_RADIUS
        self.sphere = None

    def initialize(self):
        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)
        gluQuadricTexture(self.sphere, GL_TRUE)
        self.dayEarthTexture = self._loadTexture("src/assets/earth/earth.jpg")
        self.nightEarthTexture = self._loadTexture("src/assets/earth/earth_lights.jpg")
        self.cloudTexture = self._loadTexture("src/assets/earth/clouds.jpg")
        with open("src/assets/earth/earth.vert") as f:
            earthVert = f.read()
        with open("src/assets/earth/earth.frag") as f:
            earthFrag = f.read()
        self.earthShader = compileProgram(compileShader(earthVert, GL_VERTEX_SHADER), compileShader(earthFrag, GL_FRAGMENT_SHADER))
        with open("src/assets/earth/clouds.vert") as f:
            cloudsVert = f.read()
        with open("src/assets/earth/clouds.frag") as f:
            cloudsFrag = f.read()
        self.cloudShader = compileProgram(compileShader(cloudsVert, GL_VERTEX_SHADER), compileShader(cloudsFrag, GL_FRAGMENT_SHADER))

    def render(self, context):
        if not context["config"].get("SHOW_EARTH", False):
            return
        gmstAngle = context["gmst"]
        fullJulianDate = context.get("julianDate", 2451545.0)
        sunDirectionEcef = context["sunEcef"]
        glPushMatrix()
        try:
            glRotatef(gmstAngle, 0, 0, 1)
            glRotatef(90, 0, 0, 1)
            glEnable(GL_TEXTURE_2D)
            glUseProgram(self.earthShader)
            glActiveTexture(GL_TEXTURE0)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.dayEarthTexture)
            glUniform1i(glGetUniformLocation(self.earthShader, "earthDay"), 0)
            glActiveTexture(GL_TEXTURE1)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.nightEarthTexture)
            glUniform1i(glGetUniformLocation(self.earthShader, "earthNight"), 1)
            sun = sunDirectionEcef / np.linalg.norm(sunDirectionEcef)
            glUniform3f(glGetUniformLocation(self.earthShader, "sunDirectionEcef"), sun[1], -sun[0], sun[2])
            glUniform1f(glGetUniformLocation(self.earthShader, "twilightWidth"), 0.15)
            glUniform1f(glGetUniformLocation(self.earthShader, "nightIntensity"), 1.0)
            gluSphere(self.sphere, 1.0, 160, 96)
            glUseProgram(0)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            self._drawCloudLayer(fullJulianDate, sunDirectionEcef)
            self._drawAtmosphereShell()
        finally:
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glUseProgram(0)
            glDepthMask(GL_TRUE)
            glDisable(GL_CULL_FACE)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
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

    def _drawCloudLayer(self, fullJulianDate, sunDirectionEcef: np.ndarray):
        if not self.cloudTexture or self.cloudShader is None:
            return
        daysSinceJ2000 = fullJulianDate - 2451545.0
        cloudDriftAngle = (daysSinceJ2000 * 28.8) % 360.0
        sun = sunDirectionEcef / np.linalg.norm(sunDirectionEcef)
        sunLocalDirection = np.array([sun[1], -sun[0], sun[2]], dtype=float)
        angle = np.deg2rad(-cloudDriftAngle)
        cosAngle = np.cos(angle)
        sinAngle = np.sin(angle)
        cloudSunLocal = np.array([cosAngle * sunLocalDirection[0] - sinAngle * sunLocalDirection[1], sinAngle * sunLocalDirection[0] + cosAngle * sunLocalDirection[1], sunLocalDirection[2]], dtype=float)
        glPushMatrix()
        try:
            glRotatef(cloudDriftAngle, 0, 0, 1)
            glUseProgram(self.cloudShader)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.cloudTexture)
            glUniform1i(glGetUniformLocation(self.cloudShader, "cloudTexture"), 0)
            glUniform1f(glGetUniformLocation(self.cloudShader, "cloudOpacity"), 0.8)
            glUniform1f(glGetUniformLocation(self.cloudShader, "cloudBrightnessCutoff"), 0.12)
            glUniform1f(glGetUniformLocation(self.cloudShader, "cloudNightOpacity"), 0.6)
            glUniform3f(glGetUniformLocation(self.cloudShader, "cloudColor"), 1.0, 1.0, 1.0)
            glUniform3f(glGetUniformLocation(self.cloudShader, "sunDirectionLocal"), cloudSunLocal[0], cloudSunLocal[1], cloudSunLocal[2])
            gluQuadricTexture(self.sphere, GL_TRUE)
            gluSphere(self.sphere, 1.006, 160, 96)
            glUseProgram(0)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glDepthMask(GL_TRUE)
        finally:
            glPopMatrix()

    def _drawAtmosphereShell(self):
        glPushMatrix()
        try:
            glUseProgram(0)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            glEnable(GL_CULL_FACE)
            glCullFace(GL_FRONT)
            glDepthMask(GL_FALSE)
            glColor4f(0.25, 0.48, 1.0, 0.2)
            gluQuadricTexture(self.sphere, GL_FALSE)
            gluSphere(self.sphere, 1 + self.atmosphereThickness, 160, 96)
            gluQuadricTexture(self.sphere, GL_TRUE)
            glDepthMask(GL_TRUE)
            glCullFace(GL_BACK)
            glDisable(GL_CULL_FACE)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(1.0, 1.0, 1.0, 1.0)
        finally:
            glPopMatrix()


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
        moonFixedToEci = context["moonRot"]
        sunDirectionEci = context["sunEci"]
        moonPosition = context["moonPos"] / self.EARTH_RADIUS
        sunDirectionEci = sunDirectionEci / np.linalg.norm(sunDirectionEci)
        moonTextureCorrection = np.array([[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]], dtype=float)
        eciToMoonFixed = moonFixedToEci.T
        sunDirectionMoonFixed = moonTextureCorrection.T @ (eciToMoonFixed @ sunDirectionEci)
        glPushMatrix()
        try:
            glTranslatef(*moonPosition)
            transform  = np.eye(4, dtype=np.float32)
            transform [:3, :3] = moonFixedToEci
            glMultMatrixf(transform .T.flatten())
            glRotatef(180.0, 0.0, 0.0, 1.0)
            glUseProgram(self.shader)
            glUniform3f(glGetUniformLocation(self.shader, "sunDirectionMoonFixed"), sunDirectionMoonFixed[0], sunDirectionMoonFixed[1], sunDirectionMoonFixed[2])
            glUniform1f(glGetUniformLocation(self.shader, "ambient"), 0.05)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.moonTexture)
            glUniform1i(glGetUniformLocation(self.shader, "moonTexture"), 0)
            glEnable(GL_TEXTURE_2D)
            gluSphere(self.sphere, self.moonRadius, 128, 96)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glUseProgram(0)
        finally:
            glPopMatrix()


class SkyBoxRenderer(BaseRenderer):
    def __init__(self):
        super().__init__()
        self.skyTexture = 0
        self.skyRadius = 500
        self.sphere = None
        self.textureYawOffsetDeg = 0.0
        self.texturePitchOffsetDeg = 0.0
        self.textureRollOffsetDeg = 0.0

    def initialize(self):
        self.sphere = gluNewQuadric()
        gluQuadricNormals(self.sphere, GLU_SMOOTH)
        gluQuadricTexture(self.sphere, GL_TRUE)
        gluQuadricOrientation(self.sphere, GLU_INSIDE)
        self.skyTexture = self._loadTexture("src/assets/skybox/skybox.jpg")

    def render(self, context=None):
        if not self.skyTexture or self.sphere is None:
            return
        modelView = (GLdouble * 16)()
        glGetDoublev(GL_MODELVIEW_MATRIX, modelView)
        modelViewWithoutTranslation = list(modelView)
        modelViewWithoutTranslation[12] = 0.0
        modelViewWithoutTranslation[13] = 0.0
        modelViewWithoutTranslation[14] = 0.0
        galacticToEci = self.galacticToEciMatrix()
        skyboxMatrix = np.eye(4, dtype=np.float32)
        skyboxMatrix[:3, :3] = galacticToEci
        glPushMatrix()
        try:
            glLoadMatrixd(modelViewWithoutTranslation)
            glUseProgram(0)
            glDisable(GL_LIGHTING)
            glDisable(GL_CULL_FACE)
            glDisable(GL_DEPTH_TEST)
            glDepthMask(GL_FALSE)
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.skyTexture)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            glRotatef(self.textureYawOffsetDeg, 0.0, 0.0, 1.0)
            glRotatef(self.texturePitchOffsetDeg, 1.0, 0.0, 0.0)
            glRotatef(self.textureRollOffsetDeg, 0.0, 1.0, 0.0)
            glMultMatrixf(skyboxMatrix.T.flatten())
            gluSphere(self.sphere, self.skyRadius, 128, 64)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glDepthMask(GL_TRUE)
            glEnable(GL_DEPTH_TEST)
        finally:
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)
            glDepthMask(GL_TRUE)
            glEnable(GL_DEPTH_TEST)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            glPopMatrix()

    @staticmethod
    def galacticToEciMatrix():
        return np.array([[-0.0548755604162154, 0.4941094278755837, -0.8676661490190047], [-0.8734370902348850, -0.4448296299600112, -0.1980763734312015], [-0.4838350155487132, 0.7469822444972189, 0.4559837761750669]], dtype=np.float64)

    @staticmethod
    def galacticLonLatToVector(longitudeRad, latitudeRad):
        cosLatitude = np.cos(latitudeRad)
        return np.array([cosLatitude * np.cos(longitudeRad), cosLatitude * np.sin(longitudeRad), np.sin(latitudeRad),], dtype=np.float64)

    @staticmethod
    def galacticLonLatToEci(longitudeRad, latitudeRad):
        galacticVector = SkyBoxRenderer.galacticLonLatToVector(longitudeRad, latitudeRad)
        return SkyBoxRenderer.galacticToEciMatrix() @ galacticVector


class GridRenderer(BaseRenderer):
    def __init__(self):
        self.minimumExtent = 1.0
        self.maximumExtent = 1000.0
        self.linesPerHalfAxis = 10

    def initialize(self):
        pass

    def render(self, context):
        if not context["config"].get("SHOW_XY_GRID", False):
            return
        cameraZoom = context.get("cameraZoom", 5.0)
        extent = self._niceGridExtent(cameraZoom * 2.5)
        extent = max(self.minimumExtent, min(self.maximumExtent, extent))
        step = self._gridStep(extent)
        glPushMatrix()
        try:
            glUseProgram(0)
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glLineWidth(1.0)
            glBegin(GL_LINES)
            value = -extent
            while value <= extent + 1e-9:
                isAxis = abs(value) < 1e-9
                isMajor = self._isMajorGridLine(value, step)
                if isAxis:
                    glColor4f(0.85, 0.85, 0.85, 0.55)
                elif isMajor:
                    glColor4f(0.55, 0.65, 0.75, 0.22)
                else:
                    glColor4f(0.45, 0.50, 0.55, 0.10)
                glVertex3f(-extent, value, 0.0)
                glVertex3f(extent, value, 0.0)
                glVertex3f(value, -extent, 0.0)
                glVertex3f(value, extent, 0.0)
                value += step
            glEnd()
            self._drawLabels(extent, step, context)
        finally:
            glDisable(GL_BLEND)
            glDepthMask(GL_TRUE)
            glEnable(GL_DEPTH_TEST)
            glColor4f(1.0, 1.0, 1.0, 1.0)
            glPopMatrix()


    @staticmethod
    def _niceGridExtent(value):
        if value <= 1.0:
            return 1.0
        exponent = np.floor(np.log10(value))
        base = 10 ** exponent
        scaled = value / base
        if scaled <= 2.5:
            return base
        if scaled <= 7.5:
            return 5.0 * base
        return 10 * base

    def _gridStep(self, extent):
        return extent / self.linesPerHalfAxis

    @staticmethod
    def _isMajorGridLine(value, step):
        if abs(value) < 1e-9:
            return True
        majorStep = step * 5.0
        ratio = value / majorStep
        return abs(ratio - round(ratio)) < 1e-6

    def _drawLabels(self, extent, step, context):
        viewModel = (GLdouble * 16)()
        viewProjection = (GLdouble * 16)()
        viewport = (GLint * 4)()
        glGetDoublev(GL_MODELVIEW_MATRIX, viewModel)
        glGetDoublev(GL_PROJECTION_MATRIX, viewProjection)
        glGetIntegerv(GL_VIEWPORT, viewport)
        cameraPosition = context.get("cameraPosition")
        earthOcclusionEnabled = context.get("config", {}).get("SHOW_EARTH", False)
        labelStep = step * 5.0
        value = -extent
        while value <= extent + 1e-9:
            if abs(value) > 1e-9 and self._isMajorGridLine(value, step):
                xLabelPosition, yLabelPosition = np.array([value, 0.0, 0.0], dtype=float), np.array([0.0, value, 0.0], dtype=float)
                xAlpha, yAlpha = 1.0, 1.0
                if earthOcclusionEnabled:
                    xAlpha, yAlpha = self._earthOcclusionAlpha(xLabelPosition, cameraPosition, fadeWidth=0.08), self._earthOcclusionAlpha(yLabelPosition, cameraPosition, fadeWidth=0.08)
                if xAlpha > 0.01:
                    self._drawWorldLabel(xLabelPosition[0], xLabelPosition[1], xLabelPosition[2], self._formatGridLabel(value), viewModel, viewProjection, viewport, alpha=xAlpha)
                if yAlpha > 0.01:
                    self._drawWorldLabel(yLabelPosition[0], yLabelPosition[1], yLabelPosition[2], self._formatGridLabel(value), viewModel, viewProjection, viewport, alpha=yAlpha)
            value += labelStep

    @staticmethod
    def _formatGridLabel(value):
        if abs(value) >= 10.0:
            return f"{value:.0f} Re"
        return f"{value:.1f} Re"

    @staticmethod
    def _drawWorldLabel(x, y, z, text, viewModel, viewProjection, viewport, alpha=1.0):
        xWindow, yWindow, zWindow = gluProject(x, y, z, viewModel, viewProjection, viewport)
        if zWindow <= 0.0 or zWindow >= 1.0:
            return
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, viewport[2], 0, viewport[3], -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        try:
            glUseProgram(0)
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_LIGHTING)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glColor4f(0.75, 0.80, 0.85, 0.75 * alpha)
            glRasterPos2f(xWindow + 4, yWindow + 4)
            glRasterPos2f(xWindow + 4, yWindow + 4)
            for char in text:
                glutBitmapCharacter(GLUT_BITMAP_HELVETICA_12, ord(char))
        finally:
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)

    @staticmethod
    def _earthOcclusionAlpha(position, cameraPosition, fadeWidth=0.08):
        if cameraPosition is None:
            return 1.0
        position = np.asarray(position, dtype=float)
        cameraPosition = np.asarray(cameraPosition, dtype=float)
        ray = position - cameraPosition
        rayLength = np.linalg.norm(ray)
        if rayLength <= 0:
            return 1.0
        direction = ray / rayLength
        closestT = -np.dot(cameraPosition, direction)
        closestT = max(0.0, min(rayLength, closestT))
        closestPoint = cameraPosition + direction * closestT
        closestDistance = np.linalg.norm(closestPoint)
        if closestT <= 0.0 or closestT >= rayLength:
            return 1.0
        alpha = (closestDistance - 1) / fadeWidth
        return max(0.0, min(1.0, alpha))
