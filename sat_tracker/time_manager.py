import time
import numpy as np
import datetime
import calendar


def seconds_unix_str(epoch):
    struct = time.gmtime(epoch)
    string = time.asctime(struct)
    return string


def julian_date(epoch):
    return (epoch / 86400.0) + 2440587.5


class Time_Manager:
    """ This class takes care of time managing tasks and conversions"""

    def __init__(self):
        self.julian_leap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.julian_common = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        self.months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def date_julian(self, year, dayfraction):
        YEAR = datetime.datetime(year, 1, 1, 0)
        year = YEAR.replace(tzinfo=datetime.timezone.utc).timestamp()
        epoch = year + (dayfraction - 1) * 86400
        return epoch

    def str_seconds_unix(self, string):
        structime = time.strptime(string, self.format)
        return calendar.timegm(structime)  # From struct in UTC to secs since epoch

    def day_of_year(self, epoch):
        struct = time.gmtime(epoch)
        n_days = struct.tm_yday
        return n_days

    def time_range(self, str1, str2, N):
        """ Returns a time row matrix between str1 and str2 containing N time"""
        time1 = self.str_seconds_unix(str1)
        time2 = self.str_seconds_unix(str2)
        T = np.linspace(time1, time2, num=N)
        return T

    def day_fraction(self, epoch):
        struct = time.localtime(epoch)
        years = struct.tm_year
        months = struct.tm_mon
        days = struct.tm_mday
        DATE = datetime.datetime(years, months, days, 0)
        date = DATE.replace(tzinfo=datetime.timezone.utc).timestamp()
        fraction = (epoch - date) / 86400
        return fraction

