import json

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature


def giveDefaultObject2DMapConfig():
    return {'SPOT': {'SIZE': 10, 'COLOR': (255, 85, 0),},
            'GROUND_TRACK': {'MODE': 'WHEN_SELECTED','WIDTH': 1, 'COLOR': (255, 85, 0),},
            'FOOTPRINT': {'MODE': 'NEVER', 'WIDTH': 1, 'COLOR': (0, 180, 255),}}

def giveDefaultObject3DViewConfig():
    return {'SPOT': {'SIZE': 10, 'COLOR': (1, 0.33, 0, 1),}, 'ORBIT': {'MODE': 'WHEN_SELECTED', 'WIDTH': 2, 'COLOR': (1, 0.33, 0, 1),}}

def generateDefaultSettingsJson(path):
    settings = {
        'WINDOW': {'MAXIMIZED': False, 'GEOMETRY': {'X': 300, 'Y': 300, 'WIDTH': 1200, 'HEIGHT': 600}},
        'DATA': {'UPDATE_INTERNAL_DAYS': 2, 'AUTO_DOWNLOAD': True},
        'VISUALIZATION': {'ACTIVE_OBJECTS': [25544], 'CURRENT_TAB': '2D_MAP'},
        '2D_MAP': {'DEFAULT_CONFIG': giveDefaultObject2DMapConfig(), 'OBJECTS': {'25544': giveDefaultObject2DMapConfig()}, 'SHOW_SUN': True, 'SHOW_NIGHT': True, 'SHOW_FOOTPRINT': True, 'SHOW_GROUND_TRACK': True, 'SHOW_VERNAL': False},
        '3D_VIEW': {'DEFAULT_CONFIG': giveDefaultObject3DViewConfig(), 'OBJECTS': {'25544': giveDefaultObject3DViewConfig()}, 'SHOW_ORBITS': True, 'SHOW_EARTH': True, 'SHOW_AXES': True},
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

def generateWorldMap(filename='world_map.png', width=8192, height=4096, dpi=300):
    width //= 2
    height //= 2
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_global()
    ax.axis('off')
    ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor='#001122')
    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='#2c2c2c')
    ax.add_feature(cfeature.BORDERS.with_scale('50m'), edgecolor='white', linewidth=0.6)
    ax.coastlines(resolution='50m', color='white', linewidth=0.8)
    plt.savefig(filename, bbox_inches='tight', pad_inches=0, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'Saved {filename}')


if __name__ == '__main__':
    generateWorldMap(filename='../assets/earth/world_map.png')