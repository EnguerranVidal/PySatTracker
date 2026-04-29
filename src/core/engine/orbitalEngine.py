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
    def arcsecToDegrees(arcsec):
        return arcsec / 3600.0

    @staticmethod
    def _ensureArray(x, vector=False):
        x = np.asarray(x)
        if vector:
            if x.ndim == 1:
                return x.reshape(1, -1), True
            return x, False
        else:
            if x.ndim == 0:
                return x.reshape(1), True
            return x, False

    @staticmethod
    def _maybeScalar(x, wasScalar):
        if wasScalar:
            return x[0]
        return x

    @staticmethod
    def datetimeToJulianDate(dt: datetime):
        return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)

    @staticmethod
    def dateTimeToJulianCenturies(dt: datetime):
        return (dt - datetime(2000, 1, 1, 12, 0)) / timedelta(days=1) / 36525.0

    @staticmethod
    def julianDateToJulianCenturies(fullJulianDate):
        return (fullJulianDate - 2451545) / 36525.0

    @staticmethod
    def separateJulianDate(fullJulianDate):
        julianDate = np.floor(fullJulianDate)
        fraction = fullJulianDate - julianDate
        return julianDate, fraction

    def datetimeToJulianDateArray(self, startDateTime: datetime, endDateTime: datetime, resolution=361):
        startJulianDate, startFraction = self.datetimeToJulianDate(startDateTime)
        endJulianDate, endFraction = self.datetimeToJulianDate(endDateTime)
        startJulianTotal, endJulianTotal = startJulianDate + startFraction, endJulianDate + endFraction
        fullJulianDates = np.linspace(startJulianTotal, endJulianTotal, resolution)
        julianDates = np.floor(fullJulianDates)
        fractions = fullJulianDates - julianDates
        return julianDates, fractions

    def julianDateArrayToDatetimeArray(self, fullJulianDates):
        julianDates, fractions = self.separateJulianDate(fullJulianDates)
        dateTimes = []
        for julianDate, fraction in zip(julianDates, fractions):
            totalJulianDate = julianDate + fraction
            dt = datetime(2000, 1, 1, 12) + timedelta(days=totalJulianDate - 2451545)
            dateTimes.append(dt)
        return np.array(dateTimes)

    def propagateSgp4(self, sat: Satrec, fullJulianDates):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        julianDates, fractions = self.separateJulianDate(fullJulianDates)
        if scalar:
            error, r, v = sat.sgp4(julianDates[0], fractions[0])
            if error != 0:
                raise RuntimeError(f"SGP4 error {error}")
            return np.array(r), np.array(v)
        error, r, v = sat.sgp4_array(julianDates, fractions)
        if np.any(error != 0):
            bad = np.where(error != 0)[0]
            raise RuntimeError(f"SGP4 errors at {bad}: {error[bad]}")
        return r, v

    def greenwichMeridianSiderealTime(self, fullJulianDates):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        T = self.julianDateToJulianCenturies(fullJulianDates)
        degGmst = (280.46061837 + 360.98564736629 * (fullJulianDates - 2451545) + 0.000387933 * T ** 2 - T ** 3 / 38710000)
        return self._maybeScalar(np.deg2rad(degGmst % 360), scalar)

    def eciToEcef(self, rEci, fullJulianDates):
        rEci = np.asarray(rEci)
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        if rEci.ndim == 1:
            rEci = rEci.reshape(1, 3)
        gmstAngles = self.greenwichMeridianSiderealTime(fullJulianDates)
        cosGmst, sinGmst = np.cos(gmstAngles), np.sin(gmstAngles)
        x, y, z = rEci[:, 0], rEci[:, 1], rEci[:, 2]
        xEcef, yEcef, zEcef = cosGmst * x + sinGmst * y, -sinGmst * x + cosGmst * y, z
        rEcef = np.stack([xEcef, yEcef, zEcef], axis=1)
        return self._maybeScalar(rEcef, scalar)

    def ecefToEci(self, rEcef, fullJulianDates):
        rEcef = np.asarray(rEcef)
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        if rEcef.ndim == 1:
            rEcef = rEcef.reshape(1, 3)
        gmstAngles = self.greenwichMeridianSiderealTime(fullJulianDates)
        cosGmst, sinGmst = np.cos(gmstAngles), np.sin(gmstAngles)
        x, y, z = rEcef[:, 0], rEcef[:, 1], rEcef[:, 2]
        xEci, yEci, zEci = cosGmst * x - sinGmst * y, sinGmst * x + cosGmst * y, z
        rEci = np.stack([xEci, yEci, zEci], axis=1)
        return self._maybeScalar(rEci, scalar)

    def ecefToLongitudeLatitude(self, rEcef, radians=True):
        rEcef = np.asarray(rEcef)
        scalar = (rEcef.ndim == 1)
        if scalar:
            rEcef = rEcef.reshape(1, 3)
        x, y, z = rEcef[:, 0], rEcef[:, 1], rEcef[:, 2]
        longitudes = np.arctan2(y, x)
        ep2 = (self.equatorialRadius ** 2 - self.polarRadius ** 2) / self.polarRadius ** 2
        p = np.sqrt(x * x + y * y)
        theta = np.arctan2(z * self.equatorialRadius, p * self.polarRadius)
        cosTheta, sinTheta = np.cos(theta), np.sin(theta)
        latitudes = np.arctan2(z + ep2 * self.polarRadius * sinTheta * sinTheta * sinTheta, p - self.e2Ellipsoid * self.equatorialRadius * cosTheta * cosTheta * cosTheta)
        cosLatitude, sinLatitude = np.cos(latitudes), np.sin(latitudes)
        primeVerticalRadius = self.equatorialRadius / np.sqrt(1 - self.e2Ellipsoid * sinLatitude ** 2)
        altitudes = p / np.cos(latitudes) - primeVerticalRadius
        if not radians:
            longitudes, latitudes = np.rad2deg(longitudes), np.rad2deg(latitudes)
        return self._maybeScalar(longitudes, scalar), self._maybeScalar(latitudes, scalar), self._maybeScalar(altitudes, scalar)

    def longitudeLatitudeToEcef(self, longitudes, latitudes, altitudes, radians=True):
        if not radians:
            longitudes, latitudes = np.deg2rad(longitudes), np.deg2rad(latitudes)
        cosLatitude, sinLatitude = np.cos(latitudes), np.sin(latitudes)
        cosLongitude, sinLongitude= np.cos(longitudes), np.sin(longitudes)
        N = self.equatorialRadius / np.sqrt(1 - self.e2Ellipsoid * sinLatitude ** 2)
        x = (N + altitudes) * cosLatitude * cosLongitude
        y = (N + altitudes) * cosLatitude * sinLongitude
        z = (N * (1 - self.e2Ellipsoid) + altitudes) * sinLatitude
        return np.stack([x, y, z], axis=-1)

    def ecefToEnu(self, rEcef, obsLongitude, obsLatitude, obsAltitude, radians=True):
        rEcef = np.asarray(rEcef)
        scalar = (rEcef.ndim == 1)
        if scalar:
            rEcef = rEcef.reshape(1, 3)
        if not radians:
            obsLongitude, obsLatitude = np.deg2rad(obsLongitude), np.deg2rad(obsLatitude)
        observationPosition = np.asarray(self.longitudeLatitudeToEcef(obsLongitude, obsLatitude, obsAltitude))
        if observationPosition.ndim == 1:
            observationPosition = observationPosition.reshape(1, 3)
        if observationPosition.shape[0] == 1 and rEcef.shape[0] > 1:
            observationPosition = np.repeat(observationPosition, rEcef.shape[0], axis=0)
        observationToObject = rEcef - observationPosition
        x, y, z = observationToObject[:, 0], observationToObject[:, 1], observationToObject[:, 2]
        cosLongitude, sinLongitude = np.cos(obsLongitude), np.sin(obsLongitude)
        cosLatitude, sinLatitude = np.cos(obsLatitude), np.sin(obsLatitude)
        if np.isscalar(sinLongitude):
            cosLongitude, sinLongitude = np.full_like(x, cosLongitude), np.full_like(x, sinLongitude)
            cosLatitude, sinLatitude = np.full_like(x, cosLatitude), np.full_like(x, sinLatitude)
        E = -sinLongitude * x + cosLongitude * y
        N = -sinLatitude * cosLongitude * x - sinLatitude * sinLongitude * y + cosLatitude * z
        U = cosLatitude * cosLongitude * x + cosLatitude * sinLongitude * y + sinLatitude * z
        enu = np.stack([E, N, U], axis=1)
        return self._maybeScalar(enu, scalar)

    def observerPositionEci(self, obsLongitude, obsLatitude, obsAltitude, fullJulianDates, radians=True):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        if not radians:
            obsLongitude, obsLatitude = np.deg2rad(obsLongitude), np.deg2rad(obsLatitude)
        obsEcef = np.asarray(self.longitudeLatitudeToEcef(obsLongitude, obsLatitude, obsAltitude, radians=True))
        if obsEcef.ndim == 1:
            obsEcef = np.tile(obsEcef, (fullJulianDates.shape[0], 1))
        obsEci = self.ecefToEci(obsEcef, fullJulianDates)
        return self._maybeScalar(np.asarray(obsEci), scalar)

    def enuToAzimuthElevationRange(self, enu):
        enu = np.asarray(enu)
        scalar = (enu.ndim == 1)
        if scalar:
            enu = enu.reshape(1, 3)
        E, N, U = enu[:, 0], enu[:, 1], enu[:, 2]
        objectRange = np.sqrt(E ** 2 + N ** 2 + U ** 2)
        elevation = np.arcsin(U / objectRange)
        azimuth = np.mod(np.arctan2(E, N), 2 * np.pi)
        return self._maybeScalar(azimuth, scalar), self._maybeScalar(elevation, scalar), self._maybeScalar(objectRange, scalar)

    def satelliteState(self, sat: Satrec, fullJulianDates):
        positions, velocities = self.propagateSgp4(sat, fullJulianDates)
        rEcef = self.eciToEcef(positions, fullJulianDates)
        longitudes, latitudes, altitudes = self.ecefToLongitudeLatitude(rEcef)
        return {"rECI": positions, "vECI": velocities, "rECEF": rEcef, "longitude": longitudes, "latitude": latitudes, "altitude": altitudes}

    def satellite2dVisibilityFootPrint(self, longitude, latitude, altitude, nbPoints=501):
        cosLatitude, sinLatitude = np.cos(latitude), np.sin(latitude)
        localRadius = np.sqrt((self.equatorialRadius ** 2 * cosLatitude ** 2 + self.polarRadius ** 2 * sinLatitude ** 2) / (cosLatitude ** 2 + sinLatitude ** 2))
        angleHorizon = np.arccos(localRadius / (localRadius + altitude))
        circlePoints = np.linspace(0, 2 * np.pi, nbPoints)
        cosHorizon, sinHorizon = np.cos(angleHorizon), np.sin(angleHorizon)
        circleLatitude = np.arcsin(sinLatitude * cosHorizon + cosLatitude * sinHorizon * np.cos(circlePoints))
        circleLongitude = longitude + np.arctan2(np.sin(circlePoints) * sinHorizon * cosLatitude, cosHorizon - sinLatitude * np.sin(circleLatitude))
        circleLongitude = (circleLongitude + np.pi) % (2 * np.pi) - np.pi
        return circleLongitude, circleLatitude

    def satellite3dVisibilityFootPrint(self, longitude, latitude, altitude, fullJulianDate, nbPoints=501):
        circleLongitude, circleLatitude = self.satellite2dVisibilityFootPrint(longitude, latitude, altitude, nbPoints)
        altitudes = np.zeros_like(circleLongitude)
        positionsEcef = self.longitudeLatitudeToEcef(circleLongitude, circleLatitude, altitudes)
        positionsEci = self.ecefToEci(positionsEcef, fullJulianDate)
        return positionsEci

    def satellite2dGroundTrack(self, positions, fullJulianDates):
        positionsEcef = self.eciToEcef(positions, fullJulianDates)
        longitudes, latitudes, altitudes = self.ecefToLongitudeLatitude(positionsEcef)
        longitudes = (longitudes + np.pi) % (2 * np.pi) - np.pi
        return longitudes, latitudes, altitudes

    def satellite3dGroundTrack(self, positions, fullJulianDates):
        positionsEcef = self.eciToEcef(positions, fullJulianDates)
        longitudes, latitudes, altitudes = self.ecefToLongitudeLatitude(positionsEcef)
        longitudes = (longitudes + np.pi) % (2 * np.pi) - np.pi
        altitudes = np.zeros_like(altitudes)
        positionsEcef = self.longitudeLatitudeToEcef(longitudes, latitudes, altitudes)
        positionsEci = self.ecefToEci(positionsEcef, fullJulianDates)
        return positionsEci

    @staticmethod
    def orbitalPeriod(sat: Satrec):
        return 2 * np.pi / (sat.no / 60)

    def flightPathAngle(self, positions, velocities):
        positions, velocities = np.asarray(positions), np.asarray(velocities)
        scalar = (positions.ndim == 1)
        if scalar:
            positions, velocities = positions.reshape(1, 3), velocities.reshape(1, 3)
        normPositions, normVelocities = np.linalg.norm(positions, axis=1), np.linalg.norm(velocities, axis=1)
        dotProduct = np.sum(positions * velocities, axis=1)
        gamma = np.arcsin(np.divide(dotProduct, normPositions * normVelocities, out=np.zeros_like(dotProduct), where=(normPositions * normVelocities) != 0))
        return self._maybeScalar(gamma, scalar)

    def radialTangentialVelocity(self, positions, velocities):
        positions, velocities = np.asarray(positions), np.asarray(velocities)
        scalar = (positions.ndim == 1)
        if scalar:
            positions, velocities = positions.reshape(1, 3), velocities.reshape(1, 3)
        normPositions = np.linalg.norm(positions, axis=1)
        radial = np.sum(positions * velocities, axis=1) / normPositions
        speed = np.linalg.norm(velocities, axis=1)
        tangential = np.sqrt(np.maximum(0, speed ** 2 - radial ** 2))
        return self._maybeScalar(radial, scalar), self._maybeScalar(tangential, scalar)

    def subSolarPoint(self, fullJulianDate, radians=True):
        sunEciPosition = self.solarDirectionEci(fullJulianDate)
        sunDeclination, sunRightAscension = np.arcsin(sunEciPosition[2]), np.arctan2(sunEciPosition[1], sunEciPosition[0])
        gmstAngle = self.greenwichMeridianSiderealTime(fullJulianDate)
        subSolarLongitude = sunRightAscension - gmstAngle
        subSolarLongitude = (subSolarLongitude + np.pi) % (2 * np.pi) - np.pi
        if not radians:
            return np.rad2deg(subSolarLongitude), np.rad2deg(sunDeclination), 1
        return subSolarLongitude, sunDeclination, 1

    def solarDirectionEci(self, fullJulianDates, normed=True):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        T = self.julianDateToJulianCenturies(fullJulianDates)
        meanLongitude = 280.46646 + T * (36000.76983 + T * 0.0003032)
        meanAnomaly = np.deg2rad(357.52911 + T * (35999.05029 - T * 0.0001537))
        earthOrbitEccentricity = 0.016708634 - T * (0.000042037 + T * 0.0000001267)
        centerEquation = np.deg2rad((1.914602 - T * (0.004817 + T * 0.000014)) * np.sin(meanAnomaly) + (0.019993 - T * 0.000101) * np.sin(2 * meanAnomaly) + 0.000289 * np.sin(3 * meanAnomaly))
        trueLongitude = meanLongitude + np.rad2deg(centerEquation)
        trueAnomaly = meanAnomaly + centerEquation
        sunDistance = 1.000001018 * (1 - earthOrbitEccentricity ** 2) / (1 + earthOrbitEccentricity * np.cos(trueAnomaly))
        omega = np.deg2rad(125.04452 - 1934.136261 * T + 0.0020708 * T ** 2 + T ** 3 / 450000.0)
        eclipticLongitude = np.deg2rad(trueLongitude - 0.00569 - 0.00478 * np.sin(omega))
        eclipticObliquity = np.deg2rad(23 + (26 + (21.448 - T * (46.8150 + T * (0.00059 - T * 0.001813))) / 60) / 60 + 0.00256 * np.cos(omega))
        # ECI POSITION VECTOR
        x = sunDistance * np.cos(eclipticLongitude)
        y = sunDistance * np.sin(eclipticLongitude) * np.cos(eclipticObliquity)
        z = sunDistance * np.sin(eclipticLongitude) * np.sin(eclipticObliquity)
        sunDirection = np.stack([x, y, z], axis=1)
        norm = np.linalg.norm(sunDirection, axis=1)
        return self._maybeScalar(sunDirection if not normed else sunDirection / norm[:, None], scalar)

    def lunarDirectionEci(self, fullJulianDates, normed=True):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        T = self.julianDateToJulianCenturies(fullJulianDates)
        L_prime = 218.3164591 + 481267.88134236 * T - 0.0013268 * T ** 2 + T ** 3 / 538841.0 - T ** 4 / 65194000.0
        D = 297.8502042 + 445267.1115168 * T - 0.0016300 * T ** 2 + T ** 3 / 545868.0 - T ** 4 / 113065000.0
        M_prime = 134.9634114 + 477198.8676313 * T + 0.0089970 * T ** 2 + T ** 3 / 69699.0 - T ** 4 / 14712000.0
        M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T ** 2 + T ** 3 / 24490000.0
        F = 93.2720993 + 483202.0175273 * T - 0.0034029 * T ** 2 - T ** 3 / 3526000.0 + T ** 4 / 863310000.0
        d, mp, m, f = np.radians(D), np.radians(M_prime), np.radians(M), np.radians(F)
        longitude = (L_prime + 6.28875 *  np.sin(mp) + 1.27402 *  np.sin(2 * d - mp) + 0.65831 *  np.sin(2 * d) + 0.21362 *  np.sin(2 * mp)
                     - 0.18560 *  np.sin(m) - 0.11434 *  np.sin(2 * f) + 0.05879 *  np.sin(2 * d - 2 * mp) + 0.05721 *  np.sin(2 * d - mp - m)
                     + 0.05332 *  np.sin(2 * d + mp) - 0.04587 *  np.sin(mp + m) - 0.04102 *  np.sin(mp - m) - 0.03472 *  np.sin(2 * d - 2 * f)
                     - 0.03038 *  np.sin(2 * d + mp - m) + 0.01533 *  np.sin(2 * d - mp + m))
        latitude = (5.12819 *  np.sin(f) + 0.28061 *  np.sin(mp + f) + 0.27769 *  np.sin(mp - f) + 0.17324 *  np.sin(2 * d - f) + 0.05541 *  np.sin(2 * d + f - mp)
                    + 0.04627 *  np.sin(2 * d - f - mp) + 0.03235 *  np.sin(2 * d + f) + 0.01798 *  np.sin(2 * mp + f) - 0.01667 *  np.sin(mp - m - f))
        parallax = 0.95072 + 0.05182 * np.cos(mp) + 0.00953 * np.cos(2 * d - mp) + 0.00727 * np.cos(2 * d) + 0.00286 * np.cos(2 * mp)
        omega = np.deg2rad(125.04452 - 1934.136261 * T + 0.0020708 * T ** 2 + T ** 3 / 450000.0)
        eclipticObliquity = np.deg2rad(23 + (26 + (21.448 - T * (46.8150 + T * (0.00059 - T * 0.001813))) / 60) / 60 + 0.00256 * np.cos(omega))
        moonDistance = 6378.14 / np.sin(np.deg2rad(parallax))
        longitudeRadians, latitudeRadians, obliquityRadians = np.deg2rad(longitude), np.deg2rad(latitude), np.deg2rad(eclipticObliquity)
        xEcliptic = moonDistance * np.cos(latitudeRadians) * np.cos(longitudeRadians)
        yEcliptic = moonDistance * np.cos(latitudeRadians) * np.sin(longitudeRadians)
        zEcliptic = moonDistance * np.sin(latitudeRadians)
        x = xEcliptic
        y = yEcliptic * np.cos(obliquityRadians) - zEcliptic * np.sin(obliquityRadians)
        z = yEcliptic * np.sin(obliquityRadians) + zEcliptic * np.cos(obliquityRadians)
        moonDirectionEci = np.stack([x, y, z], axis=1)
        norm = np.linalg.norm(moonDirectionEci, axis=1)
        return self._maybeScalar(moonDirectionEci if not normed else moonDirectionEci / norm[:, None], scalar)

    def moonRotationAngle(self, fullJulianDates, radians=True):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        D = fullJulianDates - 2451545.0
        meanRotationAngle = 38.3213 + 13.17635815 * D
        E1, E2 = np.deg2rad(125.045 - 0.0529921 * D), np.deg2rad(250.089 - 0.1059842 * D),
        E3, E4 = np.deg2rad(260.008 + 13.0120009 * D), np.deg2rad(176.625 + 13.3407154 * D)
        E5, E6 = np.deg2rad(357.529 + 0.9856003 * D), np.deg2rad(311.589 + 26.4057084 * D)
        E7, E8 = np.deg2rad(134.963 + 13.0649930 * D), np.deg2rad(276.617 + 0.3287146 * D)
        libration = 3.5610 * np.sin(E1) + 0.1208 * np.sin(E2) - 0.0642 * np.sin(E3) + 0.0158 * np.sin(E4) + 0.0252 * np.sin(E5) - 0.0066 * np.sin(E6) - 0.0047 * np.sin(E7) - 0.0046 * np.sin(E8)
        rotationAngle = (meanRotationAngle + libration) % 360.0
        if radians:
            return self._maybeScalar(np.deg2rad(rotationAngle), scalar)
        else:
            return self._maybeScalar(rotationAngle, scalar)

    def terminatorCurve(self, fullJulianDate, nbPoints=361, radians=True):
        sunLongitude, sunLatitude, _ = self.subSolarPoint(fullJulianDate, radians=True)
        longitudes = np.linspace(-np.pi, np.pi, nbPoints)
        latitudes = np.arctan(-np.cos(longitudes - sunLongitude) / np.tan(sunLatitude))
        order = np.argsort(longitudes)
        longitudes, latitudes = longitudes[order], latitudes[order]
        if not radians:
            return np.rad2deg(longitudes), np.rad2deg(latitudes)
        return longitudes, latitudes

    def solarExposure(self, fullJulianDates, positions):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        positions, _ = self._ensureArray(positions, vector=True)
        sunDir = self.solarDirectionEci(fullJulianDates)
        if sunDir.ndim == 1:
            sunDir = sunDir.reshape(1, 3)
        if sunDir.shape[0] == 1 and positions.shape[0] > 1:
            sunDir = np.repeat(sunDir, positions.shape[0], axis=0)
        dotProduct = np.sum(positions * sunDir, axis=1)
        isBehind = dotProduct < 0
        crossProduct = np.cross(positions, sunDir)
        distance = np.linalg.norm(crossProduct, axis=1)
        isInsideShadow = distance < self.equatorialRadius
        inShadow = isBehind & isInsideShadow
        exposure = (~inShadow).astype(int)
        return self._maybeScalar(exposure, scalar)

    def getVernalSubPoint(self, fullJulianDate, radians=True):
        vernalUnitVectorEci = np.array([1, 0, 0])
        vernalLongitude = (np.arctan2(vernalUnitVectorEci[1], vernalUnitVectorEci[0]) - self.greenwichMeridianSiderealTime(fullJulianDate)) % (2 * np.pi)
        if vernalLongitude > np.pi:
            vernalLongitude -= 2 * np.pi
        if not radians:
            return np.rad2deg(vernalLongitude), np.rad2deg(0)
        return vernalLongitude, 0

    def trueAnomaly(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        radius, velocity = np.linalg.norm(positions, axis=1), np.linalg.norm(velocities, axis=1)
        angularMomentumVector = np.cross(positions, velocities)
        eccentricityVector = np.cross(velocities, angularMomentumVector) / self.earthGravParameter - (positions / radius[:, None])
        eccentricity = np.linalg.norm(eccentricityVector, axis=1)
        valid = eccentricity > 1e-8
        cosTrueAnomaly = np.zeros_like(radius)
        cosTrueAnomaly[valid] = np.sum(eccentricityVector[valid] * positions[valid], axis=1) / (eccentricity[valid] * radius[valid])
        cosTrueAnomaly = np.clip(cosTrueAnomaly, -1, 1)
        trueAnomaly = np.zeros_like(eccentricity)
        trueAnomaly[valid] = np.arccos(cosTrueAnomaly[valid])
        dotRV = np.sum(positions * velocities, axis=1)
        mask = valid & (dotRV < 0)
        trueAnomaly[mask] = 2 * np.pi - trueAnomaly[mask]
        trueAnomaly[~valid] = 0
        return self._maybeScalar(trueAnomaly, scalar)

    def inclination(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        angularMomentumVector = np.cross(positions, velocities)
        angularMomentum = np.linalg.norm(angularMomentumVector, axis=1)
        cosInclination = angularMomentumVector[:, 2] / angularMomentum
        cosInclination = np.clip(cosInclination, -1.0, 1.0)
        inclination = np.arccos(cosInclination)
        return self._maybeScalar(inclination, scalar)

    def raan(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        angularMomentumVector = np.cross(positions, velocities)
        ascendingNodeVector = np.cross(np.tile(np.array([0, 0, 1]), (angularMomentumVector.shape[0], 1)), angularMomentumVector)
        ascendingNodeNorm = np.linalg.norm(ascendingNodeVector, axis=1)
        cosRAAN = np.divide(ascendingNodeVector[:, 0], ascendingNodeNorm, out=np.zeros_like(ascendingNodeNorm), where=ascendingNodeNorm != 0)
        cosRAAN = np.clip(cosRAAN, -1.0, 1.0)
        raan = np.arccos(cosRAAN)
        mask = ascendingNodeVector[:, 1] < 0
        raan[mask] = 2 * np.pi - raan[mask]
        return self._maybeScalar(raan, scalar)

    def argumentOfPerigee(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        radius = np.linalg.norm(positions, axis=1)
        angularMomentumVector = np.cross(positions, velocities)
        ascendingNodeVector = np.cross(np.tile(np.array([0, 0, 1]), (angularMomentumVector.shape[0], 1)), angularMomentumVector)
        eccentricityVector = np.cross(velocities, angularMomentumVector) / self.earthGravParameter - positions / radius[:, None]
        ascendingNodeNorm = np.linalg.norm(ascendingNodeVector, axis=1)
        eccentricity = np.linalg.norm(eccentricityVector, axis=1)
        cosArgumentPerigee = np.sum(ascendingNodeVector * eccentricityVector, axis=1) / (ascendingNodeNorm * eccentricity)
        cosArgumentPerigee = np.clip(cosArgumentPerigee, -1.0, 1.0)
        argumentPerigee = np.arccos(cosArgumentPerigee)
        mask = eccentricityVector[:, 2] < 0
        argumentPerigee[mask] = 2 * np.pi - argumentPerigee[mask]
        return self._maybeScalar(argumentPerigee, scalar)

    def specificEnergy(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        radius = np.linalg.norm(positions, axis=1)
        speed = np.linalg.norm(velocities, axis=1)
        energy = 0.5 * speed ** 2 - self.earthGravParameter / radius
        return self._maybeScalar(energy, scalar)

    def semiMajorAxis(self, positions, velocities):
        energy = self.specificEnergy(positions, velocities)
        energy, scalar = self._ensureArray(energy)
        semiMajorAxis = -self.earthGravParameter / (2 * energy)
        return self._maybeScalar(semiMajorAxis, scalar)

    def orbitalPeriodFromState(self, positions, velocities):
        semiMajorAxis = self.semiMajorAxis(positions, velocities)
        semiMajorAxis, scalar = self._ensureArray(semiMajorAxis)
        orbitalPeriod = 2 * np.pi * np.sqrt(semiMajorAxis ** 3 / self.earthGravParameter)
        return self._maybeScalar(orbitalPeriod, scalar)

    def eccentricity(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        radius = np.linalg.norm(positions, axis=1)
        angularMomentumVector = np.cross(positions, velocities)
        eccentricityVector = np.cross(velocities, angularMomentumVector) / self.earthGravParameter - positions / radius[:, None]
        eccentricity = np.linalg.norm(eccentricityVector, axis=1)
        return self._maybeScalar(eccentricity, scalar)

    def meanMotion(self, positions, velocities):
        semiMajorAxis = self.semiMajorAxis(positions, velocities)
        semiMajorAxis, scalar = self._ensureArray(semiMajorAxis)
        n = np.sqrt(self.earthGravParameter / semiMajorAxis ** 3)
        return self._maybeScalar(n, scalar)

    def meanAnomaly(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        trueAnomaly = self.trueAnomaly(positions, velocities)
        eccentricity = self.eccentricity(positions, velocities)
        E = 2 * np.arctan2(np.tan(trueAnomaly / 2), np.sqrt((1 + eccentricity) / (1 - eccentricity)))
        M = E - eccentricity * np.sin(E)
        M = np.mod(M, 2 * np.pi)
        return self._maybeScalar(M, scalar)

    def perigeeApogee(self, positions, velocities):
        positions, scalar = self._ensureArray(positions, vector=True)
        velocities, _ = self._ensureArray(velocities, vector=True)
        a = self.semiMajorAxis(positions, velocities)
        e = self.eccentricity(positions, velocities)
        perigeeRadius, apogeeRadius = a * (1 - e), a * (1 + e)
        perigeeAltitude, apogeeAltitude = perigeeRadius - self.equatorialRadius, apogeeRadius - self.equatorialRadius
        return self._maybeScalar(perigeeAltitude, scalar), self._maybeScalar(apogeeAltitude, scalar)

    def groundSpeed(self, velocities, fullJulianDates):
        vEcef = self.eciToEcef(velocities, fullJulianDates)
        horizontalSpeed = np.linalg.norm(vEcef[:, :2], axis=1)
        return horizontalSpeed

    def j2Acceleration(self, positions):
        positions, scalar = self._ensureArray(positions, vector=True)
        J2 = 1.08262668e-3
        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
        radius = np.linalg.norm(positions, axis=1)
        factor = (3 / 2) * J2 * self.earthGravParameter * self.equatorialRadius ** 2 / radius ** 5
        xAcceleration = factor * x * (5 * (z ** 2) / (radius ** 2) - 1)
        yAcceleration = factor * y * (5 * (z ** 2) / (radius ** 2) - 1)
        zAcceleration = factor * z * (5 * (z ** 2) / (radius ** 2) - 3)
        acceleration = np.stack([xAcceleration, yAcceleration, zAcceleration], axis=1)
        return self._maybeScalar(acceleration, scalar)

    def newtonianAcceleration(self, positions):
        positions, scalar = self._ensureArray(positions, vector=True)
        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
        radius = np.linalg.norm(positions, axis=1)
        factor = -self.earthGravParameter / radius ** 3
        ax, ay, az = factor * x, factor * y, factor * z
        acceleration = np.stack([ax, ay, az], axis=1)
        return self._maybeScalar(acceleration, scalar)

    def apparentMagnitude(self, fullJulianDates, positions, obsLongitude, obsLatitude, obsAltitude, standardMagnitude, radians=True):
        fullJulianDates, scalar = self._ensureArray(fullJulianDates)
        positions, _ = self._ensureArray(positions, vector=True)
        obsEci = np.asarray(self.observerPositionEci(obsLongitude, obsLatitude, obsAltitude, fullJulianDates, radians=radians))
        if obsEci.ndim == 1:
            obsEci = obsEci.reshape(1, 3)
        sunDir = np.asarray(self.solarDirectionEci(fullJulianDates))
        if sunDir.ndim == 1:
            sunDir = sunDir.reshape(1, 3)
        obsObjectVector = positions - obsEci
        obsObjectDistance = np.linalg.norm(obsObjectVector, axis=1)
        cosPhaseAngle = np.clip(np.sum(-sunDir * (obsObjectVector / obsObjectDistance[:, None]), axis=1), -1.0, 1.0)
        phaseAngle = np.arccos(cosPhaseAngle)
        sinPhaseAngle = np.clip(np.sum(np.sin(phaseAngle)), -1.0, 1.0)
        functionPhase = np.clip((sinPhaseAngle + (np.pi - phaseAngle) * np.cos(phaseAngle)) / np.pi, 1e-10, None)
        phaseMagnitude = -2.5 * np.log10(functionPhase)
        exposure = self.solarExposure(fullJulianDates, positions)
        magnitude = np.where(exposure == 1, standardMagnitude + 5.0 * np.log10(obsObjectDistance / 1000.0) + phaseMagnitude, np.nan)
        return self._maybeScalar(magnitude, scalar)

    @staticmethod
    def getAvailableVariables():
        return ["ALTITUDE", "LATITUDE", "LONGITUDE", "R_ECI_X", "R_ECI_Y", "R_ECI_Z", "V_ECI_X", "V_ECI_Y", "V_ECI_Z",
                "SOLAR_EXPOSURE", "FLIGHT_PATH_ANGLE", "RADIAL_VELOCITY", "TANGENTIAL_VELOCITY",
                "TRUE_ANOMALY", "INCLINATION", "RAAN", "ARGUMENT_OF_PERIGEE", "ECCENTRICITY", "MEAN_MOTION", "MEAN_ANOMALY",
                "GROUND_SPEED", "SPECIFIC_ENERGY", "SEMI_MAJOR_AXIS", "ORBITAL_PERIOD"]
