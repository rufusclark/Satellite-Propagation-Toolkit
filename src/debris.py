"""The debris module contains classes and functions for estimating debris flux for each satellite based on orbital parameters and the ESA MASTER v8.0.5 dataset

Please note this only supports altitudes of 300-2000km"""

from .models import Satellite
from .propagation import SGP4Propagation, ts, OrbitalPosition
import numpy as np


class OutOfBoundError(Exception):
    pass


class DebrisFluxDataset:
    """Singleton class representing the debris flux dataset from ESA MASTER v8.0.5"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, filename: str) -> None:
        from scipy.interpolate import RegularGridInterpolator

        # read file
        data = np.genfromtxt(
            filename,
            delimiter=',',
            skip_header=9,
            filling_values=np.nan
        )

        data = np.delete(data, 1, axis=0)  # remove blank row
        data = np.delete(data, 1, axis=1)  # remove blank column

        # extract axes
        altitude_axis = data[0, 1:]
        inclination_axis = data[1:, 0]

        # extract flux data
        flux_data = data[1:, 1:]

        self._interpolator = RegularGridInterpolator(
            (inclination_axis, altitude_axis),
            flux_data,
            method="linear"
        )

    def interpolator(self, points):
        """get the internal interpolator object"""
        if (alt := np.max(points[:, 1])) > 2000 or np.min(points[:, 1]) < 300:
            raise OutOfBoundError(
                f"altitude ({alt:.2f}km) out of bounds, must be between 300km and 2000km"
            )
        return self._interpolator(points)

    def estimate_max_flux(self, sat: Satellite | OrbitalPosition) -> float:
        """estimate the maximum debris flux [#/m²/year] for a given satellite based on its orbital parameters estimated from TLE using the SPG4 model
        """
        if isinstance(sat, Satellite):
            position = SGP4Propagation()._propagate(sat, ts.now())
        else:
            position = sat

        n = min(int(5 * (20 ** position.eccentricity)) +
                10, 100)  # optimise for orbit eccentricity
        points = np.array(
            [
                [sat.inclination, alt]  # type: ignore
                for alt in np.linspace(position.perigee, position.apogee, num=n)
            ]
        )
        flux_points = self.interpolator(points)
        return np.max(flux_points)  # type: ignore

    def estimate_average_flux(self, sat: Satellite | OrbitalPosition) -> float:
        """estimate the average debris flux [#/m²/year] for a given satellite based on its orbital parameters estimated from TLE using the SPG4 model
        """
        if isinstance(sat, Satellite):
            position = SGP4Propagation()._propagate(sat, ts.now())
        else:
            position = sat

        n = min(int(5 * (20 ** position.eccentricity)) +
                10, 100)  # optimise for orbit eccentricity
        points = np.array(
            [
                [sat.inclination, alt]  # type: ignore
                for alt in np.linspace(position.perigee, position.apogee, num=n)
            ]
        )
        flux_points = self.interpolator(points)
        return np.mean(flux_points)  # type: ignore

    def _estimate_flux(self, altitude: float, inclination: float) -> float:
        return self.interpolator([inclination, altitude])[0]


debrisFluxDataset = DebrisFluxDataset(
    "./data/MASTER/debris flux data sheet.csv")
