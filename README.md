# PySatTracker
[![GitHub watchers](https://badgen.net/github/watchers/EnguerranVidal/PyStrato/)](https://GitHub.com/EnguerranVidal/PyStrato/watchers/) [![GitHub stars](https://badgen.net/github/stars/EnguerranVidal/PyStrato)](https://GitHub.com/EnguerranVidal/PyStrato/stargazers/)
![GitHub license](https://img.shields.io/github/license/EnguerranVidal/PySatTracker)

[![GitHub branches](https://badgen.net/github/branches/EnguerranVidal/PyStrato)](https://github.com/EnguerranVidal/PyStrato/)
[![GitHub commits](https://badgen.net/github/commits/EnguerranVidal/PyStrato)](https://github.com/EnguerranVidal/PyStrato/) 
![GitHub last commit](https://img.shields.io/github/last-commit/EnguerranVidal/PySatTracker)
![Github issus open](https://img.shields.io/github/issues-raw/EnguerranVidal/PySatTracker)
![Github issus closed](https://img.shields.io/github/issues-closed-raw/EnguerranVidal/PySatTracker)


![GitHub repo size](https://img.shields.io/github/repo-size/EnguerranVidal/PySatTracker)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31019/)

<img width="937" height="858" alt="PySatTracker" src="https://github.com/user-attachments/assets/8fd88d61-2180-4c93-b83f-378102c3993e" />

## SUMMARY

<div style="text-align: justify"> PySatTracker is an interactive satellite tracking and visualization tool featuring a 2D Earth map and a 3D OpengGL space view. The system renders satellites and orbits by combining a SGP4 orbital propagation with physically accurate Earth and Sun geometry. The project focuses on implementing clear frame separation, correct astronomical transformations and orbital mechanics, in a clear rendering architecture. </div>

<div style="text-align: justify"> The tool uses a Two Line Elements database extracted daily from the <a href="https://celestrak.org">Celestrak</a> archive, featuring all currently active satellites in orbit around Earth. </div>

## INSTALLATION

1. Cloning the Github Repository.
```
git clone https://github.com/EnguerranVidal/PySatTracker.git
```
2. Going in the Repository Directory.
```
cd PySatTracker
```
3. Creating Conda Environment and activating it.
```
conda create --name pysattracker python=3.10
```
```
conda activate pysattracker
```
4. Installing PySatTracker Requirements.
```
pip install -r requirements.txt
```


## USING THE CODE

To start the tool, the following steps can be followed :
1. Going in the Repository Directory.
```
cd PySatTracker
```
2. Activating the Conda Environment.
```
conda activate pysattracker
```
3. Running the main.py file.
```
python3 main.py
```

## ROADMAP

| Feature | Description | Status |
|-------|-------------|--------|
| 2D Map Shading | Adding night shadow shader copying the 3D View rendition | Testing |
| 2D Map Optimization | Optimize 2D Map rendition for GPU usage | In Progress |
| Line Plots | Adding line plots able to graph wanted calculated values | In Progress |
| Polar Plots | Adding polar plots able to graph wanted calculated values | Planned |
| Orbit Coverage | Predict visible satellite ground coverage | Planned |
| Pass Predictions | Predict visible satellite passes for observers | Planned |
| 3D View Optimization | Optimize 3D View rendition for GPU usage | Planned |
| Orbital Calculations Optimization | Optimize orbital calculations for GPU usage | Planned |
| Object Grouping | Adding the ability to group visible objects | Planned |

<p align="left">(<a href="#readme-top">back to top</a>)</p>
