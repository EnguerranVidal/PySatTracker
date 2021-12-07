from sat_tracker.tracker import *
from Tkinter_GUI import *
import os


def ISS_tracking():
    # DON'T DELETE ############################
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    data_path = os.path.join(data_dir, "NORAD.txt")
    date1 = "28 Nov 2021 00:00:00"
    date2 = "28 Nov 2021 00:02:00"
    str_format = "%d %b %Y %H:%M:%S"
    sat_database = "https://www.ucsusa.org/media/11492"
    ###########################################

    tracker = Tracker(data_path, load=False)
    tracker.add_object("ISS")
    tracker.draw2D()


def test_overhead():
    # DON'T DELETE ############################
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    data_path = os.path.join(data_dir, "NORAD.txt")
    date1 = "28 Nov 2021 00:00:00"
    date2 = "28 Nov 2021 00:02:00"
    str_format = "%d %b %Y %H:%M:%S"
    sat_database = "https://www.ucsusa.org/media/11492"
    ###########################################

    t0 = time.time()
    T = 3
    times = np.linspace(t0, t0 + T * 3600, num=int(T * 60))

    station_toulouse = '''43°33'45"N   1°28'09"E   166m'''

    tracker = Tracker(data_path, load=False)
    tracker.add_object("ISS")
    tracker.ground_station(station_toulouse)
    tracker.draw2D(times)
    tracker.above_passing("ISS", times)


def test_tkinter():
    app = PySat_GUI()
    app.mainloop()


if __name__ == '__main__':
    test_tkinter()
