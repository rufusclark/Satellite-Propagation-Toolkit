"""future code for generating sets of future constellations based MOCAT (https://dspace.mit.edu/handle/1721.1/157822)

Please note MOCAT is only valid up to 2000km (LEO - Low Earth Orbit)"""
# TODO: Make sure reasonable MOCAT data is uploaded to github

from typing import Optional

from .datasources import init_sats
from .models import SatelliteSet, Satellite, ts
from .propagation import OrbitalPosition, SGP4Propagation
from .projection import EARTH_RADIUS

import csv
from math import isnan

import numpy as np
from sklearn.neighbors import KernelDensity
from pprint import pprint


MU = 398600  # km^3/s^2, Earth Gravitational Parameter


class OrbitalCapacity:
    """represents the orbital capacity for a given point in time"""

    def __init__(self, years: float, altitude_bands: list["AltitudeBand"]) -> None:
        """create a new object where years is the number of years from now"""
        self.years = years
        self.altitude_bands = altitude_bands

    def plot(self) -> None:
        import matplotlib.pyplot as plt

        plt.scatter(
            [item.mid for item in self.altitude_bands],
            [item._capacity for item in self.altitude_bands]
        )

        plt.xlabel("altitude [km]")
        plt.ylabel("number of objects")
        plt.title(f"Orbital population by altitude in {self.years} years")

        plt.grid(True)
        plt.show()

    def to_SatelliteSet(self, training_set: Optional[SatelliteSet] = None) -> SatelliteSet:
        """generate a new set of Satellites (`SatelliteSet`) based upon the provided training set or all active satellites if not provided.

        this makes the following assumptions when generating the new `SatelliteSet`:
        (1) the altitude distribution is defined by the `OrbitalCapacity` (`Self`)
        (2) the altitude within each `AltitudeBand` is uniformly distributed
        (3) the semi-major axis is approximately equal to the altitude (this is true where the eccentricity is near zero)
        (4) the future inclination, eccentricity and argument of perigee are representative of the training `SatelliteSet`
        (5) the mean anomaly and RAAN are uniformly distributed
        """
        # get training set of satellites if it's not provided
        if not training_set:
            training_set = init_sats()

        # propagate satellite positions to get accurate orbital elements
        propagator = SGP4Propagation()
        time = ts.now()
        training_orbital_positions = propagator.propagate(training_set, time)

        # remove erroneous orbital positions
        training_orbital_positions = [
            position for position in training_orbital_positions if not isnan(position.geo.alt)]

        # filter LEO positions (0-2000km)
        training_orbital_positions = [
            position for position in training_orbital_positions if position.geo.alt < 2000]

        training_eccentricity = np.array(
            [position.eccentricity for position in training_orbital_positions]
        )

        total_capacity = sum(band.capacity for band in self.altitude_bands)

        # (1) estimate uniformly distributed major-axis for each altitude band
        semi_major_axes = np.clip(
            np.concatenate(
                [
                    np.random.uniform(band.low, band.high, band.capacity)
                    for band in self.altitude_bands
                ]
            ), 0, 2000
        ) + EARTH_RADIUS

        # (2) resample inclination, eccentricity and argument of perigee (and vary values)
        indices = np.random.randint(
            0, len(training_eccentricity), size=total_capacity)

        eccentricities = np.clip(
            np.array(
                [training_orbital_positions[i].e +
                 np.random.uniform(0, 0.001) for i in indices]
            ), 0, 1
        )
        inclination = np.clip(
            np.array(
                [training_orbital_positions[i].i +
                 np.random.uniform(-0.1, 0.1) for i in indices]
            ), 0, np.pi
        )
        argument_of_perigee = np.clip(
            np.array(
                [training_orbital_positions[i].sat.argument_of_perigee +
                    np.random.uniform(-0.1, 0.1) for i in indices]
            ), 0, np.pi*2
        )

        # (3) estimate mean anomaly and RAAN using a uniform distribution
        mean_anomaly = np.random.uniform(
            0, np.pi * 2, total_capacity)

        RAAN = np.random.uniform(
            0, np.pi * 2, total_capacity)

        # (4) estimate mean motion parametrically
        mean_motion = np.sqrt(MU / np.pow(semi_major_axes, 3)) * 60

        # (5) copy the additional SGP4 parameters from the sats - ballistic coefficient
        bstar = [training_orbital_positions[i].sat.b_star for i in indices]

        # create new satellite objects
        sats = [
            Satellite.from_orbital_elements(
                name=f"{self.years:.0f}SAT{i:06}",
                eccentricity=eccentricities[i],
                argument_of_perigee=argument_of_perigee[i],
                inclination=inclination[i],
                mean_anomaly=mean_anomaly[i],
                mean_motion=mean_motion[i],
                RAAN=RAAN[i],
                bstar=bstar[i],
                ndot=0,  # not used by SGP4
                nndot=0,  # not used by SGP4
                category=f"{self.years:.0f} year estimate"
            ) for i in range(total_capacity)
        ]

        return SatelliteSet(sats)


class AltitudeBand:
    def __init__(self, low: float, high: float, capacity: float) -> None:
        self.low = low
        self.high = high
        self._capacity = capacity

    @property
    def capacity(self) -> int:
        return round(self._capacity)

    @property
    def density(self) -> float:
        return self._capacity/(self.high - self.low)

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2

    def _filter_orbital_positions(self, orbital_positions: list[OrbitalPosition]) -> list[OrbitalPosition]:
        """take a list of orbital positions and return a new list within the altitude of the altitude band
        """
        return [position for position in orbital_positions if position.geo.alt > self.low and position.geo.alt < self.high]

    def __repr__(self) -> str:
        return f"<AltitudeBand min={self.low}km max={self.high}km capacity={self._capacity} density={self.density:.4f}/km>"


class MOCATReader:
    """Helper class to read MOCAT data from csv and extract relevent data as an `OrbitalCapacity` object
    """

    def __init__(self, filename: str) -> None:
        self.filename = filename

    def read_yrs(self, target_year: float) -> OrbitalCapacity:
        # Read CSV data into data
        print(f"Reading MOCAT output: {self.filename}")
        with open(self.filename, newline="") as f:
            reader = csv.reader(f)
            data = list(reader)

        # Get a list of all generated years
        modelled_years = [float(row[0]) for row in data[1:]]

        # Calculate the closest modelled year and it's index from `modelled_years`
        year, index = min(((v, i) for i, v in enumerate(
            modelled_years)), key=lambda x: abs(x[0] - target_year))

        # check to see if modelled year is similar to target year
        error_threshold = 1.5
        error = abs(year - target_year)
        if error > error_threshold:
            raise Warning(
                f"Target year ({target_year}) for MOCAT orbital capacity is greater than the error threshold of {error_threshold} years. Data is available between {min(modelled_years)} and {max(modelled_years)} years")

        # user output
        print(
            f"Generating OrbitalCapacity for {year} (closest modelled year to target year of {target_year})"
        )

        # generate OrbitalCapacity
        # assume the within of each band is the same

        # read the relevent data from the data (CSV cached data)
        mid_altitudes = list(map(float, data[0][1:]))
        populations = list(map(float, data[index+1][1:]))

        # setup
        altitude_band_width = mid_altitudes[1] - mid_altitudes[0]
        half_altitude_band_width = altitude_band_width/2
        altitude_bands: list[AltitudeBand] = []

        for mid_altitude, population in zip(mid_altitudes, populations):
            altitude_bands.append(
                AltitudeBand(mid_altitude - half_altitude_band_width,
                             mid_altitude + half_altitude_band_width, population)
            )

        return OrbitalCapacity(year, altitude_bands)
