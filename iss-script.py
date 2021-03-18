# PROJECT SEPTEMBRE 2020-FEBRUARY 2021
# NORAD BASED SATELLITE TRACKER / ISS-SCRIPT
# By Enguerran VIDAL

# This file contains an example script for this project where it displays
# the ground trackof the ISS for one orbital period from where it is at
# the moment.

###############################################################
#                           IMPORTS                           #
###############################################################


#-----------------MODULES
import numpy as np
import matplotlib.pyplot as plt
import time
import calendar
import datetime
from mpl_toolkits.mplot3d import Axes3D

import cartopy.crs as ccrs
import cartopy.feature as cfeature

import os
import sys
#-----------------PYTHON FILES
from __classes import*
from __functions import*
   

##################################
##            SCRIPT            ##
##################################

station_toulouse='''43°33'45"N   1°28'09"E   166m'''
station_test='''51.7°0'0"S   114.4°0'0"E   0m'''

X=Tracker(load_online=True,filename='NORAD.txt')
X.focus("ISS")
X.ground_station(station_test)
X.draw2D_period(n=1,moment='immediate')

#X.above_passings(time_range='6h',save=True)
