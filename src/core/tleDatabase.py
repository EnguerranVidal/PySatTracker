import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

from PyQt5.QtCore import QObject, pyqtSignal
from sgp4.api import Satrec, jday


class TLEDatabase:
    CELESTRAK_SOURCES = {
        "stations": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
        "active": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
        "starlink": "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle",
        "gnss": "https://celestrak.org/NORAD/elements/gp.php?GROUP=gnss&FORMAT=tle",
        "weather": "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
        "planet": "https://celestrak.org/NORAD/elements/gp.php?GROUP=planets&FORMAT=tle",
        "visual": "https://celestrak.org/NORAD/elements/gp.php?GROUP=visual&FORMAT=tle",
        "iridium": "https://celestrak.org/NORAD/elements/gp.php?GROUP=iridium&FORMAT=tle",
        "geosynchronous": "https://celestrak.org/NORAD/elements/gp.php?GROUP=geo&FORMAT=tle",
    }

    UPDATE_INTERVAL = timedelta(days=2)

    def __init__(self, tleDataDir="data/norad"):
        self.tleDataDir = tleDataDir
        self.rows = []  # <<< FAST ACCUMULATION LIST
        self.dataFrame = None
        os.makedirs(self.tleDataDir, exist_ok=True)
        self._satrecCache = {}

    def _fileNeedsUpdate(self, path):
        if not os.path.exists(path):
            return True
        lastMod = datetime.fromtimestamp(os.path.getmtime(path))
        return datetime.utcnow() - lastMod > self.UPDATE_INTERVAL

    def _download(self, tag, url):
        localPath = os.path.join(self.tleDataDir, f"{tag}.txt")
        if self._fileNeedsUpdate(localPath):
            print(f"Downloading {tag}...")
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            with open(localPath, "w", encoding="utf-8") as f:
                f.write(res.text)
        return localPath

    @staticmethod
    def _parseTLE(name, line1, line2, tag=None, source=None):
        idNorad = int(line1[2:7])

        # EPOCH CONVERSION
        epochString = line1[18:32]
        year = 2000 + int(epochString[:2]) if int(epochString[:2]) < 57 else 1900 + int(epochString[:2])
        epochBase = datetime(year, 1, 1) + timedelta(days=float(epochString[2:]) - 1)
        jdEpoch = jday(year, epochBase.month, epochBase.day, epochBase.hour, epochBase.minute, epochBase.second + epochBase.microsecond / 1e6)

        # ORBITAL ELEMENTS
        bStar = float(f"{line1[53]}0.{line1[54:59]}e{line1[59:61]}")
        inclination, eccentricity = float(line2[8:16]), float(f"0.{line2[26:33]}")
        raan, argPerigee = float(line2[17:25]), float(line2[34:42])
        meanAnomaly, meanMotion = float(line2[43:51]), float(line2[52:63])
        revNumber = int(line2[63:68])

        return {
            "OBJECT_NAME": name, "NORAD_CAT_ID": idNorad, "EPOCH": jdEpoch,
            "MEAN_MOTION": meanMotion, "ECCENTRICITY": eccentricity, "INCLINATION": inclination,
            "RA_OF_ASC_NODE": raan, "ARG_OF_PERICENTER": argPerigee, "MEAN_ANOMALY": meanAnomaly,
            "BSTAR": bStar, "REV_AT_EPOCH": revNumber, "TLE_LINE1": line1, "TLE_LINE2": line2,
            "tags": [tag] if tag else [], "source": source
        }

    def loadSource(self, tag):
        if tag not in self.CELESTRAK_SOURCES:
            raise ValueError(f"Unknown CelesTrak tag: {tag}")
        path = self._download(tag, self.CELESTRAK_SOURCES[tag])
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        for i in range(0, len(lines), 3):
            try:
                row = self._parseTLE(lines[i], lines[i+1], lines[i+2], tag, self.CELESTRAK_SOURCES[tag])
            except Exception as e:
                print(f"Skipping {lines[i] if i<len(lines) else 'unknown'}: {e}")
                continue
            self.rows.append(row)

    def finalize(self):
        self.dataFrame = pd.DataFrame(self.rows)

    def getSatrec(self, norad_id):
        if norad_id not in self._satrecCache:
            row = self.dataFrame[self.dataFrame["NORAD_CAT_ID"] == norad_id].iloc[0]
            self._satrecCache[norad_id] = Satrec.twoline2rv(row["TLE_LINE1"], row["TLE_LINE2"])
        return self._satrecCache[norad_id]


class TLELoaderWorker(QObject):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, tleDir):
        super().__init__()
        self.tleDir = tleDir

    def run(self):
        db = TLEDatabase(self.tleDir)
        total = len(TLEDatabase.CELESTRAK_SOURCES)
        step = 100 / total
        current = 0
        for tag in TLEDatabase.CELESTRAK_SOURCES:
            db.loadSource(tag)
            current += step
            self.progress.emit(int(current))
        db.finalize()
        self.finished.emit(db)