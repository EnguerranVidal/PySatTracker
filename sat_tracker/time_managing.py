import time
import datetime
import calendar

import numpy as np


def julian_date(epoch):
    return (epoch / 86400.0) + 2440587.5


def julian_date_J2000(epoch):
    JD = (epoch / 86400.0) + 2440587.5
    return JD - 2451545


def day_fraction(unix):
    julian = julian_date(unix)
    fraction = julian - np.fix(julian - 0.5) - 0.5
    return fraction


def unix_str(unix):
    struct = time.gmtime(unix)
    string = time.asctime(struct)
    return string


def str_unix(string, str_format):
    struct = time.strptime(string, str_format)
    return calendar.timegm(struct)  # From struct in UTC to secs since epoch


def day_of_year(unix):
    struct = time.gmtime(unix)
    n_days = struct.tm_yday
    return n_days


def time_range_unix(str1, str2, N, str_format):
    time1 = str_unix(str1, str_format)
    time2 = str_unix(str2, str_format)
    T = np.linspace(time1, time2, num=N)
    return T


def time_range_julian(str1, str2, N, str_format):
    T = time_range_unix(str1, str2, N, str_format)
    return julian_fractions(T)


def julian_fractions(unix):
    julian = np.fix(julian_date(unix) - 0.5) + 0.5
    fraction = day_fraction(unix)
    return julian, fraction


def rotation_matrix(ang):
    return np.array([[np.cos(ang), np.sin(ang), 0], [-np.sin(ang), np.cos(ang), 0], [0, 0, 1]])

