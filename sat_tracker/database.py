import requests
import os
import sys
import numpy as np


class TLE_Database:
    def __init__(self, data_path, default_urls, default_toggles=None, supp_urls=None, supp_toggles=None, load_online=True):
        """
        :type load_online: bool
        :type default_urls: list
        :type supp_urls: list
        :type data_path: str
        """
        if supp_urls is None:
            supp_urls = []
        if default_toggles is None:
            default_toggles = [True] * len(default_urls)
        if supp_toggles is None:
            if len(supp_urls) != 0:
                supp_toggles = [True] * len(supp_urls)
            else:
                supp_toggles = []
        self.default_urls = default_urls
        self.default_toggles = default_toggles
        self.supp_urls = supp_urls
        self.supp_toggles = supp_toggles
        self.data_path = data_path
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
        lines = []
        for i in range(len(self.default_urls)):
            if self.default_toggles[i]:
                path = os.path.join(self.data_path, file_name_url(self.default_urls[i]))
                with open(path, "r") as file:
                    data = file.readlines()
                    lines += data
        for i in range(len(self.supp_urls)):
            if self.supp_toggles[i]:
                path = os.path.join(self.data_path, file_name_url(self.supp_urls[i]))
                with open(path, "r") as file:
                    data = file.readlines()
                    lines += data
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

    def import_data(self):
        timeout = 5
        try:
            for i in range(len(self.default_urls)):
                if self.default_toggles[i]:
                    file_name = file_name_url(self.default_urls[i])
                    path = os.path.join(self.data_path, file_name)
                    request = requests.get(self.default_urls[i], timeout=timeout, allow_redirects=True)
                    with open(path, 'wb') as file:
                        file.write(request.content)
            for i in range(len(self.supp_urls)):
                if self.supp_toggles[i]:
                    file_name = file_name_url(self.supp_urls[i])
                    path = os.path.join(self.data_path, file_name)
                    request = requests.get(self.supp_urls[i], timeout=timeout, allow_redirects=True)
                    with open(path, 'wb') as file:
                        file.write(request.content)
            print("NORAD data imported.")
        except (requests.ConnectionError, requests.Timeout) as exception:
            print("No internet connection.")

    def search_index(self, name):
        """ Returns the index of an object in the NORAD database created by the class.
            Parameters :
            :type name: str"""
        for i in range(self.n_satellites):
            index_name = self.deconstructed_data[0][i]
            index_number = self.deconstructed_data[1][i]
            if name == index_name or name == index_number:
                return i
        return False


def file_name_url(url):
    website_list = url.split("/")
    return website_list[-1]
