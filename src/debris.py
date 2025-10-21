"""The debris module contains classes and functions for estimating debris flux for each satellite based on orbital parameters and the ESA MASTER v8.0.5 dataset"""

from .models import Satellite
from .propagation import SGP4Propagation, ts, OrbitalPosition
import numpy as np


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

    def estimate_flux(self, sat: Satellite | OrbitalPosition) -> float:
        """estimate the maximum debris flux [#/m²/year] for a given satellite based on its orbital parameters estimated from TLE using the SPG4 model
        """
        if isinstance(sat, Satellite):
            position = SGP4Propagation()._propagate(sat, ts.now())
        else:
            position = sat

        points = np.array(
            [
                [sat.inclination, alt]
                for alt in np.linspace(position.perigee, position.apogee, num=25)
            ]
        )
        flux_points = self._interpolator(points)
        return np.max(flux_points)  # type: ignore

    def _estimate_flux(self, altitude: float, inclination: float) -> float:
        return self._interpolator([inclination, altitude])[0]


debrisFluxDataset = DebrisFluxDataset(
    "./data/MASTER/debris flux data sheet.csv")
