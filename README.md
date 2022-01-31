# PySatTracker Project (2020/2022)
![Github Stars](https://img.shields.io/github/stars/EnguerranVidal/PySatTracker?style=social)
![Github Watchers](https://img.shields.io/github/watchers/EnguerranVidal/PySatTracker?style=social)

![GitHub license](https://img.shields.io/github/license/EnguerranVidal/PySatTracker)
![GitHub last commit](https://img.shields.io/github/last-commit/EnguerranVidal/PySatTracker)
![Github issus open](https://img.shields.io/github/issues-raw/EnguerranVidal/PySatTracker)
![Github issus closed](https://img.shields.io/github/issues-closed-raw/EnguerranVidal/PySatTracker)
[![HitCount](http://hits.dwyl.com/EnguerranVidal/PySatTracker.svg?style=flat)](http://hits.dwyl.com/EnguerranVidal/PySatTracker)

[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)
![GitHub repo size](https://img.shields.io/github/repo-size/EnguerranVidal/PySatTracker)
[![wakatime](https://wakatime.com/badge/github/EnguerranVidal/PySatTracker.svg)](https://wakatime.com/badge/github/EnguerranVidal/PySatTracker)

<p align="center">
  <img src="https://user-images.githubusercontent.com/80796115/151719481-c8c6e5fd-38d5-4aa7-8eff-4e4b8bde5a7e.png">
</p>

## Presentation

This project vows to create a software capable of tracking known satellites with a huge accuracy as well as allowing the pursue of propagating a specified orbit using perturbations calculations.
It will consist of two different systems : 
- a satellite tracker using TLE Data for quick predictions for known satellites in the NORAD Database.
- a satellite propagator using ephemeride or user-inputted data in order to predict their future orbits, accounting for various perturbations such as the Moon and Sun, solar radiation or the roughness of the geoid.

## Satellite Tracker 

This satellite tracker uses TLE Data provided by NORAD in order to estimate the position of satellites at certain times. We used to be doing the estimation in a simple naive way although the estimator needs a SGP4 algorithm in order to provide accurate results.
 
 ### TLE Data:
 
 TLE or Two Line Element is a format capable of transmitting info about a satellte's position easily created and updated regularly by NORAD. It gives us an access to some values of our satellite's orbit through some Keplerian parameters that can be propagated through a SPG4 estimator taking into account perturbations of the satellite's trajectory.
 A Two Line Elements format looks like so :
 
ICESAT
1 27642U 03002A   03175.25018279  .00000722  00000-0  75456-4 0  1631
2 27642  94.0031 263.4514 0002250  85.5696 274.5785 14.90462832 24163

Our program updates its NORAD TLE database by downloading it directly from the **[Celestrak](https://www.celestrak.com/NORAD/elements/)** website where many categories can be found. We managed to associate an active satellites database with many famous debris families such as the Iridium 33 debris. These multiple databases can be switched on/off via the **Tracker/Preferences** option through checkboxes as shown right below :

<p align="center">
  <img src="https://user-images.githubusercontent.com/80796115/151730082-01c1642c-0534-40e2-b7a5-379de6ce93fa.png">
</p>

### SGP4 Estimator

Keplerian parameters from TLE Data cannot be used as is and need a specific algorithm in order to estimate the associated orbit. This is the role of the SGP4 estimator algorithm. It is provided by the **[sgp4](https://pypi.org/project/sgp4/)** Python library in our case.

## Future Version ?

I first announced the new version to be finilized around the end of Summer 2021 but the GUI and my attempts at creating my own SGP4 propagator lengthen the amount of work needed. But since some personal projects have been finished and college gave me a slight breaks between exams and assignements, I could finally get back to it and finish this version with a SGP4 estimator (not home made however). The promised GUI is finally done, with a lot of work still needed in creating the 3D view and propagator mechanics as well as expand the amount of shown data.

Future additions are as follows :
- Display some info on selected satellites, already found a database for this purpose.
- A satellite propagator for orbit prediction takin into account multiple perturbations such as the Moon and Sun, drag, the geoid potential and Solar radiation pressure.
- A way of creating our own satellite and implementing it into the system.
- Get the ground-track display to be more interactive, repsonding to selection on the map for displaying the ground-track for example.
- An interactive 3D display of each satellite trajectory.
- A over-head passings polar plot, possibly a tool giving multiple passages throughout the TLE data lifespan.
- Creating a play/pause/forward bar for time management/travel to see past trajectories.
- Better the GUI visually through the use of custom themes from **[ttkthemes](https://ttkthemes.readthedocs.io/en/latest/themes.html)**
