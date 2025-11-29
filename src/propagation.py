from skyfield.api import Time, wgs84, utc
from skyfield.positionlib import ICRF
from skyfield.elementslib import osculating_elements_of
from skyfield.framelib import itrs
from skyfield.toposlib import GeographicPosition

from .models import Satellite, SatelliteSet, ts
from .const import EARTH_RADIUS
from .utility import ACCEPTABLE_TIME_TYPES, accept_any_datetime

import math
import datetime

import numpy as np
from numpy.typing import NDArray

# TODO: Add methods for quickly and easily plotting ground tracks and other data
# TODO: Implement SatellitePositions
# TODO: Implement propagation techniques
# TODO: Test everything
# TODO: Plug into the satellite download system
# TODO: Add support for oscillating parameters (inclinations, etc)


class SGP4PropagationError(Exception):
    """raised when SGP4 returns math.nan (invalid propagation)"""
    pass


class OrbitalPosition:
    """Represents a satellite at an instantaneous time.

    Do not create this function directly.

    This is generated from the propagation objects"""

    def __init__(self, sat: Satellite, position: ICRF | None, time: ACCEPTABLE_TIME_TYPES) -> None:
        self.sat = sat
        self.gcrs_position = position
        self.time = accept_any_datetime(time)

        # Alternate reference frames
        self.geo = self._Geocentric(self)
        self.topo = self._Topocentric(self)

        # Osculating elements
        self._a = None
        self._e = None
        self._i = None
        self._Omega = None
        self._omega = None
        self._M = None
        self._n = None

    @property
    def a(self) -> float:
        """semi-major_axis [km]"""
        if not self._a:
            self._calculate_osculating_elements()
        return self._a  # type: ignore

    @property
    def e(self) -> float:
        """eccentricity"""
        if not self._e:
            self._calculate_osculating_elements()
        return self._e  # type: ignore

    @property
    def i(self) -> float:
        """inclination [rads]"""
        if not self._i:
            self._calculate_osculating_elements()
        return self._i  # type: ignore

    @property
    def Omega(self) -> float:
        """longitude of the ascending node (RAAN) [rads]"""
        if not self._Omega:
            self._calculate_osculating_elements()
        return self._Omega  # type: ignore

    @property
    def omega(self) -> float:
        """argument of periapsis [rads]"""
        if not self._omega:
            self._calculate_osculating_elements()
        return self._omega  # type: ignore

    @property
    def M(self) -> float:
        """mean anomaly [rads]"""
        if not self._M:
            self._calculate_osculating_elements()
        return self._M  # type: ignore

    @property
    def n(self) -> float:
        """mean motion [rads/day]"""
        if not self._n:
            self._calculate_osculating_elements()
        return self._n  # type: ignore

    @property
    def perigee(self) -> float:
        """perigee altitude [km]"""
        return self.a * (1 - self.e) - 6371.0  # Earth radius approx

    @property
    def apogee(self) -> float:
        """apogee altitude [km]"""
        return self.a * (1 + self.e) - 6371.0  # Earth radius approx

    @property
    def max_flux_debris_density(self) -> float:
        """estimate the maximum debris flux [#/m²/year] for this orbital position based on its orbital parameters estimated from TLE using the SPG4 model"""
        from .debris import debrisFluxDataset
        return debrisFluxDataset.estimate_max_flux(self)

    @property
    def avg_flux_debris_density(self) -> float:
        """estimate the average debris flux [#/m²/year] for this orbital position based on its orbital parameters estimated from TLE using the SPG4 model"""
        from .debris import debrisFluxDataset
        return debrisFluxDataset.estimate_average_flux(self)

    semi_major_axis = a
    eccentricity = e
    inclination = i
    RAAN = Omega
    longitude_of_the_ascending_node = Omega
    argument_of_periapsis = omega
    mean_anomaly = M
    mean_motion_per_day = n

    def is_above_horizon(self, obs: GeographicPosition) -> bool:
        self.topo.altitude_azimuth_and_distance(obs)
        return self.topo.alt > 0

    def is_geo(self) -> bool:
        GEO_ALT = 35786
        return (
            self.geo.alt < GEO_ALT + 500
            and self.geo.alt > GEO_ALT - 500
            and self.sat.eccentricity < 0.05
            and abs(self.sat.inclination) < 0.05
        )

    def is_leo(self) -> bool:
        return (
            self.geo.alt < 2000
            and self.sat.eccentricity < 0.05
        )

    def is_meo(self) -> bool:
        GEO_ALT = 35786
        return (
            self.geo.alt >= 2000
            and self.geo.alt < GEO_ALT - 500
            and self.sat.eccentricity < 0.05
        )

    def is_heo(self) -> bool:
        return (
            self.sat.eccentricity >= 0.5
        )

    def _calculate_osculating_elements(self) -> None:
        """calculate osculating elements from existing GCRS position"""
        if not self.gcrs_position:
            return
        elements = osculating_elements_of(self.gcrs_position)
        self._a = elements.semi_major_axis.km  # type: ignore
        self._e = elements.eccentricity
        self._i = elements.inclination.radians  # type: ignore
        self._Omega = elements.longitude_of_ascending_node.radians  # type: ignore
        self._omega = elements.argument_of_periapsis.radians  # type: ignore
        self._M = elements.mean_anomaly.radians  # type: ignore
        self._n = elements.mean_motion_per_day.radians  # type: ignore

    def oscillating_elements_to_dict(self) -> dict:
        return {
            "semi major axis [km]": self.semi_major_axis,
            "eccentricity": self.eccentricity,
            "inclinations [rads]": self.inclination,
            "longitude of ascending node [rads]": self.longitude_of_the_ascending_node,
            "argument of periapsis [rads]": self.argument_of_periapsis,
            "mean anomaly [rads]": self.mean_anomaly,
            "mean motion [/day]": self.mean_motion_per_day
        }

    def to_dict(self) -> dict:
        out = self.sat.to_dict()
        out["orbital position"] = {
            "time": self.time.utc_iso(),
            "oscillating elements": self.oscillating_elements_to_dict(),
            "geo": self.geo.to_dict()
        }
        return out

    def info(self) -> str:
        from pprint import pformat
        return pformat(self.to_dict())

    class _Geocentric:
        """ITRS Geocentric (rotation Earth Fixed) (lat vs lon)"""
        # TODO: Cache calculations and make invidual values properties to assist with charting

        def __init__(self, parent) -> None:
            self.parent = parent

            # parameters
            self._x = None
            self._y = None
            self._z = None
            self._x_v = None
            self._y_v = None
            self._z_v = None
            self._lat = None
            self._lon = None
            self._alt = None

        @property
        def x(self) -> float:
            """cartesian position [km]"""
            if not self._x:
                self.cartesian_position_and_velocity()
            return self._x  # type: ignore

        @property
        def y(self) -> float:
            """cartesian position [km]"""
            if not self._y:
                self.cartesian_position_and_velocity()
            return self._y  # type: ignore

        @property
        def z(self) -> float:
            """cartesian position [km]"""
            if not self._z:
                self.cartesian_position_and_velocity()
            return self._z  # type: ignore

        @property
        def x_v(self) -> float:
            """cartesian position [km/s]"""
            if not self._x_v:
                self.cartesian_position_and_velocity()
            return self._x_v  # type: ignore

        @property
        def y_v(self) -> float:
            """cartesian position [km/s]"""
            if not self._y_v:
                self.cartesian_position_and_velocity()
            return self._y_v  # type: ignore

        @property
        def z_v(self) -> float:
            """cartesian position [km/s]"""
            if not self._z_v:
                self.cartesian_position_and_velocity()
            return self._z_v  # type: ignore

        @property
        def lat(self) -> float:
            """latitude [deg]"""
            if not self._lat:
                self.latitude_longitude_and_altitude()
            return self._lat  # type: ignore

        @property
        def lon(self) -> float:
            """longitude [deg]"""
            if not self._lon:
                self.latitude_longitude_and_altitude()
            return self._lon  # type: ignore

        @property
        def alt(self) -> float:
            """altitude [km]"""
            if not self._alt:
                self.latitude_longitude_and_altitude()
            return self._alt  # type: ignore

        def cartesian_position_and_velocity(self) -> tuple[float, float, float, float, float, float]:
            """returns cartesian coordinates [km] and velocity [km/s]"""
            if not self.parent.gcrs_position:
                return math.nan, math.nan, math.nan, math.nan, math.nan, math.nan

            p, v = self.parent.gcrs_position.frame_xyz_and_velocity(itrs)
            self._x, self._y, self._z = p.km
            self._x_v, self._y_v, self._z_v = v.km_per_s
            return self._x, self._y, self._z, self._x_v, self._y_v, self._z_v

        def latitude_longitude_and_altitude(self) -> tuple[float, float, float]:
            """returns latitude [degrees], longitude [degrees] and altitude [km]"""
            if not self.parent.gcrs_position:
                return math.nan, math.nan, math.nan

            geo_pos = wgs84.geographic_position_of(self.parent.gcrs_position)
            self._lat = geo_pos.latitude.degrees
            self._lon = geo_pos.longitude.degrees
            self._alt = geo_pos.elevation.km

            return self._lat, self._lon, self._alt  # type: ignore

        def swath_ground_radius(self, off_nadir_half_angle: float) -> float:
            """return the ground radius (assuming a spherical Earth) of the satellite with a given off nadir half angle at it's current altitude. If the half angle points beyond the horizon this will return the ground radius to the horizon instead.

            Args:
                off_nadir_half_angle: [deg] angle from the nadir

            Returns:
                ground radius [km]
            """
            import numpy as np

            theta_rad = np.radians(off_nadir_half_angle)
            R_E = EARTH_RADIUS
            h = self.alt

            # calculate angle and radius of horizon
            theta_horizon = np.asin(R_E / (R_E + h))
            r_horizon = R_E * np.acos(R_E / (R_E + h))

            arg = (R_E + h)/R_E * np.sin(theta_rad)
            arg_clipped = np.clip(arg, -1, 1)

            # temporary non-vectorised approach
            return R_E * (np.asin(arg_clipped) - theta_rad) if theta_rad <= theta_horizon else r_horizon

            # vectorised approach for future use
            # return np.where(
            #     theta_rad <= theta_horizon,
            #     R_E * (np.asin(arg_clipped) - theta_rad),
            #     r_horizon
            # )

        def to_dict(self) -> dict:
            return {
                "x [km]": self.x,
                "y [km]": self.y,
                "z [km]": self.z,
                "x_v [km/s]": self.x_v,
                "y_v [km/s]": self.y_v,
                "z_v [km/s]": self.z_v,
                "latitude [deg]": self.lat,
                "longitude [deg]": self.lon,
                "altitude [km]": self.alt
            }

    class _Topocentric:
        """Topocentric (Local Horizon Frame)"""

        def __init__(self, parent) -> None:
            self.parent = parent

            # parameters
            self._alt = None
            self._azimuth = None
            self._distance = None

        def altitude_azimuth_and_distance(self, observer: GeographicPosition) -> tuple[float, float, float]:
            """returns tha altitude [degrees], azimuth [degrees] and distance [km] from the observer"""
            if not self.parent.gcrs_position:
                return math.nan, math.nan, math.nan

            diff = self.parent.gcrs_position - observer.at(self.parent.time)
            alt, azimuth, distance = diff.altaz()
            self._alt, self._azimuth, self._distance = alt.degrees, azimuth.degrees, distance.km
            return self._alt, self._azimuth, self._distance

        @property
        def alt(self) -> float:
            """altitude angle [deg] from observer

            this property will return the altitude [degree] of the last calculated altitude - based on the last call to `self.altitude_azimuth_and_distance` with the provided observer location. otherwise this will error"""
            if self._alt:
                return self._alt
            raise AttributeError(
                "This attribute will only exist after `self.altitude_azimuth_and_distance` is called")

        @property
        def azimuth(self) -> float:
            """azimuth angle [deg] from observer

            this property will return the azimuth [degree] of the last calculated azimuth - based on the last call to `self.altitude_azimuth_and_distance` with the provided observer location. otherwise this will error"""
            if self._azimuth:
                return self._azimuth
            raise AttributeError(
                "This attribute will only exist after `self.altitude_azimuth_and_distance` is called")

        @property
        def distance(self) -> float:
            """distance [km] from observer

            this property will return the distance [km] of the last calculated distance - based on the last call to `self.altitude_azimuth_and_distance` with the provided observer location. otherwise this will error"""
            if self._alt:
                return self._alt
            raise AttributeError(
                "This attribute will only exist after `self.altitude_azimuth_and_distance` is called")

        altitude = alt


class BasePropagation:
    def error_estimate(self, time: ACCEPTABLE_TIME_TYPES) -> float:
        # TODO: Implement or remove
        # ? Maybe
        raise NotImplementedError

    def propagate(self, sat: Satellite | list[Satellite] | SatelliteSet, time: ACCEPTABLE_TIME_TYPES) -> list[OrbitalPosition]:
        """estimate the satellite location

        Args:
            time: propagation time

        Returns:
            Position (further methods to work with various reference frames and extract useful data)
        """
        if isinstance(sat, Satellite):
            return [self._propagate(sat, time)]

        if isinstance(sat, SatelliteSet):
            sat = sat.sats

        return [self._propagate(item, time) for item in sat]

    def _propagate(self, sat: Satellite, time: ACCEPTABLE_TIME_TYPES) -> OrbitalPosition:
        """internal method without type checking and cohesion.

        This should be implemented by all child classes"""
        raise NotImplementedError


class SGP4Propagation(BasePropagation):
    """Propagation using the SGP4 (Special General Perturbations Model)

    This is the most accurate propagation model for this dataset and is accurate for 2 weeks +/- epoch"""

    def _propagate(self, sat: Satellite, time: ACCEPTABLE_TIME_TYPES) -> OrbitalPosition:
        time = accept_any_datetime(time)
        return OrbitalPosition(sat, sat._sat.at(time), time)


class KeplerianPropagation(BasePropagation):
    """Keplerian propagation (two-body problem) - uses a single SPG4 for orbital parameters

    This method only supports `pos.geo.x`, `pos.geo.y` and `pos.geo.z`

    This does not accurate for perturbations and is accurate for about 24hours +/- epoch"""

    def __init__(self) -> None:
        super().__init__()

        self._cached_orbital_positions: dict[int, OrbitalPosition] = {}
        self._cached_theta0: dict[int, float] = {}

    def _propagate(self, sat: Satellite, time: ACCEPTABLE_TIME_TYPES) -> OrbitalPosition:
        # get keplerian/oscilating elements using SGP4 propagation if they haven't been calculated
        time = accept_any_datetime(time)
        if not (sat.id in self._cached_orbital_positions):
            p0 = SGP4Propagation()._propagate(
                sat, time=time)
            p0._calculate_osculating_elements()
            self._cached_orbital_positions[sat.id] = p0

            theta0 = self._greenwich_sidereal_angle(time)
            self._cached_theta0[sat.id] = theta0
        else:
            p0 = self._cached_orbital_positions[sat.id]
            theta0 = self._cached_theta0[sat.id]

        # TODO: Include or remove ECI data points
        r_ECI, v_ECI, r_ECEF = self._propagate_kepler(
            a=p0.a,
            e=p0.e,
            i=p0.i,
            RAAN=p0.RAAN,
            argp=p0.argument_of_periapsis,
            M0=p0.mean_anomaly,
            t=time.utc_datetime().timestamp(),  # type: ignore
            t0=p0.time.utc_datetime().timestamp(),  # type: ignore
            theta0=theta0
        )

        p = OrbitalPosition(sat, None, time)
        p.geo._x, p.geo._y, p.geo._z = r_ECEF

        return p

    # Rotation matrices

    @staticmethod
    def _R3(theta):
        return np.array([
            [np.cos(theta), -np.sin(theta), 0],
            [np.sin(theta),  np.cos(theta), 0],
            [0,              0,             1]
        ])

    @staticmethod
    def _R1(theta):
        return np.array([
            [1, 0,              0],
            [0, np.cos(theta), -np.sin(theta)],
            [0, np.sin(theta),  np.cos(theta)]
        ])

    # Solve Kepler's equation M = E - e sinE
    @staticmethod
    def _solve_kepler(M, e, tol=1e-12, max_iter=100):
        E = M if e < 0.8 else np.pi  # good starting guess
        for _ in range(max_iter):
            f = E - e*np.sin(E) - M
            fprime = 1 - e*np.cos(E)
            E_new = E - f/fprime
            if abs(E_new - E) < tol:
                return E_new
            E = E_new
        raise RuntimeError("Kepler's equation did not converge")

    @staticmethod
    def _greenwich_sidereal_angle(utc_datetime: Time):
        """
        Approximate Greenwich Sidereal Angle (theta0) at given UTC datetime in radians.
        Uses simplified method (ignores nutation, small corrections).
        """
        # Julian Date
        dt = utc_datetime.utc_datetime() - \
            datetime.datetime(2000, 1, 1, 12, tzinfo=datetime.timezone.utc)
        JD = 2451545.0 + dt.total_seconds()/86400.0

        # Time in Julian centuries since J2000.0
        T = (JD - 2451545.0)/36525.0

        # Greenwich Mean Sidereal Time at 0h UT (in degrees)
        GMST = 280.46061837 + 360.98564736629 * \
            (JD - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0
        GMST = np.mod(GMST, 360.0)

        return np.radians(GMST)  # convert to radians

    @staticmethod
    def _propagate_kepler(a, e, i, RAAN, argp, M0, t, t0, mu=398600.4418, omega_earth=7.2921159e-5, theta0=0.0):
        """
        Inputs:
        a     - semi-major axis (km)
        e     - eccentricity (0<=e<1)
        i     - inclination (rad)
        RAAN  - right ascension of ascending node Ω (rad)
        argp  - argument of perigee ω (rad)
        M0    - mean anomaly at epoch t0 (rad)
        t, t0 - current time and reference epoch (s)
        mu    - gravitational parameter (km^3/s^2)
        omega_earth - Earth's rotation rate (rad/s)
        theta0      - Greenwich sidereal angle at t0 (rad)
        Returns:
        r_ECI, v_ECI - position (km) and velocity (km/s) in ECI frame
        r_ECEF       - position (km) in Earth-fixed frame
        """
        cls = KeplerianPropagation

        # Mean motion - constant
        n = np.sqrt(mu / a**3)

        # Mean anomaly at time t
        M = M0 + n*(t - t0)
        M = np.mod(M, 2*np.pi)

        # Solve Kepler's equation for eccentric anomaly
        E = cls._solve_kepler(M, e)

        # True anomaly and radius
        nu = np.arctan2(np.sqrt(1-e**2)*np.sin(E), np.cos(E)-e)
        r = a*(1 - e*np.cos(E))
        p = a*(1 - e**2)

        # Position, velocity in perifocal frame
        r_pf = np.array([r*np.cos(nu), r*np.sin(nu), 0.0])
        v_pf = np.sqrt(mu/p) * np.array([-np.sin(nu), e+np.cos(nu), 0.0])

        # Rotate to ECI
        Q = cls._R3(RAAN) @ cls._R1(i) @ cls._R3(argp)
        r_ECI = Q @ r_pf
        v_ECI = Q @ v_pf

        # Convert to ECEF (simple Earth rotation model with arbitrary theta0)
        theta_gst = theta0 + omega_earth * (t - t0)
        r_ECEF = cls._R3(theta_gst) @ r_ECI

        return r_ECI, v_ECI, r_ECEF


class CubicInterpolation(BasePropagation):
    """Cubic interpolation of SPG4

    CubicInterpolation does not currently support Topocentric interpolation. Please use `SGP4Propagation` instead"""
    # !: This is a beta feature
    # TODO: Implement CubicInterpolation to support Topocentric too

    def __init__(
            self,
            *,
            interpolation_interval: datetime.timedelta = datetime.timedelta(
                seconds=120),
            interpolated_values: list[str] = []
    ) -> None:
        """setup cubic interpolation and define what values should be interpolated (i.e. `interpolated_values = ['geo.x', 'geo.y', 'geo.z']`)

        Args:
            interpolation_interval: _description_. Defaults to datetime.timedelta( seconds=60).
            interpolated_values: _description_. Defaults to [].
        """
        super().__init__()

        from scipy.interpolate import CubicSpline

        self._cached_values: dict[int, dict[str, NDArray[np.float64]]] = {}
        self._cubic_splines: dict[int, dict[str, CubicSpline]] = {}

        self._SGP4_propagator = SGP4Propagation()

        self._interpolation_interval = interpolation_interval
        self._interpolated_values = interpolated_values

    def _propagate_and_add_to_cached_values(self, sat: Satellite, time: Time) -> None:
        # propagate using SGP4
        position = self._SGP4_propagator.propagate(sat, time)[0]

        # save time
        t_unix = time.utc_datetime().timestamp()  # type: ignore
        self._cached_values[sat.id]["time"] = np.append(
            self._cached_values[sat.id]["time"], t_unix)

        # extract required attributes and add to self._cached values
        for name in self._interpolated_values:
            try:
                # extract value
                obj = position
                for attr_name in name.split("."):
                    obj = getattr(obj, attr_name)

                # write value to self._cached_values
                self._cached_values[sat.id][name] = np.append(
                    self._cached_values[sat.id][name], obj  # type:ignore
                )
            except Exception as e:
                raise Exception(
                    f"{name} is not an attribute of {position}: {e}")

    def _calculate_cubic_splines(self, sat: Satellite) -> None:
        from scipy.interpolate import CubicSpline

        for key, value in self._cached_values[sat.id].items():
            if key == "time":
                continue
            if math.isnan(value[0]):
                raise SGP4PropagationError(
                    f"{sat.id=}, {key=}, {value=}: value is invalid due to SGP4 propagation error")
            self._cubic_splines[sat.id][key] = CubicSpline(
                self._cached_values[sat.id]["time"], value)

    def init_interpolation(self, sat: Satellite, time: Time) -> None:
        # define the number of inital points and start time (equidistance about the propagation time)
        initial_SGP4_points = 4
        t_start = time - (initial_SGP4_points-1)/2*self._interpolation_interval

        # generate initial caches
        self._cached_values[sat.id] = {}
        self._cubic_splines[sat.id] = {}
        self._cached_values[sat.id]["time"] = np.array([])
        for name in self._interpolated_values:
            self._cached_values[sat.id][name] = np.array([])

        # calculate each SGP4 position
        for i in range(0, initial_SGP4_points):
            t = t_start + self._interpolation_interval * i

            self._propagate_and_add_to_cached_values(sat, t)

        # calculate cubic splines
        self._calculate_cubic_splines(sat)

    def extend_interpolation(self, sat: Satellite, forward: bool = True) -> None:
        time = ts.from_datetime(
            datetime.datetime.fromtimestamp(
                self._cached_values[sat.id]["time"][-1], tz=utc
            ) + self._interpolation_interval)
        self._propagate_and_add_to_cached_values(sat, time)
        self._calculate_cubic_splines(sat)

    def _update_interpolation(self, start_time: Time, end_time: Time, interval: datetime.timedelta) -> None:
        # ? Remove
        # TODO: Implement
        # TODO: Include Sat in parameters
        # ? Use different methods to do different interpolations? (new vs extend)
        # ? Remove old data?

        # 1. Calculate new values
        # 2. Put into cached values
        # 3. Calculate cubic splines
        pass

    def _propagate(self, sat: Satellite, time: ACCEPTABLE_TIME_TYPES) -> OrbitalPosition:
        time = accept_any_datetime(time)
        t_unix = time.utc_datetime().timestamp()  # type:ignore

        # Calculate cubic splines if they don't exist
        if sat.id not in self._cubic_splines:
            self.init_interpolation(sat, time)

        # check if the interpolation is in range (if not extend)
        while t_unix < self._cached_values[sat.id]["time"][0]:
            raise NotImplementedError(
                "Backwards propagation is not yet supported with this propagation mode")

        while t_unix > self._cached_values[sat.id]["time"][-1]:
            self.extend_interpolation(sat)

        # create the output position object
        position = OrbitalPosition(sat, None, time)

        # interpolate the values
        for name in self._interpolated_values:
            # calculate value with cubic interpolation
            value = self._cubic_splines[sat.id][name](t_unix)

            # save the value to the position object
            obj = position
            for attr_name in name.split(".")[:-1]:
                obj = getattr(obj, attr_name)
            setattr(obj, "_"+name.split(".")[-1], value)

        return position


class HybridPropagation(BasePropagation):
    """SPG4 and Keplerian weighted"""
    # ! Waiting on KeplerianPropagation before implementation
    # TODO: Implement this
