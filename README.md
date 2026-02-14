# PySatTracker
![Github Stars](https://img.shields.io/github/stars/EnguerranVidal/PySatTracker?style=social)
![Github Watchers](https://img.shields.io/github/watchers/EnguerranVidal/PySatTracker?style=social)

![GitHub license](https://img.shields.io/github/license/EnguerranVidal/PySatTracker)
![GitHub last commit](https://img.shields.io/github/last-commit/EnguerranVidal/PySatTracker)
![Github issus open](https://img.shields.io/github/issues-raw/EnguerranVidal/PySatTracker)
![Github issus closed](https://img.shields.io/github/issues-closed-raw/EnguerranVidal/PySatTracker)

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31019/)
![GitHub repo size](https://img.shields.io/github/repo-size/EnguerranVidal/PySatTracker)

<img width="937" height="858" alt="PySatTracker" src="https://github.com/user-attachments/assets/8fd88d61-2180-4c93-b83f-378102c3993e" />

## SUMMARY

<div style="text-align: justify"> **PySatTracker** is an interactive satellite tracking and visualization tool featuring a 2D Earth map and a 3D OpengGL space view. The system renders satellites and orbits by combining a SGP4 orbital propagation with physically accurate Earth and Sun geometry. The project focuses on implementing clear frame separation, correct astronomical transformations and orbital mechanics, in a clear rendering architecture. </div>

<div style="text-align: justify"> The tool uses a Two Line Elements database extracted daily from the <a href="https://celestrak.org">Celestrak</a> archive, featuring all currently active satellites in orbit around Earth. </div>

## INSTALLATION




```
git clone https://github.com/EnguerranVidal/PySatTracker.git
```

```
cd PySatTracker
```

```
conda create --name pysattracker python=3.10
conda activate pysattracker
```

```
pip install -r requirements.txt
```


## USING THE CODE

To start the tool, the following command can be entered :
```
cd PySatTracker
conda activate pysattracker
python3 main.py
