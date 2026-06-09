from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Type
import numpy as np


@dataclass(frozen=True)
class Dimension:
    key: str
    label: str

    def __repr__(self):
        return f"<Dimension {self.key}>"


@dataclass(frozen=True)
class Unit:
    key: str
    label: str
    dimension: Dimension
    toBase: Callable
    fromBase: Callable

    def __repr__(self):
        return f"<Unit {self.key}>"

    def convertValueTo(self, value, targetUnit):
        if self.dimension != targetUnit.dimension:
            raise ValueError(f"Incompatible units: {self.key} -> {targetUnit.key}")

        baseValue = self.toBase(value)
        return targetUnit.fromBase(baseValue)


class Quantity:
    def __init__(self, values, unit: Unit):
        self.values = values
        self.unit = unit

    @property
    def dimension(self):
        return self.unit.dimension

    def to(self, targetUnit: Unit):
        convertedValues = self.unit.convertValueTo(self.values, targetUnit)
        return self.__class__(convertedValues, targetUnit)

    def asArray(self):
        return np.asarray(self.values)

    def copy(self):
        return self.__class__(np.array(self.values, copy=True), self.unit)


class DistanceQuantity(Quantity):
    pass


class AngleQuantity(Quantity):
    pass


class VelocityQuantity(Quantity):
    pass


class TimeQuantity(Quantity):
    pass


class AccelerationQuantity(Quantity):
    pass


class EnergyQuantity(Quantity):
    pass


class FrequencyQuantity(Quantity):
    pass


class DimensionlessQuantity(Quantity):
    pass


class Variable:
    def __init__(self, name: str, computeFunction: Callable, quantityType: Type[Quantity], nativeUnit: Unit, defaultUnit: Optional[Unit] = None, allowedUnits: Optional[Iterable[Unit]] = None, label: Optional[str] = None):
        self.name = name
        self.label = label or name
        self.computeFunction = computeFunction
        self.quantityType = quantityType
        self.nativeUnit = nativeUnit
        self.defaultUnit = defaultUnit or nativeUnit
        self.allowedUnits = list(allowedUnits) if allowedUnits is not None else [self.defaultUnit]
        if self.defaultUnit.dimension != self.nativeUnit.dimension:
            raise ValueError(f"Default unit for {name} is incompatible with native unit.")
        for unit in self.allowedUnits:
            if unit.dimension != self.nativeUnit.dimension:
                raise ValueError(f"Allowed unit {unit.key} is incompatible with variable {name}.")

    def computeRaw(self, engine, state, jd):
        return self.computeFunction(engine, state, jd)

    def computeQuantity(self, engine, state, jd):
        return self.quantityType(self.computeRaw(engine, state, jd), self.nativeUnit)

    def compute(self, engine, state, jd, unit: Optional[Unit] = None):
        quantity = self.computeQuantity(engine, state, jd)
        return quantity.to(unit or self.defaultUnit)


class VariableRegistry:
    def __init__(self):
        self.dimensions: Dict[str, Dimension] = {}
        self.units: Dict[str, Unit] = {}
        self.variables: Dict[str, Variable] = {}
        self._buildDimensions()
        self._buildUnits()
        self._buildVariables()

    def _buildDimensions(self):
        self.dimensions = {
            "distance": Dimension("distance", "Distance"),
            "angle": Dimension("angle", "Angle"),
            "time": Dimension("time", "Time"),
            "velocity": Dimension("velocity", "Velocity"),
            "acceleration": Dimension("acceleration", "Acceleration"),
            "specific_energy": Dimension("specific_energy", "Specific energy"),
            "dimensionless": Dimension("dimensionless", "Dimensionless"),
            "frequency": Dimension("frequency", "Frequency"),
        }

    def _buildUnits(self):
        d = self.dimensions
        self.units = {
            # DISTANCE UNITS
            "m": Unit("m", "m", d["distance"], lambda x: x, lambda x: x),
            "km": Unit("km", "km", d["distance"], lambda x: x * 1000.0, lambda x: x / 1000.0),
            "AU": Unit("AU", "AU", d["distance"], lambda x: x * 149597870700.0, lambda x: x / 149597870700.0),
            # ANGLE UNITS
            "rad": Unit("rad", "rad", d["angle"], lambda x: x, lambda x: x),
            "deg": Unit("deg", "deg", d["angle"], np.deg2rad, np.rad2deg),
            "rev": Unit("rev", "rev", d["angle"], lambda x: x * 2.0 * np.pi, lambda x: x / (2.0 * np.pi)),
            # TIME UNITS
            "s": Unit("s", "s", d["time"], lambda x: x, lambda x: x),
            "min": Unit("min", "min", d["time"], lambda x: x * 60.0, lambda x: x / 60.0),
            "h": Unit("h", "h", d["time"], lambda x: x * 3600.0, lambda x: x / 3600.0),
            "day": Unit("day", "day", d["time"], lambda x: x * 86400.0, lambda x: x / 86400.0),
            # SPEED UNITS
            "m/s": Unit("m/s", "m/s", d["velocity"], lambda x: x, lambda x: x),
            "km/s": Unit("km/s", "km/s", d["velocity"], lambda x: x * 1000.0, lambda x: x / 1000.0),
            # ACCELERATION UNITS
            "m/s2": Unit("m/s2", "m/s²", d["acceleration"], lambda x: x, lambda x: x),
            "km/s2": Unit("km/s2", "km/s²", d["acceleration"], lambda x: x * 1000.0, lambda x: x / 1000.0),
            # SPECIFIC ENERGY UNITS
            "J/kg": Unit("J/kg", "J/kg", d["specific_energy"], lambda x: x, lambda x: x),
            "km2/s2": Unit("km2/s2", "km²/s²", d["specific_energy"], lambda x: x * 1.0e6, lambda x: x / 1.0e6),
            # FREQUENCY UNITS
            "1/s": Unit("1/s", "1/s", d["frequency"], lambda x: x, lambda x: x),
            "rev/day": Unit("rev/day", "rev/day", d["frequency"], lambda x: x * 2.0 * np.pi / 86400.0, lambda x: x * 86400.0 / (2.0 * np.pi)),
            # DIMENSIONLESS UNITS
            "none": Unit("none", "", d["dimensionless"], lambda x: x, lambda x: x),
        }

    def _buildVariables(self):
        units = self.units
        angleUnits = [units["deg"], units["rad"], units["rev"]]
        distanceUnits = [units["km"], units["m"]]
        velocityUnits = [units["km/s"], units["m/s"]]
        timeUnits = [units["s"], units["min"], units["h"], units["day"]]
        specificEnergyUnits = [units["km2/s2"], units["J/kg"]]
        frequencyUnits = [units["1/s"], units["rev/day"]]
        self.variables = {
            "ALTITUDE": Variable("ALTITUDE", lambda e, s, jd: s["altitude"], DistanceQuantity, units["km"], units["km"], distanceUnits),
            "LATITUDE": Variable("LATITUDE", lambda e, s, jd: s["latitude"], AngleQuantity, units["rad"], units["deg"], angleUnits),
            "LONGITUDE": Variable("LONGITUDE", lambda e, s, jd: s["longitude"], AngleQuantity, units["rad"], units["deg"], angleUnits),
            "R_ECI_X": Variable("R_ECI_X", lambda e, s, jd: s["rECI"][:, 0], DistanceQuantity, units["km"], units["km"], distanceUnits),
            "R_ECI_Y": Variable("R_ECI_Y", lambda e, s, jd: s["rECI"][:, 1], DistanceQuantity, units["km"], units["km"], distanceUnits),
            "R_ECI_Z": Variable("R_ECI_Z", lambda e, s, jd: s["rECI"][:, 2], DistanceQuantity, units["km"], units["km"], distanceUnits),
            "V_ECI_X": Variable("V_ECI_X", lambda e, s, jd: s["vECI"][:, 0], VelocityQuantity, units["km/s"], units["km/s"], velocityUnits),
            "V_ECI_Y": Variable("V_ECI_Y", lambda e, s, jd: s["vECI"][:, 1], VelocityQuantity, units["km/s"], units["km/s"], velocityUnits),
            "V_ECI_Z": Variable("V_ECI_Z", lambda e, s, jd: s["vECI"][:, 2], VelocityQuantity, units["km/s"], units["km/s"], velocityUnits),
            "RADIAL_VELOCITY": Variable("RADIAL_VELOCITY", lambda e, s, jd: e.radialTangentialVelocity(s["rECI"], s["vECI"])[0], VelocityQuantity, units["km/s"], units["km/s"], velocityUnits),
            "TANGENTIAL_VELOCITY": Variable("TANGENTIAL_VELOCITY", lambda e, s, jd: e.radialTangentialVelocity(s["rECI"], s["vECI"])[1], VelocityQuantity, units["km/s"], units["km/s"], velocityUnits),
            "FLIGHT_PATH_ANGLE": Variable("FLIGHT_PATH_ANGLE", lambda e, s, jd: e.flightPathAngle(s["rECI"], s["vECI"]), AngleQuantity, units["rad"], units["deg"], angleUnits),
            "TRUE_ANOMALY": Variable("TRUE_ANOMALY", lambda e, s, jd: e.trueAnomaly(s["rECI"], s["vECI"]), AngleQuantity, units["rad"], units["deg"], angleUnits),
            "INCLINATION": Variable("INCLINATION", lambda e, s, jd: e.inclination(s["rECI"], s["vECI"]), AngleQuantity, units["rad"], units["deg"], angleUnits),
            "RAAN": Variable("RAAN", lambda e, s, jd: e.raan(s["rECI"], s["vECI"]), AngleQuantity, units["rad"], units["deg"], angleUnits),
            "ARGUMENT_OF_PERIGEE": Variable("ARGUMENT_OF_PERIGEE", lambda e, s, jd: e.argumentOfPerigee(s["rECI"], s["vECI"]), AngleQuantity, units["rad"], units["deg"], angleUnits),
            "MEAN_ANOMALY": Variable("MEAN_ANOMALY", lambda e, s, jd: e.meanAnomaly(s["rECI"], s["vECI"]), AngleQuantity, units["rad"], units["deg"], angleUnits),
            "ECCENTRICITY": Variable("ECCENTRICITY", lambda e, s, jd: e.eccentricity(s["rECI"], s["vECI"]), DimensionlessQuantity, units["none"], units["none"], [units["none"]]),
            "ORBITAL_PERIOD": Variable("ORBITAL_PERIOD", lambda e, s, jd: e.orbitalPeriodFromState(s["rECI"], s["vECI"]), TimeQuantity, units["s"], units["min"], timeUnits),
            "SPECIFIC_ENERGY": Variable("SPECIFIC_ENERGY", lambda e, s, jd: e.specificEnergy(s["rECI"], s["vECI"]), EnergyQuantity, units["km2/s2"], units["km2/s2"], specificEnergyUnits),
            "SEMI_MAJOR_AXIS": Variable("SEMI_MAJOR_AXIS", lambda e, s, jd: e.semiMajorAxis(s["rECI"], s["vECI"]), DistanceQuantity, units["km"], units["km"], distanceUnits),
            "MEAN_MOTION": Variable("MEAN_MOTION", lambda e, s, jd: e.meanMotion(s["rECI"], s["vECI"]), FrequencyQuantity, units["1/s"], units["rev/day"], frequencyUnits),
            "SOLAR_EXPOSURE": Variable("SOLAR_EXPOSURE", lambda e, s, jd: e.solarExposure(jd, s["rECI"]), DimensionlessQuantity, units["none"], units["none"],[units["none"]]),
            "GROUND_SPEED": Variable("GROUND_SPEED", lambda e, s, jd: e.groundSpeed(s["vECI"], jd), VelocityQuantity, units["km/s"], units["km/s"], velocityUnits),
        }

    def getUnit(self, unitKey):
        return self.units.get(unitKey)

    def getVariable(self, variableName):
        if variableName is None:
            return None
        return self.variables.get(str(variableName).upper())

    def getAvailableVariables(self):
        return list(self.variables.keys())

    def getAllowedUnits(self, variableName):
        variable = self.getVariable(variableName)
        if variable is None:
            return []
        return variable.allowedUnits

    def getDefaultUnit(self, variableName):
        variable = self.getVariable(variableName)
        if variable is None:
            return None
        return variable.defaultUnit


if __name__ == '__main__':
    variableRegistry = VariableRegistry()