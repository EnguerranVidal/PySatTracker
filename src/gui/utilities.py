import json


def giveDefaultObject2DMapConfig():
    return {'SPOT': {'SIZE': 10, 'COLOR': (255, 85, 0),},
            'GROUND_TRACK': {'MODE': 'WHEN_SELECTED','WIDTH': 1, 'COLOR': (255, 85, 0),},
            'FOOTPRINT': {'MODE': 'NEVER', 'WIDTH': 1, 'COLOR': (0, 180, 255),}}

def giveDefaultObject3DViewConfig():
    return {'SPOT': {'SIZE': 10, 'COLOR': (1, 0.33, 0, 1),}, 'ORBIT': {'MODE': 'WHEN_SELECTED', 'WIDTH': 2, 'COLOR': (1, 0.33, 0, 1),}}

def generateDefaultSettingsJson(path):
    settings = {
        'WINDOW': {'MAXIMIZED': False, 'GEOMETRY': {'X': 300, 'Y': 300, 'WIDTH': 1200, 'HEIGHT': 600}},
        'DATA': {'UPDATE_INTERNAL_DAYS': 2, 'AUTO_DOWNLOAD': True}, 'ACTIVE_OBJECTS': [25544], 'CURRENT_TAB': '3D_VIEW',
        '2D_MAP': {'DEFAULT_CONFIG': giveDefaultObject2DMapConfig(), 'OBJECTS': {'25544': giveDefaultObject2DMapConfig()}, 'SHOW_SUN': True, 'SHOW_NIGHT': True, 'SHOW_FOOTPRINT': True, 'SHOW_GROUND_TRACK': True, 'SHOW_VERNAL': False},
        '3D_VIEW': {'DEFAULT_CONFIG': giveDefaultObject3DViewConfig(), 'OBJECTS': {'25544': giveDefaultObject3DViewConfig()}, 'SHOW_ORBITS': True, 'SHOW_EARTH': True, 'SHOW_ECI_AXES': False, 'SHOW_ECEF_AXES': False, 'SHOW_EARTH_GRID': False},
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
