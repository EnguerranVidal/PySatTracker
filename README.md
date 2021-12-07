# Python Satellite Tracker and Propagator (2020/2021)

[![HitCount](http://hits.dwyl.com/EnguerranVidal/PySatTracker.svg?style=flat)](http://hits.dwyl.com/EnguerranVidal/PySatTracker) [![wakatime](https://wakatime.com/badge/github/EnguerranVidal/PySatTracker.svg)](https://wakatime.com/badge/github/EnguerranVidal/PySatTracker)


This project vows to create a software capble of tracking satellites or propagate their orbits to complete many predictions such as pass-bys, passing over head, communication capabilities ...
It will consist of two different systems : 
- a satellite tracker using TLE Data for quick predictions for known satellites in the NORAD Database.
- a satellite propagator using ephemeride or user-inputted data in order to predict their future orbits, accounting for various perturbations.

## Satellite Tracker 

This satellite tracker uses TLE Data provided by NORAD in order to estimate the position of satellites at certain times. We used to be doing the estimation in a simple naive way although the estimator needs a SGP4 algorithm in order to provide accurate results.
 
 ### TLE Data:
 
 TLE or Two Line Element is a format capable of transmitting info about a satellte's position easily created and updated regularly by NORAD. It gives us an access to some values of our satellite's orbit through some Keplerian parameters that can be propagated throgh a SPG8 estimator taking into account perturbations of the satellite's trajectory.
 A Two Line Elements format looks like so :
 
ICESAT
1 27642U 03002A   03175.25018279  .00000722  00000-0  75456-4 0  1631
2 27642  94.0031 263.4514 0002250  85.5696 274.5785 14.90462832 24163

Our program updates its NORAD TLE database by downloading it directly from the **[AMSAT website](https://www.amsat.org/tle/current/nasabare.txt)** at : 
I will try later to vary our sources in order to get a greater number of possible tracking targets.

### SGP4 Estimator

Kepelrian parameters from TLE Data cannot be used as is and need a specific algorithm in order to estimate their orbit. This is the role of the SGP4 estimator algorithm thta we use. It is provided by the **[sgp4](https://pypi.org/project/sgp4/)** Python library.

## Future Version ?
 I am currently working on a GUI for the code, which I have initially made in PyQt5 and have tried implementing a mapbox similar to one you could find on Google Maps to better showcase the course and groundtracks of specific objects. This took a long time, first trying to use Pygame to create from scratch then trying Leaflet in Python, Folium to finally settle on the use of MapBox in Plotly which is still not 100% certain to remain as its use is quite funky.

I first announced the new version to be finilized around the end of Summer 2021 but the GUI and my attempts at creating my own SGP4 propagator lengthen the amount of work needed. But since some personal projects have been finished and college gave me a slight breaks between exams and assignements, I could finally get back to it and finish this ne version with a SGP4 estimator (not home made however).

Future additions are as follows :
- An interactive GUI with the possibility of selecting satellites from a database and display some info on them, already found a database for this purpose
- A satellite propagator for orbit prediction takin into account multiple perturbations such as the Moon and Sun, drag, the geoid potential and Solar radiation pressure.
- A way of creating our own satellite and implementing it into the system
- An interactive map for ground tracks displaying
- An interactive 3D dispaly of overhead-passings of Satellite with a polar plot of the sky above your location. 
