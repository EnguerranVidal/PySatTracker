from dataclasses import asdict, dataclass, field
from typing import Any


Color = tuple[int, int, int]


@dataclass
class RenderFeatureConfig:
    mode: str = "WHEN_SELECTED"
    width: int = 2
    color: Color = (255, 60, 0)

    @classmethod
    def fromDict(cls, data: dict | None, defaultColor: Color = (255, 60, 0)):
        data = data or {}
        return cls(mode=data.get("MODE", "WHEN_SELECTED"), width=int(data.get("WIDTH", 2)), color=tuple(data.get("COLOR", defaultColor)))

    def toDict(self):
        return {"MODE": self.mode, "WIDTH": self.width, "COLOR": list(self.color)}


@dataclass
class SpotConfig:
    size: int = 6
    color: Color = (255, 60, 0)

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(size=int(data.get("SIZE", 6)), color=tuple(data.get("COLOR", (255, 60, 0))))

    def toDict(self):
        return {"SIZE": self.size, "COLOR": list(self.color)}


@dataclass
class ObjectViewConfig:
    spot: SpotConfig = field(default_factory=SpotConfig)
    groundTrack: RenderFeatureConfig = field(default_factory=RenderFeatureConfig)
    orbitPath: RenderFeatureConfig = field(default_factory=RenderFeatureConfig)
    footprint: RenderFeatureConfig = field( default_factory=lambda: RenderFeatureConfig(color=(0, 180, 255)))
    before: float = 0.5
    beforeUnit: str = "orbital periods"
    after: float = 0.5
    afterUnit: str = "orbital periods"

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(
            spot=SpotConfig.fromDict(data.get("SPOT")),
            groundTrack=RenderFeatureConfig.fromDict(data.get("GROUND_TRACK")),
            orbitPath=RenderFeatureConfig.fromDict(data.get("ORBIT_PATH")),
            footprint=RenderFeatureConfig.fromDict(data.get("FOOTPRINT"), defaultColor=(0, 180, 255)),
            before=float(data.get("BEFORE", 0.5)),
            beforeUnit=data.get("BEFORE_UNIT", "orbital periods"),
            after=float(data.get("AFTER", 0.5)),
            afterUnit=data.get("AFTER_UNIT", "orbital periods"),
        )

    def toDict(self):
        return {
            "SPOT": self.spot.toDict(),
            "GROUND_TRACK": self.groundTrack.toDict(),
            "ORBIT_PATH": self.orbitPath.toDict(),
            "FOOTPRINT": self.footprint.toDict(),
            "BEFORE": self.before,
            "BEFORE_UNIT": self.beforeUnit,
            "AFTER": self.after,
            "AFTER_UNIT": self.afterUnit,
        }


@dataclass
class GroupViewConfig:
    shared: bool = True
    source: str = "CUSTOM"
    sourceObject: int | None = None
    config: ObjectViewConfig = field(default_factory=ObjectViewConfig)

    @classmethod
    def fromDict(cls, data=None):
        data = data or {}
        sourceObject = data.get("SOURCE_OBJECT")
        return cls(
            shared=bool(data.get("SHARED", True)),
            source=data.get("SOURCE", "CUSTOM"),
            sourceObject=int(sourceObject) if sourceObject is not None else None,
            config=ObjectViewConfig.fromDict(data.get("CONFIG")),
        )

    def toDict(self):
        return {"SHARED": self.shared, "SOURCE": self.source, "SOURCE_OBJECT": self.sourceObject, "CONFIG": self.config.toDict()}


@dataclass
class Map2DViewConfig:
    showSun: bool = True
    showNight: bool = True
    showGrid: bool = False
    showVernal: bool = False
    showTerminator: bool = False
    showGroundTracks: bool = True
    showFootprints: bool = False

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(
            showSun=bool(data.get("SHOW_SUN", True)),
            showNight=bool(data.get("SHOW_NIGHT", True)),
            showGrid=bool(data.get("SHOW_GRID", False)),
            showVernal=bool(data.get("SHOW_VERNAL", False)),
            showTerminator=bool(data.get("SHOW_TERMINATOR", False)),
            showGroundTracks=bool(data.get("SHOW_GROUND_TRACKS", True)),
            showFootprints=bool(data.get("SHOW_FOOTPRINTS", False)),
        )

    def toDict(self):
        return {
            "SHOW_SUN": self.showSun,
            "SHOW_NIGHT": self.showNight,
            "SHOW_GRID": self.showGrid,
            "SHOW_VERNAL": self.showVernal,
            "SHOW_TERMINATOR": self.showTerminator,
            "SHOW_GROUND_TRACKS": self.showGroundTracks,
            "SHOW_FOOTPRINTS": self.showFootprints,
        }

@dataclass
class Rotation3DConfig:
    x: float = 45
    y: float = 225

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(x=float(data.get("X", 45)), y=float(data.get("Y", 225)))

    def toDict(self):
        return {"X": self.x, "Y": self.y}


@dataclass
class View3DConfig:
    showEarth: bool = True
    showEciAxes: bool = False
    showEcefAxes: bool = False
    showEarthGrid: bool = False
    showEquatorialGrid: bool = False
    zoom: float = 5
    rotation: Rotation3DConfig = field(default_factory=Rotation3DConfig)
    showOrbitPaths: bool = True
    showGroundTracks: bool = True
    showFootprints: bool = False

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(
            showEarth=bool(data.get("SHOW_EARTH", True)),
            showEciAxes=bool(data.get("SHOW_ECI_AXES", False)),
            showEcefAxes=bool(data.get("SHOW_ECEF_AXES", False)),
            showEarthGrid=bool(data.get("SHOW_EARTH_GRID", False)),
            showEquatorialGrid=bool(data.get("SHOW_EQUATORIAL_GRID", False)),
            zoom=float(data.get("ZOOM", 5)),
            rotation=Rotation3DConfig.fromDict(data.get("ROTATION")),
            showOrbitPaths=bool(data.get("SHOW_ORBIT_PATHS", True)),
            showGroundTracks=bool(data.get("SHOW_GROUND_TRACKS", True)),
            showFootprints=bool(data.get("SHOW_FOOTPRINTS", False)),
        )

    def toDict(self):
        return {
            "SHOW_EARTH": self.showEarth,
            "SHOW_ECI_AXES": self.showEciAxes,
            "SHOW_ECEF_AXES": self.showEcefAxes,
            "SHOW_EARTH_GRID": self.showEarthGrid,
            "SHOW_EQUATORIAL_GRID": self.showEquatorialGrid,
            "ZOOM": self.zoom,
            "ROTATION": self.rotation.toDict(),
            "SHOW_ORBIT_PATHS": self.showOrbitPaths,
            "SHOW_GROUND_TRACKS": self.showGroundTracks,
            "SHOW_FOOTPRINTS": self.showFootprints,
        }


@dataclass
class VisiblePassesConfig:
    lastLongitude: float = -74.0060
    lastLatitude: float = 40.7128
    lastTimeSpan: str = "Tonight"
    minElevationAngle: float = 20.0
    maxSunElevationAngle: float = -6.0
    timeResolution: int = 60
    observerAltitude: float = 0.0
    locationType: str = "City"
    minMagnitude: float = 3.0
    maxPasses: int = 100

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(
            lastLongitude=float(data.get("LAST_LONGITUDE", -74.0060)),
            lastLatitude=float(data.get("LAST_LATITUDE", 40.7128)),
            lastTimeSpan=data.get("LAST_TIME_SPAN", "Tonight"),
            minElevationAngle=float(data.get("MIN_ELEVATION", 20.0)),
            maxSunElevationAngle=float(data.get("SUN_MAX_ELEVATION", -6.0)),
            timeResolution=int(data.get("RESOLUTION", 60)),
            observerAltitude=float(data.get("OBSERVER_ALTITUDE", 0.0)),
            locationType=data.get("LOCATION_TYPE", "City"),
            minMagnitude=float(data.get("MIN_MAGNITUDE", 3.0)),
            maxPasses=int(data.get("MAX_PASSES", 100)),
        )

    def toDict(self):
        return {
            "LAST_LONGITUDE": self.lastLongitude,
            "LAST_LATITUDE": self.lastLatitude,
            "LAST_TIME_SPAN": self.lastTimeSpan,
            "MIN_ELEVATION": self.minElevationAngle,
            "SUN_MAX_ELEVATION": self.maxSunElevationAngle,
            "RESOLUTION": self.timeResolution,
            "OBSERVER_ALTITUDE": self.observerAltitude,
            "LOCATION_TYPE": self.locationType,
            "MIN_MAGNITUDE": self.minMagnitude,
            "MAX_PASSES": self.maxPasses,
        }


@dataclass
class ViewConfig:
    defaultConfig: ObjectViewConfig = field(default_factory=ObjectViewConfig)
    objects: dict[str, ObjectViewConfig] = field(default_factory=lambda: {"25544": ObjectViewConfig()})
    textures: dict[str, Any] = field(default_factory=dict)
    map2d: Map2DViewConfig = field(default_factory=Map2DViewConfig)
    view3d: View3DConfig = field(default_factory=View3DConfig)
    passes: VisiblePassesConfig = field(default_factory=VisiblePassesConfig)

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(
            defaultConfig=ObjectViewConfig.fromDict(data.get("DEFAULT_CONFIG")),
            objects={str(noradIndex): ObjectViewConfig.fromDict(config) for noradIndex, config in data.get("OBJECTS", {}).items()},
            textures=data.get("TEXTURES", {}),
            map2d=Map2DViewConfig.fromDict(data.get("2D_MAP")),
            view3d=View3DConfig.fromDict(data.get("3D_VIEW")),
            passes=VisiblePassesConfig.fromDict(data.get("PASSES")),
        )

    def toDict(self):
        return {
            "DEFAULT_CONFIG": self.defaultConfig.toDict(),
            "OBJECTS": {noradIndex: config.toDict() for noradIndex, config in self.objects.items()},
            "TEXTURES": self.textures,
            "2D_MAP": self.map2d.toDict(),
            "3D_VIEW": self.view3d.toDict(),
            "PASSES": self.passes.toDict(),
        }
