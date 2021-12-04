from sat_tracker.tracker import *
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

def test_database():
    pass


if __name__ == '__main__':
    ISS_tracking()
