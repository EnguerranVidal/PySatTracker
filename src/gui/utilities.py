import json
import numpy as np


def giveDefaultObjectViewConfig():
    return {'SPOT': {'SIZE': 10, 'COLOR': (255, 60, 0), },
            'GROUND_TRACK': {'MODE': 'WHEN_SELECTED', 'WIDTH': 2, 'COLOR': (255, 60, 0), },
            'ORBIT_PATH': {'MODE': 'WHEN_SELECTED', 'WIDTH': 2, 'COLOR': (255, 60, 0), },
            'FOOTPRINT': {'MODE': 'NEVER', 'WIDTH': 2, 'COLOR': (0, 180, 255), },
            'BEFORE': 0.5, 'BEFORE_UNIT': 'orbital periods', 'AFTER': 0.5, 'AFTER_UNIT': 'orbital periods'}

def giveDefaultGroupViewConfig():
    return {'SHARED': True, 'SOURCE': 'CUSTOM', 'SOURCE_OBJECT': None, 'CONFIG': giveDefaultObjectViewConfig()}

def generateDefaultSettingsJson(path):
    settings = {
        'WINDOW': {'MAXIMIZED': False, 'GEOMETRY': {'X': 300, 'Y': 300, 'WIDTH': 1200, 'HEIGHT': 600}},
        'ACTIVE_OBJECTS_MODEL': {'OBJECT_GROUPS': {}, 'UNGROUPED': [{"NORAD_INDEX": 25544, "NAME": "ISS (ZARYA)"}], "UNGROUPED_EXPANDED": True},
        'DATA': {'UPDATE_INTERNAL_DAYS': 2, 'AUTO_DOWNLOAD': True}, 'CURRENT_TAB': '3D_VIEW', 'TIMELINE_MODE': 'UTC',
        'VIEW_CONFIG': {'DEFAULT_CONFIG': giveDefaultObjectViewConfig(), 'OBJECTS': {'25544': giveDefaultObjectViewConfig()},
                        '2D_MAP': {'SHOW_SUN': True, 'SHOW_NIGHT': True, 'SHOW_GRID': False, 'SHOW_VERNAL': False, 'SHOW_TERMINATOR': False, 'SHOW_GROUND_TRACKS': True, 'SHOW_FOOTPRINTS': False},
                        '3D_VIEW': {'SHOW_EARTH': True, 'SHOW_ECI_AXES': False, 'SHOW_ECEF_AXES': False, 'SHOW_EARTH_GRID': False, 'ZOOM': 5, 'ROTATION': {'X': 45, 'Y': 225}, 'SHOW_ORBIT_PATHS': True}
                        },
        'PLOT_VIEW': {'TABS': {}},
    }
    with open(path, 'w') as f:
        json.dump(settings, f)

def loadSettingsJson(path):
    with open(path) as f:
        settings = json.load(f)
    return settings

def saveSettingsJson(path, settings):
    with open(path, 'w') as f:
        json.dump(settings, f)

def getKeyFromValue(dictionary, target):
    for key, value in dictionary.items():
        if value == target:
            return key
    raise KeyError(f'value {target} not found')

def upperBoundary(value):
    if value <= 0:
        return 1.0
    exponent = np.floor(np.log10(value))
    fraction = value / (10 ** exponent)
    if fraction <= 1:
        niceFraction = 1
    elif fraction <= 2:
        niceFraction = 2
    elif fraction <= 5:
        niceFraction = 5
    else:
        niceFraction = 10
    return niceFraction * (10 ** exponent)
