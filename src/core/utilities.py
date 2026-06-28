import json
import numpy as np
from PyQt5.QtGui import QSurfaceFormat

from src.core.settings import UiSettings
from src.core.config import *


def giveDefaultObjectViewConfig():
    return ObjectViewConfig().toDict()


def giveDefaultGroupViewConfig():
    return GroupViewConfig().toDict()


def giveDefaultTextureConfig():
    return {'EARTH_DAY': {'SELECTED': 'Default', 'OPTIONS': {'Default': {'PATH': 'src/assets/textures/earth_day/Default.jpg', 'SOURCE': 'https://www.solarsystemscope.com/textures/', 'IS_DEFAULT': True}}},
            'EARTH_NIGHT': {'SELECTED': 'Default', 'OPTIONS': {'Default': {'PATH': 'src/assets/textures/earth_night/Default.jpg', 'SOURCE': 'https://www.solarsystemscope.com/textures/', 'IS_DEFAULT': True}}},
            'EARTH_CLOUDS': {'SELECTED': 'Default', 'OPTIONS': {'Default': {'PATH': 'src/assets/textures/earth_clouds/Default.jpg', 'SOURCE': 'https://www.solarsystemscope.com/textures/', 'IS_DEFAULT': True}}},
            'SKYBOX': {'SELECTED': 'Default', 'OPTIONS': {'Default': {'PATH': 'src/assets/textures/skybox/Default.jpg', 'SOURCE': 'https://svs.gsfc.nasa.gov/4851/', 'IS_DEFAULT': True, 'COORDINATES': 'CELESTIAL'}}},
            'MOON': {'SELECTED': 'Default', 'OPTIONS': {'Default': {'PATH': 'src/assets/textures/moon/Default.jpg', 'SOURCE': 'https://www.solarsystemscope.com/textures/', 'IS_DEFAULT': True}}}}

def generateDefaultSettingsJson(path):
    settings = UiSettings().toDict()
    with open(path, 'w') as f:
        json.dump(settings, f)

def loadSettingsJson(path):
    with open(path) as f:
        settings = json.load(f)
    return UiSettings.fromDict(settings)

def saveSettingsJson(path, settings):
    if isinstance(settings, UiSettings):
        settings = settings.toDict()
    with open(path, "w") as f:
        json.dump(settings, f)

def getSelectedTextureOption(textureConfig, category):
    categoryConfig = textureConfig.get(category, {})
    selectedName = categoryConfig.get('SELECTED', 'Default')
    options = categoryConfig.get('OPTIONS', {})
    return options.get(selectedName) or options.get('Default') or {}

def getSelectedTexturePath(textureConfig, category, fallbackPath):
    option = getSelectedTextureOption(textureConfig, category)
    return option.get('PATH', fallbackPath)

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

def configureOpenGLFormat():
    surfaceFormat = QSurfaceFormat()
    surfaceFormat.setDepthBufferSize(24)
    surfaceFormat.setStencilBufferSize(8)
    surfaceFormat.setSamples(8)
    surfaceFormat.setProfile(QSurfaceFormat.CompatibilityProfile)
    QSurfaceFormat.setDefaultFormat(surfaceFormat)

def segmentArray(arr: np.ndarray, mask: np.ndarray, dim=0):
    mask = np.asarray(mask, dtype=bool)
    padded = np.r_[False, mask, False]
    changes = np.diff(padded.astype(np.int8))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1) - 1
    return [ arr[tuple(slice(s, e + 1) if i == dim else slice(None) for i in range(arr.ndim))] for s, e in zip(starts, ends)]
