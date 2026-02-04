import numpy as np
from datetime import datetime, timedelta
from sgp4.api import Satrec, jday


class OrbitalMechanicsEngine:
    def __init__(self):
        self.equatorialRadius = 6378.137
        self.flatteningRatio = 1.0 / 298.257223563
        self.polarRadius = self.equatorialRadius * (1 - self.flatteningRatio)
        self.e2Ellipsoid = 1 - (self.polarRadius**2) / (self.equatorialRadius**2)
        self.earthGravParameter = 398600.4418

    @staticmethod
    def datetimeToJd(dt: datetime):
        return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)

    @staticmethod
    def datetimeToJulianCenturies(dt: datetime):
        return (dt - datetime(2000, 1, 1, 12, 0)) / timedelta(days=1) / 36525.0

    @staticmethod
    def arcsecToDegrees(arcsec):
        return arcsec / 3600.0

    def propagateSgp4(self, sat: Satrec, dt: datetime):
        jd, fr = self.datetimeToJd(dt)
        error, r, v = sat.sgp4(jd, fr)
        if error != 0:
            raise RuntimeError(f'SGP4 error code {error}')
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

    def ecefToEci(self, rEcef, dt: datetime):
        gmstAngle = self.greenwichMeridianSiderealTime(dt)
        rot = np.array([[np.cos(gmstAngle), -np.sin(gmstAngle), 0], [np.sin(gmstAngle), np.cos(gmstAngle), 0], [0, 0, 1]])
        return rot @ rEcef

    def ecefToLongitudeLatitude(self, rEcef, radians=True):
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
        if not radians:
            return np.rad2deg(longitude), np.rad2deg(latitude), altitude
        return longitude, latitude, altitude

    def longitudeLatitudeToEcef(self, longitude, latitude, altitude, radians=True):
        if not radians:
            longitude, latitude = np.deg2rad(longitude), np.deg2rad(latitude)
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        cosLongitude, sinLongitude= np.cos(longitude), np.sin(longitude)
        N = self.equatorialRadius / np.sqrt(1 - self.e2Ellipsoid * sinLatitude ** 2)
        x = (N + altitude) * cosLatitude * cosLongitude
        y = (N + altitude) * cosLatitude * sinLongitude
        z = (N * (1 - self.e2Ellipsoid) + altitude) * sinLatitude
        return np.array([x, y, z])

    def ecefToEnu(self, rEcef, obsLongitude, obsLatitude, obsAltitude, radians=True):
        if not radians:
            obsLongitude, obsLatitude = np.deg2rad(obsLongitude), np.deg2rad(obsLatitude)
        obsPosition = self.longitudeLatitudeToEcef(obsLongitude, obsLatitude, obsAltitude)
        xDelta, yDelta, zDelta = rEcef - obsPosition
        longitude, latitude = np.deg2rad(obsLongitude), np.deg2rad(obsLatitude)
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        cosLongitude, sinLongitude= np.cos(longitude), np.sin(longitude)
        rot = np.array([[-sinLongitude, cosLongitude, 0], [-sinLatitude * cosLongitude, -sinLatitude * sinLongitude, cosLatitude], [cosLatitude * cosLongitude, cosLatitude * sinLongitude, sinLatitude]])
        enu = rot @ np.array([xDelta, yDelta, zDelta])
        return enu

    @staticmethod
    def enuToAzimuthElevation(enu):
        E, N, U = enu
        slantRange = np.sqrt(E ** 2 + N ** 2 + U ** 2)
        elevation = np.arcsin(U / slantRange)
        azimuth = np.arctan2(E, N)
        if azimuth < 0:
            azimuth += 2 * np.pi
        return azimuth, elevation, slantRange

    def satelliteState(self, sat: Satrec, dt: datetime, obsLongitude=None, obsLatitude=None, obsAltitude=None, radians=True):
        if not radians:
            obsLongitude, obsLatitude = np.deg2rad(obsLongitude), np.deg2rad(obsLatitude)
        rEci, vEci = self.propagateSgp4(sat, dt)
        rEcef = self.eciToEcef(rEci, dt)
        longitude, latitude, altitude = self.ecefToLongitudeLatitude(rEcef)
        state = {'rECI': rEci, 'vECI': vEci, 'rECEF': rEcef, 'altitude': altitude, 'latitude': latitude, 'longitude': longitude}
        if obsLongitude is not None:
            enu = self.ecefToEnu(rEcef, obsLongitude, obsLatitude, obsAltitude)
            state['azimuth'], state['elevation'], state['range'] = self.enuToAzimuthElevation(enu)
        return state

    def satelliteVisibilityFootPrint(self, state, nbPoints=360):
        longitude, latitude, altitude = state['longitude'], state['latitude'], state['altitude']
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        localRadius = np.sqrt((self.equatorialRadius ** 2 * cosLatitude ** 2 + self.polarRadius ** 2 * sinLatitude ** 2) / (cosLatitude ** 2 + sinLatitude ** 2))
        angleHorizon = np.arccos(localRadius / (localRadius + altitude))
        circlePoints = np.linspace(0, 2 * np.pi, nbPoints)
        cosHorizon, sinHorizon = np.cos(angleHorizon), np.sin(angleHorizon)
        circleLatitude = np.arcsin(sinLatitude * cosHorizon + cosLatitude * sinHorizon * np.cos(circlePoints))
        circleLongitude = longitude + np.arctan2(np.sin(circlePoints) * sinHorizon * cosLatitude, cosHorizon - sinLatitude * np.sin(circleLatitude))
        circleLongitude = (circleLongitude + np.pi) % (2 * np.pi) - np.pi
        return circleLongitude, circleLatitude

    def satelliteOrbitPath(self, sat: Satrec, dt: datetime, nbPoints=361, nbPast=0.5, nbFuture=0.5):
        orbitalPeriod = self.orbitalPeriod(sat)
        times = np.linspace( - nbPast * orbitalPeriod, nbFuture * orbitalPeriod, nbPoints)
        positionsEci = np.empty((nbPoints, 3))
        for i, offset in enumerate(times):
            t =  dt + timedelta(seconds=float(offset))
            rEci, _ = self.propagateSgp4(sat, t)
            positionsEci[i, :] = rEci
        return positionsEci

    def satelliteGroundTrack(self, sat: Satrec, dt: datetime, nbPoints=361, nbPast=0.5, nbFuture=0.5):
        orbitalPeriod = self.orbitalPeriod(sat)
        times = np.linspace( - nbPast * orbitalPeriod, nbFuture * orbitalPeriod, nbPoints)
        longitudes, latitudes, altitudes = np.empty(nbPoints), np.empty(nbPoints), np.empty(nbPoints)
        for i, offset in enumerate(times):
            t =  dt + timedelta(seconds=float(offset))
            rEci, _ = self.propagateSgp4(sat, t)
            rEcef = self.eciToEcef(rEci, t)
            longitudes[i], latitudes[i], altitudes[i] = self.ecefToLongitudeLatitude(rEcef)
        longitudes = (longitudes + np.pi) % (2 * np.pi) - np.pi
        return longitudes, latitudes, altitudes

    @staticmethod
    def orbitalPeriod(sat: Satrec):
        meanMotion = sat.no / 60
        return 2 * np.pi / meanMotion

    def semiMajorAxis(self, sat: Satrec):
        meanMotion = sat.no / 60
        return np.cbrt(self.earthGravParameter / meanMotion ** 2)

    @staticmethod
    def tleOrbitalElements(sat: Satrec):
        return {'inclination': sat.inclo, 'RAAN': sat.nodeo, 'arg_perigee': sat.argpo, 'eccentricity': sat.ecco}

    @staticmethod
    def flightPathAngle(rVec, vVec):
        rNorm, vNorm = np.linalg.norm(rVec), np.linalg.norm(vVec)
        if rNorm == 0 or vNorm == 0:
            return 0.0
        return np.arcsin(np.dot(rVec, vVec) / (rNorm * vNorm))

    def subSolarPoint(self, dt: datetime, radians=True):
        sunEciPosition = self.solarDirectionEci(dt)
        sunDeclination, sunRightAscension = np.arcsin(sunEciPosition[2]), np.arctan2(sunEciPosition[1], sunEciPosition[0])
        gmstAngle = self.greenwichMeridianSiderealTime(dt)
        subSolarLongitude = sunRightAscension - gmstAngle
        subSolarLongitude = (subSolarLongitude + np.pi) % (2 * np.pi) - np.pi
        if not radians:
            return np.rad2deg(subSolarLongitude), np.rad2deg(sunDeclination), 1
        return subSolarLongitude, sunDeclination, 1

    def solarDirectionEci(self, dt: datetime):
        T = self.datetimeToJulianCenturies(dt)
        meanLongitude = 280.46646 + T * (36000.76983 + T * 0.0003032)
        meanAnomaly = np.deg2rad(357.52911 + T * (35999.05029 - T * 0.0001537))
        earthOrbitEccentricity = 0.016708634 - T * (0.000042037 + T * 0.0000001267)
        centerEquation = np.deg2rad((1.914602 - T * (0.004817 + T * 0.000014)) * np.sin(meanAnomaly) + (0.019993 - T * 0.000101) * np.sin(2 * meanAnomaly) + 0.000289 * np.sin(3 * meanAnomaly))
        trueLongitude = meanLongitude + np.rad2deg(centerEquation)
        trueAnomaly = meanAnomaly + centerEquation
        sunDistance = 1.000001018 * (1 - earthOrbitEccentricity ** 2) / (1 + earthOrbitEccentricity * np.cos(trueAnomaly))
        moonOrbitAscendingNode = np.deg2rad(125.04 - 1934.136 * T)
        eclipticLongitude = np.deg2rad(trueLongitude - 0.00569 - 0.00478 * np.sin(moonOrbitAscendingNode))
        eclipticObliquity = np.deg2rad(23 + (26 + (21.448 - T * (46.8150 + T * (0.00059 - T * 0.001813))) / 60) / 60 + 0.00256 * np.cos(moonOrbitAscendingNode))
        # ECI POSITION VECTOR
        x = sunDistance * np.cos(eclipticLongitude)
        y = sunDistance * np.sin(eclipticLongitude) * np.cos(eclipticObliquity)
        z = sunDistance * np.sin(eclipticLongitude) * np.sin(eclipticObliquity)
        r = np.array([x, y, z])
        return r / np.linalg.norm(r)

    def terminatorCurve(self, dt: datetime, nbPoints=361, radians=True):
        sunLongitude, sunLatitude, _ = self.subSolarPoint(dt, radians=True)
        longitudes = np.linspace(-np.pi, np.pi, nbPoints)
        latitudes = np.arctan(-np.cos(longitudes - sunLongitude) / np.tan(sunLatitude))
        if not radians:
            return np.rad2deg(longitudes), np.rad2deg(latitudes)
        return longitudes, latitudes

    def getVernalSubPoint(self, dt: datetime, radians=True):
        vernalUnitVectorEci = np.array([1, 0, 0])
        sunEciPosition = self.solarDirectionEci(dt)
        vernalLongitude = np.arctan2(vernalUnitVectorEci[1], vernalUnitVectorEci[0]) - self.greenwichMeridianSiderealTime(dt)
        if not radians:
            return np.rad2deg(vernalLongitude), np.rad2deg(0)
        return vernalLongitude, 0



