"""[Work In Progress] the coverage module provides a suite of tools for working with geographics grid points, optimised computation of satellite latitude, longitudes and altitudes throughout their orbit, a coverage engine to determine the coverage of satellites and constellations alongside plotting methods and utility functions"""

from .const import EARTH_RADIUS
from .models import SatelliteSet, Satellite
from .utility import accept_any_datetime, ProgressBar
from .propagation import wgs84

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from pyproj import Geod

from typing import Protocol, Optional, Callable, Tuple, Literal
import numpy as np
import datetime
import numba

DEFAULT_LAT_LON_TYPE = np.float64
DEFAULT_ALT_TYPE = np.float32
DEFAULT_STEP_TYPE = np.uint32
DEFAULT_VALUE_TYPE = np.float32


class BaseGrid(Protocol):
    """Base Class for latitude and longitude grids [deg]"""
    lats_deg: np.typing.NDArray
    lons_deg: np.typing.NDArray
    lats_rad: np.typing.NDArray
    lons_rad: np.typing.NDArray
    _resolution_msg: str
    _type: type

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} n={self.points} res={self._resolution_msg}>"

    def resolution(self) -> str:
        return self._resolution_msg

    @property
    def points(self) -> int:
        return len(self.lats_deg)

    def _compute_rads(self) -> None:
        self.lats_rad = np.radians(self.lats_deg, dtype=self._type)
        self.lons_rad = np.radians(self.lons_deg, dtype=self._type)

    def plot_grid(self) -> None:
        fig = plt.figure(figsize=(18, 9))
        ax = plt.axes(projection=ccrs.Robinson())
        ax.set_global()
        ax.coastlines()

        # Plot the points
        s = 0.005 if self.points > 100 else 50
        ax.scatter(self.lons_deg, self.lats_deg, s=s, color='red',
                   alpha=0.7, transform=ccrs.Geodetic())

        plt.title(f"Grid Points on Global Map ({self})")
        plt.show()


class LatLonGrid(BaseGrid):
    """othogal latitude and longitude global grid"""

    def __init__(self, lat_res_deg: float, lon_res_deg: float, *, dtype: type = DEFAULT_LAT_LON_TYPE) -> None:
        self._type = dtype
        self._resolution_msg = f"{lat_res_deg}° lat, {lon_res_deg}° lon"

        lats = np.arange(-90, 90 + lat_res_deg, lat_res_deg)
        lons = np.arange(-180, 180 + lon_res_deg, lon_res_deg)
        grid_lats, grid_lons = np.meshgrid(lats, lons)

        self.lats_deg = np.ascontiguousarray(
            grid_lats, dtype=self._type
        ).ravel()
        self.lons_deg = np.ascontiguousarray(
            grid_lons, dtype=self._type
        ).ravel()

        self._compute_rads()


class FibonacciSphereGrid(BaseGrid):
    """almost equal area global grid of points defined by resolution in km. 

    most efficient way to assess global coverage.

    see https://extremelearning.com.au/how-to-evenly-distribute-points-on-a-sphere-more-effectively-than-the-canonical-fibonacci-lattice/ for more details
    """

    def __init__(self, res_km: float, *, dtype: type = DEFAULT_LAT_LON_TYPE) -> None:
        self._type = dtype
        self._resolution_msg = f"{res_km}km"

        # calculate the number of points needed
        n = np.ceil((4 * np.pi * EARTH_RADIUS**2)/(res_km)**2)

        # generate fibonacci sphere coordinates
        sat_idx = np.arange(n)
        golden_ratio = (1 + 5**0.5)/2
        theta = 2 * np.pi * sat_idx / golden_ratio
        phi = np.arccos(1 - 2*(sat_idx)/n)

        # convert to spherical coordinates
        x, y, z = np.cos(theta) * np.sin(phi), np.sin(theta) * \
            np.sin(phi), np.cos(phi)

        # convert to lat/lon (degrees)
        self.lats_deg = np.degrees(np.arcsin(y), dtype=self._type)
        self.lons_deg = np.degrees(np.arctan2(z, x), dtype=self._type)

        self._compute_rads()


class SpotCheckGrid(BaseGrid):
    """grid for spot checking specific points.

    much faster coverage computations than global grids
    """

    def __init__(self, lats_deg: list[float], lons_deg: list[float], *, dtype: type = DEFAULT_LAT_LON_TYPE) -> None:
        self._type = dtype
        self._resolution_msg = "N/A"

        self.lats_deg = np.array(lats_deg, dtype=self._type)
        self.lons_deg = np.array(lons_deg, dtype=self._type)

        self._compute_rads()


class SatLatLon:
    """`SatLatLon` is an object that propagate `Satellite` locations for given times and provided methods for working with that data.
    """

    def __init__(
            self,
            start_time: datetime.datetime,
            total_duration: datetime.timedelta,
            step_duration: datetime.timedelta,
            sats: SatelliteSet,
            *,
            swath_radius_function: Optional[Callable[[
                Satellite, np.typing.NDArray], np.typing.NDArray]] = None,
            chunk_size: int = 10000,
            latlon_dtype: type = DEFAULT_LAT_LON_TYPE,
            alt_dtype: type = DEFAULT_ALT_TYPE,
            swath_dtype: type = DEFAULT_VALUE_TYPE,
            step_dtype: Optional[type] = None
    ) -> None:
        """generate a new `SatLatLon` object and propagate `Satellite` positions.

        parameter datatypes can be changed to tune propagation precision, SIMD vectorisation speed and memory usage. always ensure sufficient precision to accurately represent the data without introducing errors to the model.

        Sample `swath_radius_functions`:
            >>> lambda *_: 352 # constant swath
            >>> lambda sat, alt: alt * np.tan(np.radians(15)) # flat earth approximiation
            >>> lambda sat, alt: {"SENTINEL-2A": 145, "STARLINK-11628": 400}[sat.name] # dictionary lookup based on `Satellite` name

        Args:
            start_time: propagation period start time
            total_duration: propagation period total duration
            step_duration: propagation period step duration
            sats: `SatelliteSet` to propagate
            swath_radius_function: function to calculate swath radius (see examples above.). Defaults to None.
            chunk_size: chunk size for computation of satellite positions. Defaults to 10000.
            latlon_dtype: numpy dtype. Defaults to DEFAULT_LAT_LON_TYPE.
            alt_dtype: numpy dtype. Defaults to DEFAULT_ALT_TYPE.
            swath_dtype: numpy dtype. Defaults to DEFAULT_VALUE_TYPE.
            step_dtype: numpy dtype. Defaults to None.

        Raises:
            ValueError: raises error if step_dtype is too small to store all steps
        """
        # save parameters to object
        self.t0_dt: datetime.datetime = start_time
        self.t1_dt: datetime.date = start_time + total_duration
        self.dt_td: datetime.timedelta = step_duration
        self.dt_seconds = self.dt_td.total_seconds()

        self._latlon_type = latlon_dtype
        self._alt_type = alt_dtype
        self._swath_type = swath_dtype

        self.sats = sats
        self.num_sats = len(sats)

        # Compute the number of time steps
        self.num_steps = int((self.t1_dt - self.t0_dt) / self.dt_td) + 1

        # Validate step_type or use smallest suitable if step_type isn't provided
        bits_needed_for_steps = self.num_steps.bit_length()
        if step_dtype:
            if bits_needed_for_steps > np.iinfo(step_dtype).bits:
                raise ValueError(
                    f"invalid step type: {step_dtype} can only hold {np.iinfo(step_dtype).bits} bits but {bits_needed_for_steps} are needed for {self.num_steps} steps")
            self._step_type = step_dtype
        else:
            if bits_needed_for_steps <= 8:
                self._step_type = np.uint8
            elif bits_needed_for_steps <= 16:
                self._step_type = np.uint16
            elif bits_needed_for_steps <= 32:
                self._step_type = np.uint32
            else:
                self._step_type = np.uint64

        # setup outputs
        output_shape = (self.num_sats, self.num_steps)
        self.lats_deg = np.zeros(output_shape, dtype=self._latlon_type)
        self.lons_deg = np.zeros(output_shape, dtype=self._latlon_type)
        self.alt_km = np.zeros(output_shape, dtype=self._alt_type)
        self.swath_radius_km = np.zeros(output_shape, dtype=self._swath_type)

        # setup propagation times
        sat_times_dt = [self.t0_dt + self.dt_td *
                        i for i in range(self.num_steps)]
        sat_times_skyfield = accept_any_datetime(sat_times_dt)
        sat_times_skyfield_chunks = [
            sat_times_skyfield[i:i+chunk_size]
            for i in range(0, len(sat_times_skyfield), chunk_size)
        ]

        bar = ProgressBar(len(sats) * self.num_steps)

        # for each sat
        for sat_pos_idx, sat in enumerate(sats.sats):

            # chunk for times
            for sat_idx, start in enumerate(range(0, self.num_steps, chunk_size)):
                bar.update(sat_pos_idx * self.num_steps + start)

                end = min(start + chunk_size, self.num_steps)

                sat_pos = sat._sat.at(sat_times_skyfield_chunks[sat_idx])
                geo_pos = wgs84.geographic_position_of(sat_pos)

                self.lats_deg[sat_pos_idx,
                              start:end] = geo_pos.latitude.degrees
                self.lons_deg[sat_pos_idx,
                              start:end] = geo_pos.longitude.degrees
                self.alt_km[sat_pos_idx, start:end] = geo_pos.elevation.km

                if swath_radius_function:
                    self.swath_radius_km[sat_pos_idx, start:end] = swath_radius_function(
                        sat, self.alt_km[sat_pos_idx, start:end]
                    )

        # create rad copy
        self.lats_rad = np.radians(self.lats_deg, dtype=self._latlon_type)
        self.lons_rad = np.radians(self.lons_deg, dtype=self._latlon_type)

        bar.update(bar.tasks)

    def step_to_dt(self, step: float | int) -> datetime.datetime:
        return self.t0_dt + self.dt_td * step

    def dt_to_step(self, dt: datetime.datetime) -> float:
        return (dt - self.t0_dt) / self.dt_td

    @property
    def times(self):
        return self.step_to_dt(np.arange(self.num_steps))  # type: ignore

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} sats={self.num_sats} steps={self.num_steps} datapoints={self.num_sats*self.num_steps} t0={self.t0_dt} t1={self.t1_dt} td={self.dt_td} latlontype={self._latlon_type} steptype={self._step_type}>"

    def plot_coverage(self, *, force_show: bool = False, title: Optional[str] = None, show: bool = True):
        """plot boundary of swath coverage and ground track on a global map for each satellite.

        if more than `THRESHOLD_DATAPOINTS` datapoints (num_sats x num_steps) are provided this function will print a message rather than plotting a graph due to very slow (>5 minute) plotting time. This behaviour can be overidden by setting `force_show=True`.

        Args:
            force_show: ignore `THRESHOLD_DATAPOINTS` and always plot. Defaults to False.
            title: plot `title` if provided. Defaults to None.
            show: show plt automatically or return `plt` to allow use to customise and show it themselves. Defaults to True.
        """
        THRESHOLD_DATAPOINTS = 100000
        if (self.num_sats * self.num_steps > THRESHOLD_DATAPOINTS) and (not force_show):
            print(
                f"More than {THRESHOLD_DATAPOINTS} datapoints. It is not recommended to generate coverage plots with more than {THRESHOLD_DATAPOINTS} datapoint, you have {self.num_sats * self.num_steps} datepoints. This can be overidden by setting `force_show=True`.")
            return plt

        # Earth model for geodesics
        geod = Geod(ellps="WGS84")

        # Plot
        fig = plt.figure(figsize=(18, 9))
        ax = plt.axes(projection=ccrs.Robinson())
        ax.set_global()
        ax.coastlines()

        for sat, sat_lats_deg, sat_lons_deg, sat_swath_radius in zip(self.sats.sats, self.lats_deg, self.lons_deg, self.swath_radius_km):
            line, = ax.plot(sat_lons_deg, sat_lats_deg,
                            transform=ccrs.Geodetic(), linewidth=0.8, label=sat.name)
            colour = line.get_color()

            # compute ground track bearings
            bearings = geod.inv(sat_lons_deg[:-1], sat_lats_deg[:-1],
                                sat_lons_deg[1:], sat_lats_deg[1:])[0]

            # pad to same length
            bearings = np.append(bearings, bearings[-1])

            # left and right swath bearings
            left_bearings = bearings + 90
            right_bearings = bearings - 90

            # km to m
            dist = sat_swath_radius * 1000.0

            left_lons, left_lats, _ = geod.fwd(
                sat_lons_deg, sat_lats_deg, left_bearings, dist)
            right_lons, right_lats, _ = geod.fwd(
                sat_lons_deg, sat_lats_deg, right_bearings, dist)

            # plot boundaries
            ax.plot(left_lons, left_lats,  transform=ccrs.Geodetic(),
                    linewidth=0.5, color=colour, alpha=0.5)
            ax.plot(right_lons, right_lats, transform=ccrs.Geodetic(),
                    linewidth=0.5, color=colour, alpha=0.5)

        if self.num_sats < 5:
            ax.legend()
        if title:
            plt.title(title)
        if show:
            plt.show()
            return plt
        else:
            return plt


def remove_outliers_by_lat(arr, bin_width_deg: float, lower_percentile: float, upper_percentile: float, grid: BaseGrid):
    """remove outliers from the provided `value` by putting into latitude bins of `bin_width_deg` and then replacing data that falls outside of `lower_percentile`% and `upper_percentile`% with the median within each bin.

    Args:
        value: 2D np.array of size (num sats, num grid points)
        bin_width_deg: bin width, deg
        lower_percentile: lower percentile %
        upper_percentile: upper percentile %

    Raises:
        ValueError: not enough data points in a bin

    Returns:
        copy of `value` without outliers
    """
    cleaned = arr.copy()

    lat_bins = np.arange(-90, 90+bin_width_deg, bin_width_deg)

    for b in lat_bins:
        mask = (grid.lats_deg > b) & (grid.lons_deg < b + bin_width_deg)
        if np.sum(mask) < 10:
            raise ValueError(
                f"too few points to compute percentiles reliably: n={np.sum(mask)}")

        vals = arr[:, mask]
        lower_percentiles = np.percentile(
            vals, lower_percentile, axis=1, keepdims=True)
        upper_percentiles = np.percentile(
            vals, upper_percentile, axis=1, keepdims=True)
        median = np.median(vals, axis=1, keepdims=True)

        cleaned[:, mask] = np.where(
            (vals < lower_percentiles) | (vals > upper_percentiles),
            median,
            vals
        )
    return cleaned


@numba.vectorize([numba.float64(numba.float64, numba.float64, numba.float64, numba.float64)], target="cpu", cache=True)
def _great_circle_distance(lat1, lon1, lat2, lon2):
    """computes the great-circle distance in kilometres.

    uses the spherical law of cosines (accurate when distance is > 1m) otherwise you haversine formula

    typical error vs WGS-64 Ellipsoid is 0.1%-0.5%

    Args:
        lat1: latitude [rad]
        lon1: longitude [rad]
        lat2: latitude [rad]
        lon2: longitude [rad]

    Returns:
        great-circle distance [km]
    """
    dlon = lon2 - lon1

    return EARTH_RADIUS * np.acos(
        np.sin(lat1) * np.sin(lat2) + np.cos(lat1) *
        np.cos(lat2) * np.cos(dlon)
    )


@numba.njit(cache=True)
def _pass_and_coverage_logic(
    is_covered,
    step_num,
    sat_coverage,
    sat_passes,
    sat_pass_start_step,
    sat_pass_end_step,
    sat_first_central_pass_step,
    sat_last_central_pass_step,
    sat_passes_duration_steps,
    MIN_SEPARATION_STEPS,
    STEP_TYPE_MAX,
    MIN_PASS_STEPS
):
    """brains of the operation.

    processing the data coverage to extract the following data points for further analysis. these are all mutated in place:
    - `sat_coverage`, the number of times a grid points is within radius
    - `sat_passes`, the number of times a grid point has a pass (see PASS logic below)
    - `sat_first_central_pass_step`, the central step of the first pass
    - `sat_last_central_pass_step`, the central step of the last pass

    passes are defined by:
    - `MIN_SEPARATION_STEPS`, the minimum steps between subsequent passes (this can be used to remove noise)
    - `MIN_PASS_STEPS`, the minimum number of steps to be considered a pass

    both of these are VERY sensitive to changes in step duration and grid size. duplicate points at the same time are ignored.

    Args:
        is_covered: 1d numpy array
        sat_time: scalar
        sat_coverage: 1d numpy array
        sat_passes: 1d numpy array
        sat_pass_start_time: 1d numpy array
        sat_pass_end_time: 1d numpy array
        sat_first_central_pass_step: 1d numpy array
        sat_last_central_pass_step: 1d numpy array
    """
    # precompute with vectorisation to optimise for most common path
    # not (not covered and time between passes is less than MIN_SEPARATION_STEPS)
    mask = ~ ((~ is_covered) & (
        (step_num - sat_pass_end_step) <= MIN_SEPARATION_STEPS))

    # for each grid point
    for idx in range(len(is_covered)):
        if mask[idx]:
            # is grid point covered by the sat swath radius
            if is_covered[idx]:
                # is this the first time for this pass
                if sat_pass_end_step[idx] == STEP_TYPE_MAX:
                    sat_pass_start_step[idx] = step_num
                sat_pass_end_step[idx] = step_num
            else:
                sat_coverage[idx] += 1
                # is the pass duration is greater than MIN_PASS_STEPS
                if (sat_pass_end_step[idx] - sat_pass_start_step[idx]) >= MIN_PASS_STEPS:
                    sat_last_central_pass_step[idx] = (
                        sat_pass_start_step[idx] + sat_pass_end_step[idx]) / 2
                    sat_passes_duration_steps[idx] += sat_pass_end_step[idx] - \
                        sat_pass_start_step[idx]
                    # is this the first pass recorded
                    if sat_passes[idx] == 0:
                        sat_first_central_pass_step[idx] = sat_last_central_pass_step[idx]
                    sat_passes[idx] += 1
                sat_pass_end_step[idx] = STEP_TYPE_MAX


@numba.njit(parallel=True)
def _coverage_calculations(
    sats_lats_rad,
    sats_lons_rad,
    sats_swath_radii,
    grid_lats_rad,
    grid_lons_rad,
    consider_passes,
    MIN_SEPARATION_STEPS,
    MIN_PASS_STEPS,
    STEP_TYPE_MAX,
    STEP_TYPE_MIX,
    STEP_TYPE: type,
    CENTRAL_PASS_STEP_TYPE: type,
    COVERAGE_PASSES_TYPE: type,
):
    # setup output values
    output_shape = (sats_lats_rad.shape[0], grid_lons_rad.shape[0])
    sats_coverage = np.zeros(output_shape, dtype=COVERAGE_PASSES_TYPE)
    """number of intersections"""
    sats_passes = np.zeros(output_shape, dtype=COVERAGE_PASSES_TYPE)
    """number of passes, considering pass logic"""
    sats_pass_start_step = np.full(
        output_shape, STEP_TYPE_MIX, dtype=STEP_TYPE)
    """start step of last pass"""
    sats_pass_end_step = np.full(
        output_shape, STEP_TYPE_MAX, dtype=STEP_TYPE)
    """end step of last pass"""
    sats_first_central_pass_step = np.zeros(
        output_shape, dtype=CENTRAL_PASS_STEP_TYPE)
    """central step number [float] of first pass"""
    sats_last_central_pass_step = np.zeros(
        output_shape, dtype=CENTRAL_PASS_STEP_TYPE)
    """central step number [float] of last pass"""
    sats_passes_duration_steps = np.zeros(output_shape, dtype=STEP_TYPE)
    """number of steps from all passes"""

    # for each sat
    for sat_idx in numba.prange(sats_lats_rad.shape[0]):
        sat_lats_rad = sats_lats_rad[sat_idx]
        sat_lons_rad = sats_lons_rad[sat_idx]
        sat_swath_radii = sats_swath_radii[sat_idx]

        # setup ascending/descending pass logic
        sat_lats_rad = np.ascontiguousarray(sat_lats_rad)
        lat_diffs = np.diff(sat_lats_rad)
        lat_diffs = np.append(lat_diffs, 0)  # prevent out-of-bounds error
        consider_pass = consider_passes[sat_idx]
        skip = (
            (consider_pass == "ascending") & (lat_diffs <= 0)
        ) | (
            (consider_pass == "descending") & (lat_diffs >= 0)
        )

        # for each sat position
        for step_num in range(sats_lats_rad.shape[1]):

            if skip[step_num]:
                continue

            sat_lat_rad = sat_lats_rad[step_num]
            sat_lon_rad = sat_lons_rad[step_num]
            sat_swath_radius = sat_swath_radii[step_num]

            # performance optimisations

            # bounding box calculations
            central_angle = sat_swath_radius / EARTH_RADIUS

            # latitude mask
            lat_mask = np.abs(grid_lats_rad - sat_lat_rad) <= central_angle

            # end of performance optimisations

            # Great circle distance
            dist = _great_circle_distance(
                grid_lats_rad[lat_mask], grid_lons_rad[lat_mask], sat_lat_rad, sat_lon_rad)

            # check if grid point is within radius (masked only)
            within_swath_mask = dist <= sat_swath_radius

            # if grid point is within radius (all points)
            full_within_swatch_mask = np.zeros(
                grid_lats_rad.shape, dtype=np.bool)
            full_within_swatch_mask[lat_mask] = within_swath_mask

            _pass_and_coverage_logic(
                is_covered=full_within_swatch_mask,
                step_num=step_num,
                sat_coverage=sats_coverage[sat_idx],
                sat_passes=sats_passes[sat_idx],
                sat_pass_start_step=sats_pass_start_step[sat_idx],
                sat_pass_end_step=sats_pass_end_step[sat_idx],
                sat_first_central_pass_step=sats_first_central_pass_step[sat_idx],
                sat_last_central_pass_step=sats_last_central_pass_step[sat_idx],
                sat_passes_duration_steps=sats_passes_duration_steps[sat_idx],
                MIN_PASS_STEPS=MIN_PASS_STEPS,
                MIN_SEPARATION_STEPS=MIN_SEPARATION_STEPS,
                STEP_TYPE_MAX=STEP_TYPE_MAX
            )

    return (
        sats_coverage,
        sats_passes,
        sats_first_central_pass_step,
        sats_last_central_pass_step,
        sats_passes_duration_steps
    )


class Coverage:
    """`Coverage` class compute the coverage (and passes) of the `SatLatLon` object on the `BaseGrid` object and provides methods for working with and plotting the output"""

    def __init__(
        self,
        grid: BaseGrid,
        satlatlon: SatLatLon,
        *,
        max_threads: int = 4,
        consider_passes: Optional[
            Tuple[Literal["both", "ascending", "descending", 1], ...]] = None,
    ) -> None:
        """compute the coverage of `SatLatLon` on `BaseGrid`.

        this is an expensive function that may take multiple hours to complete, even with various optimisation strategies including: vectorisation, JIT complication, boundary boxes and more

        Args:
            grid: `BaseGrid` or child object containing the grid to be used
            satlatlon: `SatLatLon` object with satellites latitudes, longitudes and swath radii
            max_threads: the maximum number of threads to use. Defaults to 4.
            consider_passes: tuple (of same length as num sats) defining whether each sat should consider "ascending", "descending" or "both" passes. Defaults to None, equal to "both" if not provided.
        """
        self.grid = grid
        self.satlatlon = satlatlon

        if consider_passes is None:
            consider_passes = ("both",) * self.satlatlon.num_sats
        if len(consider_passes) != self.satlatlon.num_sats:
            raise ValueError(
                f"mismatch between consider_passes length and number of sats: {len(consider_passes)=} and {self.satlatlon.num_sats=}"
            )

        # define data types
        self._step_type = satlatlon._step_type
        STEP_TYPE = self._step_type
        STEP_TYPE_MAX = np.iinfo(STEP_TYPE).max
        STEP_TYPE_MIN = np.iinfo(STEP_TYPE).min
        CENTRAL_PASS_STEP_TYPE = np.float32
        COVERAGE_PASSES_TYPE = STEP_TYPE

        # define pass logic
        MIN_SEPARATION_STEPS = STEP_TYPE(10)
        """minimum number of steps between passes"""
        MIN_PASS_STEPS = STEP_TYPE(1)
        """minimum steps to be considered a pass.
        
        care should be taken when choosing this parameter. It dt is small relative to pass duration values above 1 will reduce noise and slightly decrease coverage. large values should be avoided."""

        numba.set_num_threads(max_threads)

        # TODO: Add progress bar
        self.coverage, self.passes, self.first_central_pass_step, self.last_central_pass_step, self.pass_duration_steps = _coverage_calculations(
            sats_lats_rad=satlatlon.lats_rad,
            sats_lons_rad=satlatlon.lons_rad,
            sats_swath_radii=satlatlon.swath_radius_km,
            grid_lats_rad=grid.lats_rad,
            grid_lons_rad=grid.lons_rad,
            consider_passes=consider_passes,
            MIN_SEPARATION_STEPS=MIN_SEPARATION_STEPS,
            MIN_PASS_STEPS=MIN_PASS_STEPS,
            STEP_TYPE_MAX=STEP_TYPE_MAX,
            STEP_TYPE_MIX=STEP_TYPE_MIN,
            STEP_TYPE=STEP_TYPE,
            CENTRAL_PASS_STEP_TYPE=CENTRAL_PASS_STEP_TYPE,
            COVERAGE_PASSES_TYPE=COVERAGE_PASSES_TYPE,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} grid={self.grid} satlatlon={self.satlatlon}>"

    @property
    def revisit_frequency(self):
        return np.where(np.isnan(self.revisit_period), 0, 1/self.revisit_period)

    @property
    def revisit_period(self):
        """revisit period [seconds] per sat per grid point"""
        with np.errstate(invalid="ignore"):
            return np.where(self.passes > 1, ((self.last_central_pass_step - self.first_central_pass_step) * self.satlatlon.dt_seconds) / self.passes, np.nan)

    @property
    def mean_revisit_days(self):
        return self.revisit_period / (60 * 60 * 24)

    @property
    def constellation_revisit_frequency(self):
        return np.nansum(self.revisit_frequency, axis=0)

    @property
    def constellation_revisit_period(self):
        with np.errstate(divide="ignore"):
            return np.where(self.constellation_revisit_frequency != 0, 1 / self.constellation_revisit_frequency, np.nan)

    @property
    def constellation_mean_revisit_days(self):
        return self.constellation_revisit_period / (60 * 60 * 24)

    @property
    def constellation_coverage(self):
        return np.nansum(self.coverage, axis=0)

    @property
    def total_pass_duration(self):
        return self.pass_duration_steps * self.satlatlon.dt_seconds

    @property
    def mean_pass_duration(self):
        return np.where(self.passes > 0, self.total_pass_duration / self.passes, 0)

    def plot_coverage(self, sat_idx: int = -1, *, title: Optional[str] = None, show: bool = True, vmin: Optional[float] = None, vmax: Optional[float] = None):
        """plot global coverage (number of times each grid point each grid point has been within `Satellite` swath), ignoring overlap for each gridpoint.

        if `sat_idx` is provied this will pull data from the respective satellite index otherwise if `sat_idx` is -1 or not provided the entire constellation will be used.

        Args:
            sat_idx: index of `Satellite`. Defaults to -1.
            title: plot `title` if provided. Defaults to None.
            show: show plt automatically or return `plt` to allow use to customise and show it themselves. Defaults to True.
        """
        if sat_idx == -1:
            coverage = self.constellation_coverage
        else:
            coverage = self.coverage[sat_idx]

        fig = plt.figure(figsize=(14, 6))
        ax = plt.axes(projection=ccrs.Robinson())
        ax.set_global()
        ax.coastlines()
        sc = ax.scatter(self.grid.lons_deg, self.grid.lats_deg, c=coverage,
                        s=10, cmap="viridis", alpha=0.7, transform=ccrs.Geodetic(), vmin=vmin, vmax=vmax)
        plt.colorbar(sc, orientation="vertical",
                     label="Number of satellites covering each point")
        if title:
            plt.title(title)
        if show:
            plt.show()
            return plt
        else:
            return plt

    def plot_mean_revisit_days(self, sat_idx: int = -1, *, title: Optional[str] = None, show: bool = True, vmin: Optional[float] = None, vmax: Optional[float] = None):
        """plot the mean revisit days on a global map for each grid point.

        if `sat_idx` is provied this will pull data from the respective satellite index otherwise if `sat_idx` is -1 or not provided the entire constellation will be used.

        Args:
            sat_idx: index of `Satellite`. Defaults to -1.
            title: plot `title` if provided. Defaults to None.
            show: show plt automatically or return `plt` to allow use to customise and show it themselves. Defaults to True.
        """
        # TODO: Add datacleaning?
        if sat_idx == -1:
            mean_revisit_days = self.constellation_mean_revisit_days
        else:
            mean_revisit_days = self.mean_revisit_days[sat_idx]

        cmap = plt.cm.viridis  # type: ignore
        cmap = cmap.copy()
        cmap.set_over("yellow")

        fig = plt.figure(figsize=(10, 5))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
        ax.set_global()  # type: ignore
        ax.coastlines()  # type: ignore

        s = 10 if self.grid.points > 100 else 50
        sc = ax.scatter(
            self.grid.lons_deg,
            self.grid.lats_deg,
            c=mean_revisit_days,
            cmap=cmap,
            s=5,
            vmin=vmin,
            vmax=vmax,
            alpha=0.7,
            transform=ccrs.PlateCarree(),
        )
        cb = plt.colorbar(sc, orientation="vertical",
                          label="Mean revisit (days)")
        cb.ax.tick_params(labelsize=10)
        if title:
            plt.title(title)
        if show:
            plt.show()
            return plt
        else:
            return plt

    def plot_mean_revisit_time_vs_latitude(
            self,
            sat_idx: int = -1,
            *,
            lat_min_deg: float = -90,
            lat_max_deg: float = 90,
            bin_width_deg: float = 0.2,
            trim_lower_percentile: float = 0,
            trim_upper_percentile: float = 100,
            title: Optional[str] = None,
            show: bool = True
    ):
        """plot the mean revisit time (min, max, mean) against latitude in latitude bins.

        if `sat_idx` is provied this will pull data from the respective satellite index otherwise if `sat_idx` is -1 or not provided the entire constellation will be used.

        if `trim_lower_percentile` or `trim_upper_percentile` are provided they will remove outliers outside of these percentages.

        Args:
            sat_idx: index of `Satellite`. Defaults to -1.
            lat_min_deg: minimum latitude [deg]. Defaults to -90.
            lat_max_deg: maximum latitude [deg]. Defaults to 90.
            bin_width_deg: bin width [deg]. Defaults to 0.2.
            trim_lower_percentile: trim lower percentile percentage. Defaults to 0.
            trim_upper_percentile: trim upper percentile percentage. Defaults to 100.
            title: plot `title` if provided. Defaults to None.
            show: show plt automatically or return `plt` to allow use to customise and show it themselves. Defaults to True.
        """
        if sat_idx == -1:
            mean_revisit_days = self.constellation_mean_revisit_days
        else:
            mean_revisit_days = self.mean_revisit_days[sat_idx]

        # Define lat bins
        lat_bins = np.arange(lat_min_deg, lat_max_deg +
                             bin_width_deg, bin_width_deg)
        lat_centers = (lat_bins[:-1] + lat_bins[1:]) / 2
        num_bins = len(lat_bins) - 1

        # preallocate arrays
        mean_revisit_by_lat = np.full(
            num_bins, np.nan, dtype=self.satlatlon._latlon_type)
        min_revisit_by_lat = np.full(
            num_bins, np.nan, dtype=self.satlatlon._latlon_type)
        max_revisit_by_lat = np.full(
            num_bins, np.nan, dtype=self.satlatlon._latlon_type)

        # remove outliers
        for sat_idx in range(num_bins):
            lat_mask = (self.grid.lats_deg >= lat_bins[sat_idx]) & (
                self.grid.lats_deg < lat_bins[sat_idx+1])

            if np.any(lat_mask) and not np.all(np.isnan(mean_revisit_days[lat_mask])):
                vals = mean_revisit_days[lat_mask]

                # remove outliers by percentile
                vals_nonan = vals[~np.isnan(vals)]
                if len(vals_nonan) == 0:
                    continue  # skip if no valid values

                low, high = np.percentile(
                    vals_nonan, [trim_lower_percentile, trim_upper_percentile])
                vals_filtered = vals_nonan[(
                    vals_nonan >= low) & (vals_nonan <= high)]

                if len(vals_filtered) == 0:
                    continue  # skip if filtering removed all values

                # Compute stats on filtered values
                mean_revisit_by_lat[sat_idx] = np.nanmean(vals_filtered)
                min_revisit_by_lat[sat_idx] = np.nanmin(vals_filtered)
                max_revisit_by_lat[sat_idx] = np.nanmax(vals_filtered)

        # plot
        plt.figure()
        plt.plot(lat_centers, mean_revisit_by_lat, label="Mean")
        plt.plot(lat_centers, min_revisit_by_lat, label="Minimum")
        plt.plot(lat_centers, max_revisit_by_lat, label="Maximum")
        plt.xlabel("Latitude, deg")
        plt.ylabel("Revisit time, days")
        plt.ylim(0, None)
        plt.xlim(lat_min_deg, lat_max_deg)
        plt.grid()
        plt.legend()
        if title:
            plt.title(title)
        if show:
            plt.show()
            return plt
        else:
            return plt

    def plot_mean_revisit_days_reverse_CDF(self, sat_idx: int = -1, *, title: Optional[str] = None, show: bool = True):
        """plot mean revisit days reverse CDF (mean revisit days vs cumulative pass coveraged).

        if `sat_idx` is provied this will pull data from the respective satellite index otherwise if `sat_idx` is -1 or not provided the entire constellation will be used.

        please note this makes no attempt to scale grid area for grid's with non-uniform area. use `FibonacciGrid` to generate this plot with near uniform area.

        Args:
            sat_idx: index of `Satellite`. Defaults to -1.
            title: plot `title` if provided. Defaults to None.
            show: show plt automatically or return `plt` to allow use to customise and show it themselves. Defaults to True.
        """
        if sat_idx == -1:
            mean_revisit_days = self.constellation_mean_revisit_days
        else:
            mean_revisit_days = self.mean_revisit_days[sat_idx]
        # TODO: Ensure this actually implements coverage

        # Sort array from small → large
        sorted_vals = np.sort(mean_revisit_days)

        # Compute reverse cumulative percentages
        n = len(sorted_vals)
        percent = 1 - np.arange(n) / (n - 1)  # goes from 1 → 0
        percent *= 100  # convert to %

        # Plot
        plt.plot(sorted_vals, percent)
        plt.xlabel("Mean revisit, days")
        plt.ylabel("Percent of values ≥ X")
        plt.xlim(0, None)
        plt.ylim(0, None)
        if title:
            plt.title(title)
        plt.grid()
        if show:
            plt.show()
            return plt
        else:
            return plt
