from sgp4.api import Satrec
from sgp4.api import SatrecArray
import os

import numpy as np
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
from cartopy.feature.nightshade import Nightshade

from sat_tracker.database import *
from sat_tracker.time_managing import *
from sat_tracker.earth import *


class Tracker:
    def __init__(self, path, load=True):
        self.estimator = None
        self.data_path = path
        self.database = TLE_Database(path, load_online=load)
        self.tracked_objects = []
        self.tracked_indexes = []
        self.n_tracked_objects = 0
        # Earth object for earth coordinates transformations
        self.earth = Earth()

    def add_object(self, name):
        index = self.database.search_index(name)
        if index:
            self.tracked_objects.append(self.database.data[index][0])
            self.tracked_indexes.append(index)
            self.load_estimator()
            self.n_tracked_objects += 1
        else:
            print("WARNING : Could not find ", name, "in the source database.")

    def load_estimator(self):
        satellites = []
        for i in self.tracked_indexes:
            line1 = self.database.data[i][1]
            line2 = self.database.data[i][2]
            satellites.append(Satrec.twoline2rv(line1, line2))
        self.estimator = SatrecArray(satellites)

    def estimate(self, times):
        jd, fr = julian_fractions(times)
        e, r, v = self.estimator.sgp4(jd, fr)
        return r, v

    def sub_points(self, times):
        r, v = self.estimate(times)
        X, Y, Z = r[:, :, 0] * 1000, r[:, :, 1] * 1000, r[:, :, 2] * 1000
        longitudes = np.zeros_like(X)
        latitudes = np.zeros_like(X)
        heights = np.zeros_like(X)
        for i in range(self.n_tracked_objects):
            x, y, z = self.earth.ECI_ECEF(X[i, :], Y[i, :], Z[i, :], times)
            long, lat, h = self.earth.ECEF_geodetic(x, y, z)
            longitudes[i, :] = long
            latitudes[i, :] = lat
            heights[i, :] = h
        return longitudes, latitudes, heights

    def draw2D(self, T=3 * 3600):
        t0 = time.time()
        times = np.linspace(t0, t0 + T, 3000)
        Long, Lat, H = self.sub_points(times)
        Long = np.degrees(Long)
        Lat = np.degrees(Lat)
        ax = plt.axes(projection=ccrs.PlateCarree())
        for i in range(self.n_tracked_objects):
            ax.plot(Long[i, :], Lat[i, :], transform=ccrs.Geodetic())
        ax.set_extent([-180, 180, -90, 90])
        ax.stock_img()
        ax.coastlines()
        current_time = datetime.datetime.now()
        ax.add_feature(Nightshade(current_time, alpha=0.3))
        ax.gridlines(draw_labels=False, linewidth=1, color='blue', alpha=0.3, linestyle='--')
        plt.show()

    def draw3D(self, T=12 * 3600):
        fig = plt.figure()
        ax = fig.gca(projection='3d')
        ax.set_title(' '.join(self.tracked_objects))
        ax.set_xlim3d(-50000, 50000)
        ax.set_ylim3d(-50000, 50000)
        ax.set_zlim3d(-50000, 50000)
        ax.set_xlabel('\nX [ km ]', linespacing=3.2)
        ax.set_ylabel('\nY [ km ]', linespacing=3.1)
        ax.set_zlabel('\nZ [ km ]', linespacing=3.4)
        t0 = time.time()
        times = np.linspace(t0, t0 + T, 3000)
        R, V = self.estimate(times)
        X, Y, Z = R[:, :, 0], R[:, :, 1], R[:, :, 2]
        for i in range(self.n_tracked_objects):
            x, y, z = X[i, :], Y[i, :], Z[i, :]
            ax.plot(x, y, z, c='b')
            ax.plot(x[0], y[0], z[0], c="r")
        plt.show()














