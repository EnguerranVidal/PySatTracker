import numpy as np


class Dimension:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<Dimension {self.name}>"


class Unit:
    def __init__(self, name, dimension, toSI, fromSI):
        self.name = name
        self.dimension = dimension
        self.toSI = toSI
        self.fromSI = fromSI

    def __repr__(self):
        return f"<Unit {self.name}>"

    def convertToUnit(self, value, otherUnit):
        if self.dimension != otherUnit.dimension:
            raise ValueError(f"Incompatible units: {self.name} → {otherUnit.name}")
        siValue = self.toSI(value)
        return otherUnit.fromSI(siValue)


class Quantity:
    def __init__(self, values, unit: Unit):
        self.values = values
        self.unit = unit

    def to(self, newUnit: Unit):
        return Quantity(self.unit.convertToUnit(self.values, newUnit), newUnit)


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


class Variable:
    def __init__(self, name, computeFunction, quantityType, defaultUnit, allowedUnits):
        self.name = name
        self.computeFunction = computeFunction
        self.quantityType = quantityType
        self.defaultUnit = defaultUnit
        self.allowedUnits = allowedUnits

    def compute(self, engine, state, jd):
        return self.computeFunction(engine, state, jd)


class VariableRegistry:
    def __init__(self):
        self.dimensions = {}
        self.units = {}
        self.variables = {}
        self._buildDimensions()
        self._buildUnits()
        self._buildVariables()

    def _buildDimensions(self):
        self.dimensions = {
            "distance": Dimension("distance"),
            "angle": Dimension("angle"),
            "time": Dimension("time"),
            "velocity": Dimension("velocity"),
            "acceleration": Dimension("acceleration"),
            "energy": Dimension("energy"),
            "dimensionless": Dimension("dimensionless"),
        }

    def _buildUnits(self):
        d = self.dimensions
        self.units = {
            "m": Unit("m", d["distance"], lambda x: x, lambda x: x),
            "km": Unit("km", d["distance"], lambda x: x * 1000, lambda x: x / 1000),
            "rad": Unit("rad", d["angle"], lambda x: x, lambda x: x),
            "deg": Unit("deg", d["angle"], np.deg2rad, np.rad2deg),
            "s": Unit("s", d["time"], lambda x: x, lambda x: x),
            "min": Unit("min", d["time"], lambda x: x * 60, lambda x: x / 60),
            "h": Unit("h", d["time"], lambda x: x * 3600, lambda x: x / 3600),
            "day": Unit("h", d["time"], lambda x: x * 86400, lambda x: x / 86400),
            "m/s": Unit("m/s", d["velocity"], lambda x: x, lambda x: x),
            "km/s": Unit("km/s", d["velocity"], lambda x: x * 1000, lambda x: x / 1000),
            "J/kg": Unit("J/kg", d["energy"], lambda x: x, lambda x: x),
            "none": Unit("none", d["dimensionless"], lambda x: x, lambda x: x),
        }

    def _buildVariables(self):
        units = self.units
        self.variables = {
            "ALTITUDE": Variable("ALTITUDE", lambda e, s, jd: s['altitude'], DistanceQuantity, units["km"], [units["km"], units["m"]]),
            "LATITUDE": Variable("LATITUDE", lambda e, s, jd: s['latitude'], AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "LONGITUDE": Variable("LONGITUDE", lambda e, s, jd: s['longitude'], AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "R_ECI_X": Variable("R_ECI_X", lambda e, s, jd: s['rECI'][:, 0], DistanceQuantity, units["km"], [units["km"], units["m"]]),
            "R_ECI_Y": Variable("R_ECI_Y", lambda e, s, jd: s['rECI'][:, 1], DistanceQuantity, units["km"], [units["km"], units["m"]]),
            "R_ECI_Z": Variable("R_ECI_Z", lambda e, s, jd: s['rECI'][:, 2], DistanceQuantity, units["km"], [units["km"], units["m"]]),
            "V_ECI_X": Variable("V_ECI_X", lambda e, s, jd: s['vECI'][:, 0], VelocityQuantity, units["km/s"], [units["km/s"], units["m/s"]]),
            "V_ECI_Y": Variable("V_ECI_Y", lambda e, s, jd: s['vECI'][:, 1], VelocityQuantity, units["km/s"], [units["km/s"], units["m/s"]]),
            "V_ECI_Z": Variable("V_ECI_Z", lambda e, s, jd: s['vECI'][:, 2], VelocityQuantity, units["km/s"], [units["km/s"], units["m/s"]]),
            "RADIAL_VELOCITY": Variable("RADIAL_VELOCITY", lambda e, s, jd: e.radialTangentialVelocity(s['rECI'], s['vECI'])[0], VelocityQuantity, units["km/s"], [units["km/s"], units["m/s"]]),
            "TANGENTIAL_VELOCITY": Variable("TANGENTIAL_VELOCITY", lambda e, s, jd: e.radialTangentialVelocity(s['rECI'], s['vECI'])[1], VelocityQuantity, units["km/s"], [units["km/s"], units["m/s"]]),
            "FLIGHT_PATH_ANGLE": Variable("FLIGHT_PATH_ANGLE", lambda e, s, jd: e.flightPathAngle(s['rECI'], s['vECI']), AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "TRUE_ANOMALY": Variable("TRUE_ANOMALY", lambda e, s, jd: e.trueAnomaly(s['rECI'], s['vECI']), AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "INCLINATION": Variable("INCLINATION", lambda e, s, jd: e.inclination(s['rECI'], s['vECI']), AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "RAAN": Variable("RAAN", lambda e, s, jd: e.raan(s['rECI'], s['vECI']), AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "ARGUMENT_OF_PERIGEE": Variable("ARGUMENT_OF_PERIGEE", lambda e, s, jd: e.argumentOfPerigee(s['rECI'], s['vECI']), AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "ECCENTRICITY": Variable("ECCENTRICITY", lambda e, s, jd: e.eccentricity(s['rECI'], s['vECI']), Quantity, units["none"], [units["none"]]),
            "MEAN_MOTION": Variable("MEAN_MOTION", lambda e, s, jd: e.meanMotion(s['rECI'], s['vECI']), Quantity, units["none"], [units["none"]]),
            "MEAN_ANOMALY": Variable("MEAN_ANOMALY", lambda  e, s, jd: e.meanAnomaly(s['rECI'], s['vECI']), AngleQuantity, units["rad"], [units["rad"], units["deg"]]),
            "ORBITAL_PERIOD": Variable("ORBITAL_PERIOD", lambda e, s, jd: e.orbitalPeriodFromState(s['rECI'], s['vECI']), TimeQuantity, units["s"], [units["s"], units["min"], units["h"]]),
            "SPECIFIC_ENERGY": Variable("SPECIFIC_ENERGY", lambda e, s, jd: e.specificEnergy(s['rECI'], s['vECI']), Quantity, units["J/kg"], [units["J/kg"]]),
            "SEMI_MAJOR_AXIS" : Variable("SEMI_MAJOR_AXIS", lambda e, s, jd: e.semiMajorAxis(s['rECI'], s['vECI']), DistanceQuantity, units["km"], [units["km"], units["m"]]),
        }

    def getVariable(self, variableName):
        return self.variables.get(variableName, None)


if __name__ == '__main__':
    variableRegistry = VariableRegistry()