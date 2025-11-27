import pandas as pd
import requests
from datetime import datetime
from sgp4.api import Satrec
from sgp4.conveniences import jday, eci_to_geodetic


class TLEDatabase:
    def __init__(self):
        self.dataFrame = pd.DataFrame(columns=["name", "firstLine", "secondLine", "source", "updated"])

    def loadFromUrl(self, url, sourceName=None):
        res = requests.get(url)
        res.raise_for_status()
        text = res.text.strip().split("\n")
        entries = []
        for i in range(0, len(text), 3):
            name = text[i].strip()
            firstLine, secondLine = text[i + 1].strip(), text[i + 2].strip()
            entries.append({"name": name, "firstLine": firstLine, "secondLine": secondLine, "source": sourceName or url, "updated": datetime.utcnow().isoformat()})
        newDataFrame = pd.DataFrame(entries)
        self.dataFrame = pd.concat([self.dataFrame, newDataFrame], ignore_index=True)

    def getSatellite(self, name):
        row = self.dataFrame[self.dataFrame["name"] == name].iloc[0]
        return Satrec.twoline2rv(row.firstLine, row.secondLine)

    def propagate(self, name, when=None):
        if when is None:
            when = datetime.utcnow()
        sat = self.getSatellite(name)
        julianDate, fractionDate = jday(when.year, when.month, when.day, when.hour, when.minute, when.second + when.microsecond / 1e6)
        error, position, velocity = sat.sgp4(julianDate, fractionDate)
        if error != 0:
            raise RuntimeError(f"SGP4 error code {error} for '{name}'")
        lat, lon, alt = eci_to_geodetic(position[0], position[1], position[2])
        return position, velocity , lat * 180.0 / 3.1415926535, lon * 180.0 / 3.1415926535, alt

    def listSatellites(self):
        return self.dataFrame["name"].tolist()

    def filterBySource(self, source):
        return self.dataFrame[self.dataFrame["source"] == source]