import os
import json

def generateDefaultSettingsJson(path):
    settings = {
        "WINDOW": {"MAXIMIZED": False, "GEOMETRY": {"X": 300, "Y": 300, "WIDTH": 1200, "HEIGHT": 600}},
        "DATA": {"UPDATE_INTERNAL_DAYS": 2, "AUTO_DOWNLOAD": True},
        "VISUALIZATION": {"SELECTED_OBJECTS": [25544], "CURRENT_TAB": "Map"},
    }
    with open(path, "w") as f:
        json.dump(settings, f)

def loadSettingsJson(path):
    with open(path) as f:
        settings = json.load(f)
    return settings

def saveSettingsJson(path, settings):
    with open(path, "w") as f:
        json.dump(settings, f)