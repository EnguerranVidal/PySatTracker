# Norad-Satellite-Tracker (2020/2021)

[![wakatime](https://wakatime.com/badge/github/EnguerranVidal/PySatTracker.svg)](https://wakatime.com/badge/github/EnguerranVidal/PySatTracker)

 This projects focuses on using Norad provided TLE format data in order to track satellites orbiting around Earth and predict their overhead-passings using an analytical propagation estimator. For this project, we used Michel Capderou's book **"Satellites : de Kepler au GPS"** which describes in great details the space and orbital mechanics that we applied here for this satellite tracker.
 We have two main .py files so far :
 - **__classes.py** : This .py file contains the five classes used throughout the project : **NORAD_TLE_Database** (fetches the NORAD TLE Data from the AMSAT website and extracts the needed info), **Orbit** (renders and commands calculations regarding orbital mechanics and its associated perturbations),**Earth** (takes care of the obverser'sposition and calculatiosn regarding transformations from fixed to inertial reference frame, GMST calculation, etc...), **Time_Manager** (takes care of time values, timestamps, julian dates, etc...) and **Tracker** ( focuses on a given traget and plots the results from all four other classes)
 - **__functions.py** : Contains the different fucntions used in **__classes.py**.
 
 This project began back in September 2020 and was put on hold in late October before being worked on again in late January. I am currently working on succesfully predicting over-head passings, some issues could be raised on the crtopy usage as well. I will be trying to fiw those in a few weeks.
 
 This code uses Numpy, Matplotlib, Time, Calendar, Os, Datetime and Cartopy. You should try and create an environment containing these libraries before running it.
 
 # TLE Data:
 
 TLE or Two Line Element is a format capable of transmitting info about a satellte's position easily created and updated regularly by NORAD. It gives us an access to some values of our satellite's orbit through some Keplerian parameters that can be propagated throgh a SPG8 estimator taking into account perturbations of the satellite's trajectory.
 A Two Line Elements format looks like so :
 
ICESAT
1 27642U 03002A   03175.25018279  .00000722  00000-0  75456-4 0  1631
2 27642  94.0031 263.4514 0002250  85.5696 274.5785 14.90462832 24163

Our program updates its NORAD TLE database by downloading it directly from the AMSAT website at : https://www.amsat.org/tle/current/nasabare.txt
I will try later to vary our sources in order to get a greater number of possible tracking targets.
