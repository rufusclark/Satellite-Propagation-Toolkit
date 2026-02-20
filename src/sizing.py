"""The sizing module contains functions and methods for approximating the size, mass, mission duration and other related factors of Satellites based on TLE data"""
from .models import Satellite, SatelliteSet
from .propagation import SGP4Propagation, ts

import numpy as np

from typing_extensions import Self
from datetime import datetime

class _UCSSizingDataset:
    """Singleton class representing the UCS Satellite Database and approximations based on it's data.
    
    Primary data sources, https://www.ucs.org/resources/satellite-database
    
    Pleae not the datasource might be updated from the published online version as this hasn't been updated since 2023 and is unlikely to be updated soon"""
    _instance = None

    def __new__(cls, *args, **kwards) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, filename: str) -> None:
        import pandas as pd

        # read data from csv
        df = pd.read_csv(filename, encoding="utf-8-sig")
        data = df.to_numpy()

        # extract useful columns
        NORAD_CAT_ID_COL = 26
        LAUNCH_MASS_COL = 16
        self._norad_cat_ids = data[:, NORAD_CAT_ID_COL]
        self._launch_masses = data[:, LAUNCH_MASS_COL]

        # setup interpolator functions
        self._interpolator_func: dict[str, function] = {}

    def lookup_launch_mass(self, sat: Satellite) -> float:
        """get the launch mass of the `Satellite` from the UCS database in kg.

        Other common satellite are hardcoded for example Starlink between known windows.

        If no records are available -1 will be provided instead

        Args:
            sat: `Satellite` object

        Returns:
            launch mass in kg
        """

        # TODO: Hardcode post 2023 Starlink?
        # hardcode STARLINK mini v2
        if (
            (sat.constellation == "STARLINK") and
            (sat.launch_date > datetime(2023, 7, 19)) and # type: ignore
            (sat.launch_date < datetime(2026, 2, 16)) # type: ignore
        ):
            return 740.0

        # lookup from UCS database
        if sat.norad_cat_id in self._norad_cat_ids:
            idx = np.where(self._norad_cat_ids == sat.norad_cat_id)[0][0]
            mass = float(str(self._launch_masses[idx]).replace(",", ""))
            return mass
        return -1

    def build_interpolators(self, sats: SatelliteSet) -> None:
        """compute the interpolating functions that provide a first-order estimate of satellite masses (where masses are unkown) based on the semi-major-axis and masses of known satellites

        Args:
            sats: Training `SatelliteSet` object
        """
        # get list of all sat categories
        cats = list(sats.get_all_categories().keys())

        self._interpolator_func["all"] = self.build_interpolator(sats) # type: ignore
        for cat in cats:
            training_sats = sats.filter_category(cat)
            self._interpolator_func[cat] = self.build_interpolator(training_sats) # type: ignore

    def build_interpolator(self, sats: SatelliteSet, *, _deg: int = 1):
        """compute a single interpolation function that provides a first-order estimate of satellite masses (where masses are unknown) based on the semi-major-axis and masses of known satellites

        Args:
            sats: Training `SatelliteSet` object
            cat: training group category
            _deg: polyfit degrees. Defaults to 1.
        """
        # define propagation time for calculation semi-major axis - interpolation is not sensitive to this
        t = ts.now()

        # match TLE dataset sats to UCS dataset
        launch_mass = []
        semi_major_axis = []
        for sat in sats.sats:
            mass = self.lookup_launch_mass(sat)
            if (mass != -1) and (not np.isnan(mass)):
                a: float = SGP4Propagation()._propagate(sat, t).a # type: ignore
                if np.isfinite(a):
                    launch_mass.append(mass)
                    semi_major_axis.append(a)

        # convert to np arrays
        launch_mass = np.array(launch_mass)
        semi_major_axis = np.array(semi_major_axis)

        # generate interpolation function
        coeffs = np.polyfit(semi_major_axis, launch_mass, _deg)
        f_mass = np.poly1d(coeffs)

        return f_mass

    def plot_interpolator(self, sats: SatelliteSet, degs: list[int] = [1, 2, 3]) -> None:
        """plot known mass data vs range of polyfit degree interpolation lines

        Args:
            sats: Training `SatelliteSet`
            degs: polyfit degrees. Defaults to [1, 2, 3].
        """
        if len(sats) < (max(degs) + 1):
            raise ValueError(f"Not enough sats provided in the `SatelliteSet` there must be at least `max(degs) + 1`. Only {len(sats)} sats provided.")

        # match TLE dataset sats to UCS dataset
        semi_major_axis = []
        launch_mass = []
        for sat in sats.sats:
            mass = self.lookup_launch_mass(sat)
            if (mass != -1) and (not np.isnan(mass)):
                a: float = SGP4Propagation()._propagate(sat, ts.now()).a # type: ignore
                if np.isfinite(a):
                    launch_mass.append(mass)
                    semi_major_axis.append(a)

        semi_major_axis = np.array(semi_major_axis)
        launch_mass = np.array(launch_mass)

        # generate polyfit lines
        f_semi_major_axis = np.linspace(semi_major_axis.min(), semi_major_axis.max(), 200)
        f_launch_masses = [self.build_interpolator(sats, _deg=deg)(f_semi_major_axis) for deg in degs]
        
        # plot graph
        import matplotlib.pyplot as plt
        plt.scatter(launch_mass, semi_major_axis, marker="x", label="known masses", color="red")
        for deg, f_launch_mass in zip(degs, f_launch_masses):
            plt.plot(f_launch_mass, f_semi_major_axis, label=f"polyfit (n={deg})")
        plt.xlabel("Launch Mass [kg]")
        plt.ylabel("Semi Major Axis [km]")
        plt.title(f"mass vs altitude polyfit for {len(sats)} sats")
        plt.legend()
        plt.show()
    
    def get_mass(self, sat: Satellite) -> float:
        """return the launch mass of the spacecraft either from existing datasets or from a locally trained first-order approximation model of other satellite altitudes, masses and categories.

        This must be called after `USCSizingDataset.build_interpolators()` when interpolations are needed.

        Args:
            sat: the mass of the sat to find

        Raises:
            UserWarning: `USCSizingDataset.build_intpolators()` hasn't been called yet.

        Returns:
            launch mass [kg]
        """
        
        # lookup mass from dataset
        mass = self.lookup_launch_mass(sat)
        if (mass != -1) and (not np.isnan(mass)):
            return mass
        
        # interpolate mass
        pos = SGP4Propagation()._propagate(sat, ts.now())
        semi_major_axis: float = pos.a # type: ignore
        if sat.category in list(self._interpolator_func.keys()):
            return self._interpolator_func[sat.category](semi_major_axis) # type: ignore
        
        if len(self._interpolator_func) == 0:
            raise UserWarning("Please ensure you've generated the interpolation plots using the `build_interpolators(sats)` method before calling this method")

        # catch all for missing categories
        return self._interpolator_func["all"](semi_major_axis) # type: ignore
        

UCSSizingDataset = _UCSSizingDataset("./data/UCS/UCS-Satellite-Database 5-1-2023.csv")