# PROJECT SEPTEMBRE 2020-FEBRUARY 2021
# NORAD BASED SATELLITE TRACKER / FUNCTIONS
# By Enguerran VIDAL

# This .py file contains the multitude of functions used throughout
# the project.

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


###############################################################
#                        FUNCTIONS                            #
###############################################################

def angle(degrees,minutes,seconds):
    ''' Get an angle into full degrees from degress, minutes and seconds of arc '''
    return degrees+minutes/60+seconds/3600

def degrees2radians(angle):
    ''' Transforms degrees into radians '''
    return (2*np.pi*angle)/360

def radians2degrees(angle):
    ''' Transforms radians into degrees '''
    return 360*angle/(2*np.pi)

def gravitational_constant():
    ''' Returns the gravitational Newton's constant '''
    return 6.6740831*10**(-11)

def WireframeSphere(centre=[0,0,0],radius=1,n_meridians=20,n_circles_latitude=None):
    ''' This function creation plottable points for a wireframe sphere usable by Matplotlib '''
    if n_circles_latitude is None:
        n_circles_latitude=max(n_meridians/2,4)
    u,v=np.mgrid[0:2*np.pi:n_meridians*1j, 0:np.pi:n_circles_latitude*1j]
    sphere_x=centre[0]+radius*np.cos(u)*np.sin(v)
    sphere_y=centre[1]+radius*np.sin(u)*np.sin(v)
    sphere_z=centre[2]+radius*np.cos(v)
    return sphere_x,sphere_y,sphere_z

def vector_norm(vector):
    return np.sqrt(vector[0]**2+vector[1]**2+vector[2]**2)

def str_to_float_list(string):
    L=string.split(' ')
    n=len(L)
    for i in range(n):
        L[i]=float(L[i])
    return L

def geo_coordinates(coords):
    ''' Returns the following info : long ( longitude ), lat ( latitude), elevation
        coords must be in this example format :
        43°33'45"N   1°28'09"E   166m '''
    [long,lat,elevation]=coords.split()
    # Elevation handling
    elevation=float(elevation[:-1])
    # Longitude handling
    long=long.replace('°',' ')
    long=long.replace("'",' ')
    long=long.replace('''"''',' ')
    if long[-1]=='S':
        sign=-1
    else:
        sign=1
    long=str_to_float_list(long[:-2])
    long=sign*degrees2radians(angle(long[0],long[1],long[2]))
    lat=lat.replace('°',' ')
    lat=lat.replace("'",' ')
    lat=lat.replace('''"''',' ')
    if lat[-1]=='W':
        sign=-1
    else:
        sign=1
    lat=str_to_float_list(lat[:-2])
    lat=sign*degrees2radians(angle(lat[0],lat[1],lat[2]))
    return long,lat,elevation
    
