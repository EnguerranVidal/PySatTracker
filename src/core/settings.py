from src.core.objects import ActiveObjectsModel
from src.core.config import *


def _defaultActiveObjectsModel():
    return ActiveObjectsModel.fromDict({"OBJECT_GROUPS": {}, "UNGROUPED": [{"NORAD_INDEX": 25544, "NAME": "ISS (ZARYA)"}], "UNGROUPED_EXPANDED": True})


def _activeObjectsModelFromDict(data):
    return ActiveObjectsModel.fromDict(data or {"OBJECT_GROUPS": {}, "UNGROUPED": [{"NORAD_INDEX": 25544, "NAME": "ISS (ZARYA)"}], "UNGROUPED_EXPANDED": True})


@dataclass
class DataSettings:
    updateIntervalDays: int = 2
    autoDownload: bool = True

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(updateIntervalDays=int(data.get("UPDATE_INTERNAL_DAYS", 2)), autoDownload=bool(data.get("AUTO_DOWNLOAD", True)))

    def toDict(self):
        return {"UPDATE_INTERNAL_DAYS": self.updateIntervalDays, "AUTO_DOWNLOAD": self.autoDownload,}


@dataclass
class WindowGeometry:
    x: int = 300
    y: int = 300
    width: int = 1200
    height: int = 600

    @classmethod
    def fromDict(cls, data=None):
        data = data or {}
        return cls(data.get("X", 300), data.get("Y", 300), data.get("WIDTH", 1200), data.get("HEIGHT", 600))

    def toDict(self):
        return {"X": self.x, "Y": self.y, "WIDTH": self.width, "HEIGHT": self.height}


@dataclass
class WindowSettings:
    maximized: bool = False
    geometry: WindowGeometry = field(default_factory=WindowGeometry)

    @classmethod
    def fromDict(cls, data=None):
        data = data or {}
        return cls(bool(data.get("MAXIMIZED", False)), WindowGeometry.fromDict(data.get("GEOMETRY")))

    def toDict(self):
        return {"MAXIMIZED": self.maximized, "GEOMETRY": self.geometry.toDict()}


@dataclass
class UiSettings:
    window: WindowSettings = field(default_factory=WindowSettings)
    activeObjectsModel: ActiveObjectsModel = field(default_factory=_defaultActiveObjectsModel)
    data: DataSettings = field(default_factory=DataSettings)
    currentTab: str = "3D_VIEW"
    timelineMode: str = "UTC"
    viewConfig: ViewConfig = field(default_factory=ViewConfig)
    plotView: dict[str, Any] = field(default_factory=lambda: {"TABS": {}})

    @classmethod
    def fromDict(cls, data: dict | None):
        data = data or {}
        return cls(
            window=WindowSettings.fromDict(data.get("WINDOW")),
            activeObjectsModel=_activeObjectsModelFromDict(data.get("ACTIVE_OBJECTS_MODEL")),
            data=DataSettings.fromDict(data.get("DATA")),
            currentTab=data.get("CURRENT_TAB", "3D_VIEW"),
            timelineMode=data.get("TIMELINE_MODE", "UTC"),
            viewConfig=ViewConfig.fromDict(data.get("VIEW_CONFIG")),
            plotView=data.get("PLOT_VIEW", {"TABS": {}}),
        )

    def toDict(self):
        return {
            "WINDOW": self.window.toDict(),
            "ACTIVE_OBJECTS_MODEL": self.activeObjectsModel.toDict(),
            "DATA": self.data.toDict(),
            "CURRENT_TAB": self.currentTab,
            "TIMELINE_MODE": self.timelineMode,
            "VIEW_CONFIG": self.viewConfig.toDict(),
            "PLOT_VIEW": self.plotView,
        }
