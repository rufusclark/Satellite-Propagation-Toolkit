"""The debris module contains classes and functions for estimating debris flux for each satellite based on orbital parameters and the ESA MASTER v8.0.5 dataset (Flux of debris [# m^-2 yr^-1] vs Altitude [km] and Inclination [deg] year of reference: 2024 - size threshold: >1cm - MASTER-8.0.5)

Please note this only supports altitudes of 200-1000000km"""

from .models import Satellite
from .propagation import SGP4Propagation, ts, OrbitalPosition
import numpy as np


class OutOfBoundError(Exception):
    pass


class _DebrisFluxDataset:
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

        # extrapolate high altitude flux data linearly based on post-GSO data
        upper_bound = 37200  # km
        if altitude_axis[-1] > upper_bound:
            # get the index of first post target altitude
            upper_bound_index = np.argmax(altitude_axis < upper_bound)

            # extract data
            interpolation_data = data[:, [upper_bound_index, -1]]
            interpolation_altitudes = altitude_axis[[upper_bound_index, -1]]

            # linear interpolation along each row
            interpolated_altitude = 1000000  # km
            interpolated_data = np.array([
                np.interp(interpolated_altitude, interpolation_altitudes, interpolation_data[i]) for i in range(interpolation_data.shape[0])
            ])

            # extend existing dataset
            altitude_axis = np.append(altitude_axis, interpolated_altitude)
            flux_data = np.column_stack((flux_data, interpolated_data[1:]))

        # cache bounds
        self._altitude_min = altitude_axis[0]
        self._altitude_max = altitude_axis[-1]

        # create interpolator
        self._interpolator = RegularGridInterpolator(
            (inclination_axis, altitude_axis),
            flux_data,
            method="linear"
        )

    def interpolator(self, points):
        """get the internal interpolator object"""
        # TODO: Estimate debris flux outside of upper bound - potentially add a final altitude at 1Mkm to the end of the dataset to allow effective interpolation out to a crazy high altitude?

        if (alt := np.max(points[:, 1])) > self._altitude_max or np.min(points[:, 1]) < self._altitude_min:
            raise OutOfBoundError(
                f"altitude ({alt:.2f}km) out of bounds, must be between {self._altitude_min:.1f}km and {self._altitude_max:.1f}m"
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


debrisFluxDataset = _DebrisFluxDataset(
    "./data/MASTER/debris flux data sheet (200-40000km).csv")
