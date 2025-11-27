import numpy as np
from datetime import datetime
from sgp4.api import Satrec, jday


class OrbitalMechanicsEngine:
    def __init__(self):
        self.equatorialRadius = 6378.137
        self.flatteningRatio = 1.0 / 298.257223563
        self.polarRadius = self.equatorialRadius * (1 - self.flatteningRatio)
        self.e2Ellipsoid = 1 - (self.polarRadius**2) / (self.equatorialRadius**2)

    @staticmethod
    def datetimeToJd(dt: datetime):
        return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)

    def propagateSgp4(self, sat: Satrec, dt: datetime):
        jd, fr = self.datetimeToJd(dt)
        error, r, v = sat.sgp4(jd, fr)
        if error != 0:
            raise RuntimeError(f"SGP4 error code {error}")
        return np.array(r), np.array(v)

    def greenwichMeridianSiderealTime(self, dt: datetime):
        julianDate, fraction = self.datetimeToJd(dt)
        julianDate += fraction
        T = (julianDate - 2451545) / 36525
        degGmst = (280.46061837 + 360.98564736629 * (julianDate - 2451545) + 0.000387933 * T ** 2 - T ** 3 / 38710000)
        return np.deg2rad(degGmst % 360)

    def eciToEcef(self, rEci, dt: datetime):
        gmstAngle = self.greenwichMeridianSiderealTime(dt)
        rot = np.array([[np.cos(gmstAngle), np.sin(gmstAngle), 0], [-np.sin(gmstAngle), np.cos(gmstAngle), 0], [0, 0, 1]])
        return rot @ rEci

    def ecefToLongitudeLatitude(self, rEcef):
        x, y, z = rEcef
        longitude = np.arctan2(y, x)
        ep2 = (self.equatorialRadius ** 2 - self.polarRadius ** 2) / self.polarRadius ** 2
        p = np.sqrt(x * x + y * y)
        theta = np.arctan2(z * self.equatorialRadius, p * self.polarRadius)
        cosTheta, sinTheta = np.cos(theta), np.sin(theta)
        latitude = np.arctan2(z + ep2 * self.polarRadius * sinTheta * sinTheta * sinTheta, p - self.e2Ellipsoid * self.equatorialRadius * cosTheta * cosTheta * cosTheta)
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        primeVerticalRadius = self.equatorialRadius / np.sqrt(1 - self.e2Ellipsoid * sinLatitude ** 2)
        altitude = p / np.cos(latitude) - primeVerticalRadius
        return latitude, longitude, altitude

    def longitudeLatitudeToEcef(self, longitude, latitude, altitude):
        longitude, latitude = np.deg2rad(longitude), np.deg2rad(latitude)
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        cosLongitude, sinLongitude= np.cos(longitude), np.sin(longitude)
        N = self.equatorialRadius / np.sqrt(1 - self.e2Ellipsoid * sinLatitude ** 2)
        x = (N + altitude) * cosLatitude * cosLongitude
        y = (N + altitude) * cosLatitude * sinLongitude
        z = (N * (1 - self.e2Ellipsoid) + altitude) * sinLatitude
        return np.array([x, y, z])

    def ecefToEnu(self, rEcef, obsLatitude, obsLongitude, obsAltitude):
        obsPosition = self.longitudeLatitudeToEcef(obsLongitude, obsLatitude, obsAltitude)
        xDelta, yDelta, zDelta = rEcef - obsPosition
        longitude, latitude = np.deg2rad(obsLongitude), np.deg2rad(obsLatitude)
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        cosLongitude, sinLongitude= np.cos(longitude), np.sin(longitude)
        rot = np.array([[-sinLongitude, cosLongitude, 0], [-sinLatitude * cosLongitude, -sinLatitude * sinLongitude, cosLatitude], [cosLatitude * cosLongitude, cosLatitude * sinLongitude, sinLatitude]])
        enu = rot @ np.array([xDelta, yDelta, zDelta])
        return enu






