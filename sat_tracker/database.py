import requests
import os
import sys
import numpy as np


class TLE_Database:
    def __init__(self, path, load_online=True):
        """
        :type load_online: bool
        :type path: str
        """
        self.source_url = "https://www.amsat.org/tle/current/nasabare.txt"
        self.default_url = "https://www.amsat.org/tle/current/nasabare.txt"
        self.data_path = path
        if load_online:
            self.import_data()
        self.data = None
        self.deconstructed_data = None
        self.n_satellites = 0
        self.labels = ['name', 'number', 'epoch_year', 'epoch', 'i', 'Omega', 'e', 'w', 'M', 'n']
        self.load_data()

    def load_data(self):
        self.data = []
        self.deconstructed_data = []
        ''' Formats the data from "filename" ( .txt file ) and returns the
                    desired outputs ( moslty Keplerian Parameters)'''
        with open(self.data_path, "r") as file:
            lines = file.readlines()
            file.close()
        n = len(lines)
        satellite_names = []
        satellite_numbers = []
        epoch_years = []
        epoch_days = []
        inclinations = []
        ascensions = []
        eccentricities = []
        arguments = []
        mean_anomalies = []
        mean_motions = []
        self.n_satellites = int(n / 3)
        for i in range(int(n / 3)):
            line1 = lines[i * 3]
            line2 = lines[i * 3 + 1]
            line3 = lines[i * 3 + 2]
            self.data.append([line1, line2, line3])
            satellite_names.append(line1)
            # print(line2[18:20])
            satellite_numbers.append(int(line2[2:7]))
            if int(line2[18:20]) >= 57:
                epoch_years.append(int("19" + line2[18:20]))
            else:
                epoch_years.append(int("20" + line2[18:20]))
            epoch_days.append(float(line2[20:32]))
            inclinations.append(np.radians(float(line3[8:16])))
            ascensions.append(np.radians(float(line3[17:25])))
            eccentricities.append(float("0." + line3[26:33]))
            arguments.append(np.radians(float(line3[34:42])))
            mean_anomalies.append(np.radians(float(line3[34:42])))
            mean_motions.append(float(line3[52:63]) * 7.272205216643 * 10 ** (-5))
        self.deconstructed_data.append(satellite_names)
        self.deconstructed_data.append(satellite_numbers)
        self.deconstructed_data.append(epoch_years)
        self.deconstructed_data.append(epoch_days)
        self.deconstructed_data.append(inclinations)
        self.deconstructed_data.append(ascensions)
        self.deconstructed_data.append(eccentricities)
        self.deconstructed_data.append(arguments)
        self.deconstructed_data.append(mean_anomalies)
        self.deconstructed_data.append(mean_motions)

    def import_data(self, website=None):
        if website is not None:
            self.source_url = website
        r = requests.get(self.source_url, allow_redirects=True)
        with open(self.data_path, 'wb')as file:
            file.write(r.content)
        print("NORAD data imported from Amsat website.")

    def default_source(self):
        self.source_url = self.default_url

    def search_index(self, name):
        """ Returns the index of an object in the NORAD database created by the class.
            Parameters :
            :type name: str"""
        name = name.lower()
        for i in range(self.n_satellites):
            index_name = self.deconstructed_data[0][i].lower()
            index_name = index_name[:-1]
            if name == index_name:
                return i
        return False


class Satellite_Database:
    def __init__(self, path, load_online=True):
        pass

