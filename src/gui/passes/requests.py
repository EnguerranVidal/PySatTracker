from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QRunnable

from src.core.utilities import segmentArray
from src.core.database.tleDatabase import TLEDatabase
from src.core.engine.orbitalEngine import OrbitalMechanicsEngine


@dataclass
class VisiblePassesRequest:
    longitude: float
    latitude: float
    timeSpan: str = "Tonight"
    timeResolution: int = 60
    minElevationAngle: float = 10
    maxSunElevationAngle: float = -6
    observerAltitude: float = 0
    minMagnitude: float = 6
    maxPasses: int = 100

@dataclass
class VisiblePassResult:
    noradIndex: int
    objectName: str
    startTime: datetime
    endTime: datetime
    duration: int
    maxElevation: float
    magnitude: float
    julianDates: np.ndarray
    positions: np.ndarray
    azimuths: np.ndarray
    elevations: np.ndarray
    ranges: np.ndarray


class VisiblePassesCalculationSignals(QObject):
    progress = pyqtSignal(int)
    result = pyqtSignal(list)


class VisiblePassesCalculationTask(QRunnable):
    def __init__(self, request: VisiblePassesRequest, tleDatabase: TLEDatabase =None):
        super().__init__()
        self.request = request
        self.tleDatabase = tleDatabase
        self.engine = OrbitalMechanicsEngine()
        self.signals = VisiblePassesCalculationSignals()
        self.setAutoDelete(True)

    def run(self):
        try:
            if self.tleDatabase is None or self.tleDatabase.dataFrame is None:
                self.signals.result.emit([])
                return
            results = []
            startTime, endTime = self._timeSpanBounds(datetime.utcnow())
            fullJulianDates = self._buildFullJulianDates(startTime, endTime)
            dateTimes = self.engine.julianDateArrayToDatetimeArray(fullJulianDates)
            obsLongitude, obsLatitude, obsAltitude = self.request.longitude, self.request.latitude, self.request.observerAltitude
            noradIndices = self.tleDatabase.dataFrame["NORAD_CAT_ID"].dropna().astype(int).to_list()
            observerIsDark = self.engine.observerIsDark(obsLongitude, obsLatitude, obsAltitude, fullJulianDates, radians=False, maxSunElevationAngle=self.request.maxSunElevationAngle)
            for i, noradIndex in enumerate(noradIndices):
                try:
                    satObject = self.tleDatabase.getSatrec(noradIndex)
                    results.extend(self._calculateVisiblePassesForObject(noradIndex, satObject, fullJulianDates, dateTimes, observerIsDark))
                except Exception as e:
                    print(f"Skipping NORAD {noradIndex}: {e}")
                self.signals.progress.emit(i + 1)
            results.sort(key=lambda visiblePass: visiblePass.startTime)
            results = [r for r in results if np.isfinite(r.magnitude) and r.magnitude <= self.request.minMagnitude]
            self.signals.result.emit(results[:self.request.maxPasses])
        except Exception as e:
            print(f"Calculation error: {e}")
            self.signals.result.emit([])

    def _timeSpanBounds(self, now: datetime):
        if self.request.timeSpan == "Next 24 hours":
            return now, now + timedelta(hours=24)
        if self.request.timeSpan == "Next 48 hours":
            return now, now + timedelta(hours=48)
        end = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if end <= now:
            end += timedelta(days=1)
        return now, end

    def _buildFullJulianDates(self, startDateTime: datetime, endDateTime: datetime):
        durationSeconds = max(1, int((endDateTime - startDateTime).total_seconds()))
        resolution = max(2, durationSeconds // self.request.timeResolution + 1)
        julianDates, fractions = self.engine.datetimeToJulianDateArray(startDateTime, endDateTime, resolution=resolution)
        return julianDates + fractions

    def _calculateVisiblePassesForObject(self, noradIndex, satObject, fullJulianDates, dateTimes, observerIsDark):
        state = self.engine.satelliteState(satObject, fullJulianDates)
        enu = self.engine.ecefToEnu(state["rECEF"], self.request.longitude, self.request.latitude, self.request.observerAltitude, radians=False)
        azimuths, elevations, ranges = self.engine.enuToAzimuthElevationRange(enu)
        azimuths, elevations = np.rad2deg(azimuths), np.rad2deg(elevations)
        satelliteIsSunlit = self.engine.solarExposure(fullJulianDates, state["rECI"]) == 1
        visibleMask = ((elevations >= self.request.minElevationAngle) & satelliteIsSunlit & observerIsDark)
        magnitudes = self.engine.apparentMagnitude(fullJulianDates, state["rECI"], self.request.longitude, self.request.latitude, self.request.observerAltitude, self._standardMagnitude(noradIndex), radians=False)
        indexSegments = segmentArray(np.arange(fullJulianDates.size), visibleMask)
        objectName = self.tleDatabase.getObjectName(noradIndex)
        visiblePasses = []
        for indices in indexSegments:
            if indices.size < 2:
                continue
            passMagnitudes = magnitudes[indices]
            finiteMagnitudes = passMagnitudes[np.isfinite(passMagnitudes)]
            if finiteMagnitudes.size == 0:
                continue
            averageMagnitude = float(np.mean(finiteMagnitudes))
            segmentElevations = elevations[indices]
            maxElevationIndex = indices[int(np.argmax(segmentElevations))]
            visiblePasses.append(
                VisiblePassResult(
                    noradIndex=noradIndex,
                    objectName=objectName,
                    startTime=dateTimes[indices[0]],
                    endTime=dateTimes[indices[-1]],
                    duration=int((dateTimes[indices[-1]] - dateTimes[indices[0]]).total_seconds()),
                    maxElevation=float(elevations[maxElevationIndex]),
                    magnitude=averageMagnitude,
                    julianDates=fullJulianDates[indices],
                    positions=state["rECI"][indices],
                    azimuths=azimuths[indices],
                    elevations=elevations[indices],
                    ranges=ranges[indices]
                )
            )
        return visiblePasses

    def _standardMagnitude(self, noradIndex):
        row = self.tleDatabase.dataFrame[self.tleDatabase.dataFrame["NORAD_CAT_ID"] == noradIndex]
        if row.empty:
            return 4.5
        if "RCS_SIZE" not in row.columns:
            return 4.5
        rcsSize = str(row.iloc[0].get("RCS_SIZE", "")).upper()
        if rcsSize == "LARGE":
            return 2.0
        if rcsSize == "MEDIUM":
            return 4.0
        if rcsSize == "SMALL":
            return 6.0
        return 4.5
