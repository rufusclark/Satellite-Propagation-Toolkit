"""contains grids for projecting satellite locations onto square grids"""
from typing_extensions import Self, Sequence

import math

from skyfield.toposlib import GeographicPosition
from skyfield.timelib import Time

from .models import Sats, SatPosition
from .matrix import Matrix, ImageFrame
from .analysis import BasePixelModifier

EARTH_RADIUS = 6371  # [km] mean radius


class SatFrame:
    # TODO: Docs
    def __init__(self, model: "BaseProjectionModel", time: Time, sats: list[SatPosition] = []) -> None:
        self.model = model
        self._sats = sats
        self.time = time

    @property
    def sats(self) -> list[SatPosition]:
        return self._sats

    def add_sat(self, sat: SatPosition) -> None:
        self._sats.append(sat)

    def __len__(self) -> int:
        return len(self._sats)

    def info(self) -> str:
        # TODO: Implement
        raise NotImplementedError()

    def render(self, modifiers: Sequence[BasePixelModifier]) -> ImageFrame:
        # Convert SatFrame to ImageFrame
        # TODO: Docs
        frame = ImageFrame(self.model._matrix, self.time)
        for sat in self.sats:
            rgb = frame.get_pixel(sat.x, sat.y)
            for modifier in modifiers:
                rgb = modifier.handle(sat, rgb)
            frame.set_pixel(sat.x, sat.y, rgb)
        return frame


class BaseProjectionModel:
    name: str

    def __init__(self, matrix: Matrix, sats: Sats, observer: GeographicPosition, x_width: float = 0.5, y_width: float = 0.5) -> None:
        self._matrix = matrix
        self._sats = sats
        self.origin = observer
        self.x_width = x_width
        self.y_width = y_width

    @classmethod
    def from_FoV(cls, matrix: Matrix, sats: Sats, observer: GeographicPosition, FoV: float) -> Self:
        # TODO: Add documentation
        return cls(matrix, sats, observer, *cls._cell_width_and_height_from_FoV(matrix, FoV))

    @classmethod
    def _cell_width_and_height_from_FoV(cls, matrix: Matrix, FoV: float) -> tuple[float, float]:
        # TODO: Implement for all children
        # TODO: Implement this method for all children
        raise NotImplementedError()

    def generate_sat_frame(self, t: Time) -> SatFrame:
        raise NotImplementedError()

    def info(self) -> str:
        raise NotImplementedError()

    @property
    def width(self) -> int:
        return self._matrix.width

    @property
    def height(self) -> int:
        return self._matrix.height

    def minimum_FoV(self) -> float:
        # ! Should this be removed
        # ? Use reasonable estimate for Geocentric
        raise NotImplementedError()

    def effective_FoV(self) -> float:
        # ! Should this be removed
        # ? Use reasonable estimate for Geocentric
        raise NotImplementedError()


class GeocentricProjectionModel(BaseProjectionModel):
    """Geocentric Grid over an origin on the surface of the Earth where each row and col represents a specified change in latitude and longitude"""
    name = "geo"

    def info(self) -> str:
        from .models import Orbits
        orbits = Orbits()
        orbit_data = [
            f"At {orbit.name} ({orbit.alt}km), effective FoV is {self.effective_FoV(orbit.alt):.0f} degrees and minimum FoV is {self.minimum_FoV(orbit.alt):.0f} degrees" for orbit in orbits.orbits]
        new_line = "\n"

        return f"Geocentric Projection about {self.origin.latitude.degrees:.2f} degrees North and {self.origin.longitude.degrees:.2f} degrees East where each cell has a width of {self.x_width} degrees and height of {self.y_width} degrees \n{new_line.join(orbit_data)}"

    def generate_sat_frame(self, t: Time) -> SatFrame:
        # TODO: Alters docs for new code
        """checks whether each sat in sats falls within the grid box when propogated to a given time defined about the center of the Earth above the origin location. This checks whether each satellite is within a given latitude and longitude range around the observer.

        If the sat falls within this grid the supplied function fn is called with the (x, y) coordinates and sat provided as args, where the top left cell is given the position (0, 0).

        This does not estimate using the angles from the observer, for this use `compute_sat_position_topocentric()`.

        Example Usage:
            >>> compute_sat_position_geocentric(sats, lambda x, y, sat: print(f"row={x} col={y} {sat=}"))

        Args:
            sats: satellites objects
            fn: function to be called when the sat falls within the range
            t: propogation time for sat. Defaults to ts.now().
        """
        frame = SatFrame(self, t)

        for sat in self._sats.sats:
            # propogate
            lat, lon, alt = sat.projected_lat_lon_alt(t)

            # ignore when propogation is invalid
            if math.isnan(lat) or math.isnan(lon) or math.isnan(alt):
                continue

            # calculate idx within frame of sat
            x = int((lon - self.origin.longitude.degrees) /
                    self.x_width + self.width/2)
            if x < 0 or x >= self.width:
                continue

            y = self.height - int((lat - self.origin.latitude.degrees) /
                                  self.y_width + self.height/2)
            if y < 0 or y >= self.height:
                continue

            frame.add_sat(SatPosition(sat, x, y, altiude=alt))

        return frame

    # @DeprecationWarning
    def _cell_bounds(self, x: int, y: int) -> tuple[float, float, float, float]:
        """returns the bounds of a grid cell with position (x, y). Please note positions are zero indexed

        Args:
            x: row position
            y: col position

        Returns:
            min_lat, min_lon, max_lat, max_lon
        """
        # calculate (0,0)-th lat and lon
        lat_00 = self.origin.latitude.degrees - \
            (self.height/2) * self.y_width
        lon_00 = self.origin.longitude.degrees - \
            (self.width/2) * self.x_width

        # calculate lat and lon for edges of box
        min_lat = lat_00 + self.y_width * y
        max_lat = min_lat + self.y_width
        min_lon = lon_00 + self.x_width * x
        max_lon = min_lon + self.x_width

        return min_lat, min_lon, max_lat, max_lon

    # # @DeprecationWarning
    # def cell_observer_angles(self, x: int, y: int, altitude: float) -> tuple[float, float]:
    #     """returns the minimum and maximum observer altitude angle [degrees] from above the horizon of a grid cell with given position (x, y) for a given altitude in km

    #     Args:
    #         x: row position
    #         y: col position
    #         observer: GeographicPosition to measure angles from
    #         altitude: altitude of box for calculation in km

    #     Returns:
    #         minimum observer altitude angle,
    #         maximum obxerver altitude angle
    #     """
    #     t = ts.now()

    #     # calculate lat/lon position of cell bounds
    #     min_lat, min_lon, max_lat, max_lon = self._cell_bounds(x, y)

    #     def alt_angle(lat, lon, alt) -> float:
    #         # define position in the sky
    #         p = wgs84.latlon(lat, lon, alt*1000)
    #         # position relative to observer
    #         diff = p - self.origin
    #         # altitude angle of point
    #         alt, _, _ = diff.at(t).altaz()
    #         return alt.degrees  # type: ignore

    #     alt_angles = [
    #         alt_angle(min_lat, min_lon, altitude),
    #         alt_angle(min_lat, max_lon, altitude),
    #         alt_angle(max_lat, min_lon, altitude),
    #         alt_angle(max_lat, max_lon, altitude)]

    #     return min(alt_angles), max(alt_angles)

    # @DeprecationWarning
    # def equivalent_altitude_angle(self, altitude: float) -> float:
    #     """returns an equivalent altitude angle from the origin for the size of the sky in observation.

    #     This is based on an approximation of the area of observation at a given altitude [km], if it was approximately as a circle on a sphere. This is purely an illustrative value.

    #     Args:
    #         altitude: altitude of project [km]

    #     Returns:
    #         equivalent altitude angle [degrees] above the horizon
    #     """
    #     EARTH_RADIUS = 6371  # km
    #     R = EARTH_RADIUS + altitude  # km

    #     min_lat, min_lon, _, _ = self._cell_bounds(0, 0)
    #     _, _, max_lat, max_lon = self._cell_bounds(self.width, self.height)

    #     # calculate the area of project lat/lon on a sphere
    #     # https://www.johndcook.com/blog/2023/02/21/sphere-grid-area/#:~:text=Area%20of%20latitude%2Flongitude%20grid&text=A%20%3D%20%CF%80%20R%C2%B2%20(sin%20%CF%86,1%20%E2%88%92%20%CE%B82)%2F180.
    #     A = math.pi * R ** 2 * (math.sin(math.radians(max_lat)) - math.sin(
    #         math.radians(min_lat))) * math.radians(max_lon - min_lon)

    #     # calculate the radius of circle on a sphere
    #     # https://math.stackexchange.com/questions/1832110/area-of-a-circle-on-sphere#:~:text=On%20a%20(flat)%20Euclidean%20plane,r)%3D%CF%80r2.
    #     r = R * math.acos(1 - A/(2*math.pi*R**2))

    #     # TODO: Account for spherical curvature in altitude below

    #     # calculate altitude angle
    #     alt_angle = math.degrees(math.atan(r/altitude))
    #     return alt_angle

    # @DeprecationWarning
    # def minimum_FoV(self, altitude: float) -> float:
    #     """calcualte the minimuse FoV of the projected

    #     This represents the smallest complete FoV cone that the seen from the observer at the given altitude

    #     Args:
    #         altitude: altitude above the observer [km]

    #     Returns:
    #         minimum FoV at this altitude
    #     """
    #     # BUG: minimum is inconsistent with effective
    #     return 2 * (90 - min(
    #         abs(self.cell_observer_angles(self.width//2, 0, altitude)[0]),
    #         abs(self.cell_observer_angles(0, self.height//2, altitude)[0])
    #     ))

    # @DeprecationWarning
    # def effective_FoV(self, altitude: float) -> float:
    #     """calculate the effective FoV of the projection based on being the same area of a projected circle

    #     Args:
    #         altitude: altitude to projected area in km

    #     Returns:
    #         effective FoV at this altitude
    #     """
    #     # BUG: effective is incosistent with minimum
    #     return 2 * (self.equivalent_altitude_angle(altitude))

    @classmethod
    def _cell_width_and_height_from_FoV(cls, matrix: Matrix, FoV: float) -> tuple[float, float]:
        """calculate the width and height per cell for a given matrix, m, with the desired (area equivalent) FoV

        altitude is assumed to be 3000km for a reasonable estimation

        Args:
            m: matrix
            FoV: desired FoV degrees

        Returns:
            cell_width, cell_height measured in degrees per cell
        """
        FoV = cls._FoV_relative_to_origin(FoV, 2000)
        cell_width = cell_height = math.sqrt(
            (4 * FoV**2)/(math.pi * (matrix.width**2 + matrix.height**2)))
        return cell_width, cell_height

    @classmethod
    def _FoV_relative_to_origin(cls, observer_FoV: float, alt: float) -> float:
        """calculate the field of view relative to the origin (Earth's Centre)

        Args:
            FoV: Field of view [degrees]
            alt: altitude [km]

        Returns:
            FoV from origin [degrees]
        """
        # calculate the FoV relative to the origin
        B = 180 - 0.5 * observer_FoV
        b = EARTH_RADIUS + alt
        c = EARTH_RADIUS
        C = math.degrees(math.asin(c/b * math.sin(math.radians(B))))
        A = 180 - B - C
        origin_FoV = 2 * A

        return origin_FoV

    @classmethod
    def _FoV_relative_to_observer(cls, origin_FoV: float, alt: float) -> float:
        # TODO: Docs
        # calculate the FoV relative to the observer
        A = 0.5 * origin_FoV
        b = EARTH_RADIUS + alt
        c = EARTH_RADIUS
        a = math.sqrt(b**2 + c**2 - 2 * b * c * math.cos(math.radians(A)))
        B = math.degrees(math.asin(b/a * math.sin(math.radians(A))))
        D = 180 - B

        return 2 * D

    def minimum_FoV(self, alt: float) -> float:
        # TODO: Docs
        return self._FoV_relative_to_observer(2 * min(self.width * self.x_width/2, self.height * self.y_width/2), alt)

    def effective_FoV(self, alt) -> float:
        # TODO: Docs
        return self._FoV_relative_to_observer(0.5 * math.sqrt(math.pi * ((self.width * self.x_width)**2 + (self.height * self.y_width)**2)), alt)


class TopocentricProjectionModel(BaseProjectionModel):
    """Topocentric Grid about an origin on the surface of the Earth where each row and col represents a specified change in degrees North and East"""
    name = "topo"

    def info(self) -> str:
        return f"Topocentric Projection about {self.origin.latitude.degrees:.3f} degrees North and {self.origin.longitude.degrees:.3f} degrees East where each cell has a width of {self.x_width} degrees and height of {self.y_width} degrees with an effective Field of View of {self.effective_FoV():.0f} degrees and minimum Field of View of {self.minimum_FoV():.0f} degrees"

    @classmethod
    def _cell_width_and_height_from_FoV(cls, matrix: Matrix, FoV: float) -> tuple[float, float]:
        """calculate the width and height per cell for a given matrix, m, with the desired (area equivalent) FoV

        Args:
            m: matrix
            FoV: desired FoV degrees

        Returns:
            cell_width, cell_height measured in degrees per cell
        """
        cell_width = cell_height = math.sqrt(
            (4 * FoV**2)/(math.pi * (matrix.width**2 + matrix.height**2)))
        return cell_width, cell_height

    def generate_sat_frame(self, t: Time) -> SatFrame:
        # TODO: Alter docs for new code
        """checks whether each sat in sats falls with the grid box when progtated to a given time defined about the origin (topocentric), where the angels are perpendicular to themselves in the North and East directions. This gives an effective field of view from the origin/observer, given by north and south angles normal to the origin/observers point on the Earth.

        If the sat falls within this grid the supplied function fn is called with the (x, y) coordinates and sat provided as args, where the top left cell is given the position (0, 0).

        Example Usage:
            >>> compute_sat_position_geocentric(sats, lambda x, y, sat: print(f"row={x} col={y} {sat=}"))

        Args:
            sats: satellites objects
            fn: function to be called when the sat falls within the range
            t: propogation time for sat. Defaults to ts.now().
        """

        sats: list[SatPosition] = []

        for sat in self._sats.sats:
            # propogate
            alt, azi, distance = sat.topocentric_alt_azimuth_distance(
                self.origin, t)

            # ignore when propogation is invalid
            if math.isnan(alt) or math.isnan(azi) or math.isnan(distance):
                continue

            # Tinker with azimuth so North is up
            azi += 90

            # calculate North and East Position from alt/azi
            N = (90 - alt) * math.sin(math.radians(azi))  # N
            E = (90 - alt) * math.cos(math.radians(azi))  # E

            # calculate idx of sat
            x = int(E/self.x_width + self.width/2)
            if x < 0 or x >= self.width:
                continue

            y = int(N/self.y_width + self.height/2)
            if y < 0 or y >= self.height:
                continue

            # calculate altitude (distance) [km]
            alt_distance = math.sqrt(distance**2 + EARTH_RADIUS**2 - 2 * distance *
                                     EARTH_RADIUS * math.cos(math.radians(alt + 90))) - EARTH_RADIUS

            sats.append(SatPosition(
                sat, x, y, altiude=alt_distance, distance=distance))

        return SatFrame(self, t, sats)

    def minimum_FoV(self) -> float:
        """minimimum FoV from the observers locations

        This represents the smallest complete FoV cone that the seen from the observer at the given altitude

        Returns:
            FoV measured in degrees
        """
        return 2 * min(self.width * self.x_width/2, self.height * self.y_width/2)

    def effective_FoV(self) -> float:
        """effective FoV using a geometric approximation of the area of the projected region

        Returns:
            FoV measured in degrees
        """
        return 0.5 * math.sqrt(math.pi * ((self.width * self.x_width)**2 + (self.height * self.y_width)**2))
