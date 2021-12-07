import numpy as np
from sat_tracker.time_managing import *


class Earth:
    def __init__(self):
        self.object_name = 'Earth'
        self.mass = 5.9722 * 10 ** 24  # kg
        self.equatorial_radius = 6378000  # m
        self.polar_radius = 6356000  # m
        self.rotation_rate0 = 7.2921155 * 10 ** (-5)  # rad/sec
        self.rotation_rate1 = 1.00273790934  # turn/day
        self.J = [1, 0, 1082.62622070 * 10 ** (-6),
                  -2.53615069 * 10 ** (-6), -1.61936355 * 10 ** (-6),
                  -0.22310138 * 10 ** (-6), 0.54028952 * 10 ** (-6),
                  -0.36026016 * 10 ** (-6), -0.20776704 * 10 ** (-6),
                  -0.14456739 * 10 ** (-6), -0.23380081 * 10 ** (-6)]
        self.geodesic_eccentricity = np.sqrt(1 - (self.polar_radius / self.equatorial_radius) ** 2)
        # OBSERVER
        self.observer_longitude = None
        self.observer_latitude = None
        self.observer_elevation = None
        self.observer_position = None  # np.array([X, Y, Z])

    def define_observer(self, lon, lat, elev):
        self.observer_longitude = lon
        self.observer_latitude = lat
        self.observer_elevation = elev
        self.observer_position = self.geodetic_ECEF(lat, lon, elev)

    @staticmethod
    def sidereal_rotation(unix):
        DJ = day_fraction(unix)
        du = julian_date(unix) - 2451545.0 - DJ
        Tu = du / 36525
        return 7.2921158553 * 10 ** (-5) + 4.3 * 10 ** (-15) * Tu

    def define_ENU_ref(self, longitude, latitude, height):
        self.observer_longitude = longitude
        self.observer_latitude = latitude
        self.observer_elevation = height
        X, Y, Z = self.geodetic_ECEF(latitude, longitude, height)
        self.observer_position = np.array(X, Y, Z)

    def GMST(self, unix):
        """ Returns the Greenwich Mean Sidereal Time in radians at the given UNIX time"""
        DJ = day_fraction(unix)
        du = julian_date(unix) - 2451545.0 - DJ
        Tu = du / 36525
        qG00 = (24110.54841 + 8640184.812866 * Tu + 0.093104 * Tu ** 2 - 6.2 * 10 ** (-6) * Tu ** 3) % 86400
        qGt = (qG00 + 86400 * self.rotation_rate1 * DJ) % 86400
        OmegaGt = np.radians(qGt / 240)
        return OmegaGt

    def geodetic_ECEF(self, latitude, longitude, height):
        N = self.equatorial_radius / np.sqrt(1 - self.geodesic_eccentricity ** 2 * np.sin(latitude) ** 2)
        X = (N + height) * np.cos(latitude) * np.cos(longitude)
        Y = (N + height) * np.cos(latitude) * np.sin(longitude)
        Z = ((self.polar_radius ** 2) / (self.equatorial_radius ** 2) * N + height) * np.sin(latitude)
        return X, Y, Z

    def ECEF_ENU(self, X, Y, Z, long0, lat0, h0):
        x0, y0, z0 = self.geodetic_ECEF(lat0, long0, h0)
        return self.UVW_ENU(X - x0, Y - y0, Z - z0)

    @staticmethod
    def UVW_ENU(U, V, W, long0, lat0):
        t = np.cos(long0) * U + np.sin(long0) * V
        east = -np.sin(long0) * U + np.cos(long0) * V
        up = np.cos(lat0) * t + np.sin(lat0) * W
        north = -np.sin(lat0) * t + np.cos(lat0) * W
        return east, north, up

    @staticmethod
    def ENU_UVW(East, North, Up, long0, lat0):
        t = np.cos(lat0) * Up - np.sin(lat0) * North
        w = np.sin(lat0) * Up + np.cos(lat0) * North
        u = np.cos(long0) * t - np.sin(long0) * East
        v = np.sin(long0) * t + np.cos(long0) * East
        return u, v, w

    def ECI_ECEF(self, X, Y, Z, unix):
        GMST = self.GMST(unix)
        n = X.size
        ECI = np.column_stack((X.ravel(), Y.ravel(), Z.ravel()))
        ECEF = np.zeros(shape=(n, 3))
        for i in range(n):
            ECEF[i, :] = rotation_matrix(GMST[i]) @ ECI[i, :]
        x = ECEF[:, 0].reshape(X.shape)
        y = ECEF[:, 1].reshape(X.shape)
        z = ECEF[:, 2].reshape(X.shape)
        return x, y, z

    def ECEF_ECI(self, X, Y, Z, unix):
        GMST = self.GMST(unix)
        n = X.size
        ECEF = np.column_stack((X.ravel(), Y.ravel(), Z.ravel()))
        ECI = np.zeros(shape=(n, 3))
        for i in range(n):
            ECI[i, :] = rotation_matrix(GMST[i]).T @ ECEF[i, :]
        x = ECI[:, 0].reshape(X.shape)
        y = ECI[:, 1].reshape(X.shape)
        z = ECI[:, 2].reshape(X.shape)
        return x, y, z

    def ECEF_geodetic(self, X, Y, Z):
        """  algorithm : https://hal.archives-ouvertes.fr/hal-01704943v2/document """
        longitude = np.arctan2(Y, X)
        # Shortening notation
        a = self.equatorial_radius
        e = self.geodesic_eccentricity
        # Calculating k for latitude and height (Zhu enhanced algorithm)
        w2 = X ** 2 + Y ** 2
        _l = e ** 2 / 2
        m = w2 / (a ** 2)
        n = Z ** 2 * (1 - e ** 2) / (a ** 2)
        p = (m + n - 4 * _l ** 2) / 6
        G = m * n * _l ** 2
        H = 2 * p ** 3 + G
        C = np.cbrt(H + G + 2 * np.sqrt(H * G)) / np.cbrt(2)
        i = - (2 * _l ** 2 + m + n) / 2
        P = p ** 2
        beta = i / 3 - C - P / C
        k = _l ** 2 * (_l ** 2 - m - n)
        t = np.sqrt(np.sqrt(beta ** 2 - k) - (beta + i) / 2) - np.sign(m - n) * np.sqrt(np.abs((beta - i) / 2))
        F = t ** 4 + 2 * i * t ** 2 + 2 * _l * (m - n) * t + k
        dF = 4 * t ** 3 + 4 * i * t + 2 * _l * (m - n)
        dt = - F / dF
        u = t + dt + _l
        v = t + dt - _l
        w = np.sqrt(w2)
        latitude = np.arctan2(Z * u, w * v)
        dw = w * (1 - 1 / u)
        dz = Z * (1 - (1 - e ** 2) / v)
        height = np.sign(u - 1) * np.sqrt(dw ** 2 + dz ** 2)
        return longitude, latitude, height

    def ECEF_spherical(self, X, Y, Z):
        longitude = np.arctan2(Y, X)
        R = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
        latitude = np.arcsin(Z / R)
        return longitude, latitude, R - self.equatorial_radius

    def ENU_ECEF(self, x, y, z):
        n = x.shape[0]
        long = self.observer_longitude
        lat = self.observer_latitude
        rotation = np.array([[-np.sin(long), -np.sin(lat) * np.cos(long), np.cos(lat) * np.cos(long)],
                             [np.cos(long), -np.sin(lat) * np.sin(long), np.cos(lat) * np.sin(long)],
                             [0, np.cos(lat), np.sin(lat)]])
        object_pos = np.zeros(shape=(3, n))
        object_pos[0, :], object_pos[1, :], object_pos[2, :] = x, y, z
        result = np.matmul(rotation, self.observer_position + object_pos)
        X, Y, Z = result[0, :], result[1, :], result[2, :]
        return X, Y, Z

    @staticmethod
    def ENU_AER(E, N, U):
        r = np.sqrt(E ** 2 + N ** 2)
        slant_range = np.qrt(U ** 2 + r ** 2)
        elev = np.atan2(U, r)
        az = np.atan2(E, N)
        return az, elev, slant_range



