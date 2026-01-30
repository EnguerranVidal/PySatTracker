import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout


class Earth3DWidget(QWidget):
    EARTH_RADIUS = 6371

    def __init__(self, parent=None):
        super().__init__(parent)
        self.objectSpots, self.objectOrbits = {}, {}
        self.selectedObject, self.displayConfiguration = None, {}
        self._setupUi()
        self._setupScene()

    def _setupUi(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor('#202124')

        # Camera setup
        self.view.opts['distance'] = 15
        self.view.opts['elevation'] = 20
        self.view.opts['azimuth'] = 45

        layout.addWidget(self.view)

    def _setupScene(self):
        self.axes = gl.GLAxisItem()
        self.axes.setSize(2, 2, 2)
        self.view.addItem(self.axes)
        self._addEarth()

    def _addEarth(self):
        meshData = gl.MeshData.sphere(rows=64, cols=128, radius=1.0)
        earth = gl.GLMeshItem(meshdata=meshData, smooth=True, drawFaces=True, drawEdges=False, color=(0.2, 0.4, 0.8, 1.0), shader='shaded')
        self.view.addItem(earth)
        self.earthItem = earth

    def _removeItems(self, items):
        if not items:
            return
        if isinstance(items, list):
            for item in items:
                self.view.removeItem(item)
        else:
            self.view.removeItem(items)

    def updateView(self, positions: dict, visibleNorads: set[int], selectedNorad: int | None, displayConfiguration: dict):
        self.selectedObject, self.displayConfiguration = selectedNorad, displayConfiguration
        # REMOVING EVERYTHING NOT VISIBLE
        for noradIndex in list(self.objectSpots.keys()):
            if noradIndex not in visibleNorads:
                self._removeItems(self.objectSpots.pop(noradIndex))
                self._removeItems(self.objectOrbits.pop(noradIndex, None))
        # UPDATE EARTH DISPLAY
        self._updateEarthDisplay(positions['3D_VIEW']['GMST'])
        # UPDATING/ADDING VISIBLE OBJECTS
        for noradIndex in visibleNorads:
            if noradIndex not in positions['3D_VIEW']['OBJECTS']:
                continue
            self._updateObjectDisplay(noradIndex, positions['3D_VIEW']['OBJECTS'][noradIndex])

    def _updateObjectDisplay(self, noradIndex, noradPosition):
        noradObjectConfiguration = self.displayConfiguration['OBJECTS'][str(noradIndex)]
        # OBJECT SPOT
        spotColor, spotSize = noradObjectConfiguration['SPOT']['COLOR'], noradObjectConfiguration['SPOT']['SIZE']
        if noradIndex in self.objectSpots:
            spot = self.objectSpots[noradIndex]
            spot.setData(pos=np.array([noradPosition['POSITION']['R_ECI']]) / self.EARTH_RADIUS , size=spotSize, color=spotColor)
        else:
            spot = gl.GLScatterPlotItem(pos=np.array([noradPosition['POSITION']['R_ECI']]) / self.EARTH_RADIUS, size=spotSize, color=spotColor, pxMode=True)
            self.view.addItem(spot)
            self.objectSpots[noradIndex] = spot
        # ORBIT PATH
        if self.displayConfiguration['SHOW_ORBITS']:
            orbitColor, orbitWidth = noradObjectConfiguration['ORBIT']['COLOR'], noradObjectConfiguration['ORBIT']['WIDTH']
            orbitPositions = np.array(noradPosition['ORBIT_PATH']) / self.EARTH_RADIUS
            if noradIndex in self.objectOrbits:
                orbit = self.objectOrbits[noradIndex]
                orbit.setData(pos=orbitPositions, color=orbitColor, width=orbitWidth)
            else:
                orbit = gl.GLLinePlotItem(pos=orbitPositions, color=orbitColor, width=orbitWidth, antialias=True)
                self.view.addItem(orbit)
                self.objectOrbits[noradIndex] = orbit
        else:
            if noradIndex in self.objectOrbits:
                self._removeItems(self.objectOrbits.pop(noradIndex))


    def _updateEarthDisplay(self, gmst):
        self.earthItem.resetTransform()
        self.earthItem.rotate(np.rad2deg(gmst), 0, 0, 1)


