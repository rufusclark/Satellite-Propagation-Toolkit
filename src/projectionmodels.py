"""contains grids for projecting satellite locations onto rectangular grids"""
from typing_extensions import Self, Sequence

import math

from skyfield.toposlib import GeographicPosition
from skyfield.timelib import Time

from .models import Sats, SatPosition
from .matrix import Matrix, ImageFrame
from .analysis import BasePixelModifier

EARTH_RADIUS = 6371  # [km] mean radius


class SatFrame:
    """SatFrame is a frame with the same dimension as the matrix in it's constructor and contains all the sats that fall within the frame area in its specified model.

    use the `generate_sat_frame` method from models to create a new sat frame.

    sat frames can be used for analysis in place or for generating ImageFrame using the `render` method
    """

    def __init__(self, model: "BaseProjectionModel", time: Time, sats: list[SatPosition] = []) -> None:
        self.model = model
        self._sats = sats
        self.time = time

    @property
    def sats(self) -> list[SatPosition]:
        return self._sats

    def add_sat(self, sat: SatPosition) -> None:
        self._sats.append(sat)

    @property
    def unix_timestamp(self) -> float:
        """unix timestamp of frame in seconds including microseconds

        Returns:
            float seconds since epoch
        """
        return self.time.utc_datetime().timestamp()  # type: ignore

    @property
    def unix_timestamp_seconds(self) -> int:
        """unix timestamp of frame in seconds - no microseconds

        Returns:
            integer seconds since epoch
        """
        return int(self.unix_timestamp)

    @property
    def cells(self) -> int:
        """number of cells"""
        return len(self.model._matrix)

    @property
    def density(self) -> float:
        """average cell density"""
        return self.number_of_sats / self.cells

    @property
    def number_of_sats(self) -> int:
        return len(self._sats)

    def info(self) -> str:
        """outputs useful information about the SatFrame and the sat's within it

        Returns:
            str information output
        """
        return f"Sat Frame (sats: {self.number_of_sats})\n  propagation time: {self.time.utc_strftime('%Y-%m-%d %H:%M:%S')}\n  {self.model._matrix.info()}\n{self.model.info()}\n{''.join([sat.info() for sat in self.sats])}"

    def render(self, modifiers: Sequence[BasePixelModifier]) -> ImageFrame:
        """render a new ImageFrame object from this object based on the sats in this frame and their tags and other data

        Args:
            modifiers: list of modifiers to apply to sats

        Returns:
            New ImageFrame object
        """
        # generate appropriate info
        modifier_str = "Key\n  " + \
            "\n  ".join([modifier.info() for modifier in modifiers])

        # create new image frame
        frame = ImageFrame(self.model._matrix, self.time,
                           _sat_frame=self, _modifier_info=modifier_str)

        # render frame
        for sat in self.sats:
            rgb = frame.get_pixel(sat.x, sat.y)
            for modifier in modifiers:
                rgb = modifier.handle(sat, rgb)
            frame.set_pixel(sat.x, sat.y, rgb)
        return frame


class BaseProjectionModel:
    name: str

    def __init__(self, matrix: Matrix, sats: Sats, observer: GeographicPosition, x_width: float = 0.5, y_width: float = 0.5) -> None:
        """create a new projection model

        please note models can also be created using the `from_FoV` method instead of using the x_width and y_width

        Args:
            matrix: Matrix object representing the size of output
            sats: Sats object containing all the sats to include in analysis
            observer: GeographicPosition of the observer. note the origin may differ depending on type of model.
            x_width: cell width [degrees per cell]. Defaults to 0.5.
            y_width: cell height [degrees per cell]. Defaults to 0.5.
        """
        self._matrix = matrix
        self._sats = sats
        self.origin = observer
        self.x_width = x_width
        self.y_width = y_width

    @classmethod
    def from_FoV(cls, matrix: Matrix, sats: Sats, observer: GeographicPosition, FoV: float) -> Self:
        """create a new projection model

        Args:
            matrix: Matrix object representing the size of output
            sats: Sats object containing all the sats to include in analysis
            observer: GeographicPosition of the observer. note the origin may differ depending on type of model.
            FoV: FoV of the observer in degrees
        """
        return cls(matrix, sats, observer, *cls._cell_width_and_height_from_FoV(matrix, FoV))

    @classmethod
    def _cell_width_and_height_from_FoV(cls, matrix: Matrix, FoV: float) -> tuple[float, float]:
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


class GeocentricProjectionModel(BaseProjectionModel):
    """Geocentric Grid above an observer on the surface of the Earth and about the surface of the Earth where each row and col represents a given number of degrres change in latitude and longitude respectively"""
    name = "geo"

    def info(self) -> str:
        from .models import Orbits
        orbits = Orbits()

        lat = self.origin.latitude.degrees
        lon = self.origin.longitude.degrees
        lat_str = f"{lat:.2f}°N" if lat > 0 else f"{abs(lat):.2f}°S"
        lon_str = f"{lon:.2f}°E" if lon > 0 else f"{abs(lon):.2f}°W"

        orbit_str = [
            f'  {orbit.name} - {orbit.alt}km - minimum FoV {self.minimum_FoV(orbit.alt):.0f}° - area equivalent FoV {self.equivalent_FoV(orbit.alt):.0f}°\n' for orbit in orbits.orbits
        ]

        return f"Geocentric Projection\n  observer: {lat_str}, {lon_str}\n  cell width: {self.y_width:.2f}°N/S, {self.x_width:.2f}°E/W\n  field of view depends on altitude as observer and oribit are not co-located\n{''.join(orbit_str)}"

    def generate_sat_frame(self, t: Time) -> SatFrame:
        """checks whether each sat in sats falls within the grid box when propogated to a given time defined about the center of the Earth above the origin location. This checks whether each satellite is within a given latitude and longitude range around the observer.

        If the sat falls within this grid the it is added to the SatFrame and returned. The (x, y) coordinates and sat provided as args, where the top left cell is given the position (0, 0).

        Args:
            t: Time propogation time for sat.
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

    @classmethod
    def _cell_width_and_height_from_FoV(cls, matrix: Matrix, FoV: float) -> tuple[float, float]:
        """calculate the width and height per cell for a given matrix, m, with the desired (area equivalent) FoV

        altitude is assumed to be 3000km for a reasonable estimation, please note FoV where the observer and origin are not co-located differs based on what difference it is measured from

        Args:
            matrix: Matrix
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
        """calculate the field of view relative to the origin (Earth's centre)

        Args:
            FoV: Field of view about the observer [degrees]
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
        """calculate the field of view relative to the observer (on Earth's surface)

        Args:
            origin_FoV: Field of view about the origin [degrees]
            alt: altitude [km]

        Returns:
            FoV from observer [degrees]
        """
        A = 0.5 * origin_FoV
        b = EARTH_RADIUS + alt
        c = EARTH_RADIUS
        a = math.sqrt(b**2 + c**2 - 2 * b * c * math.cos(math.radians(A)))
        B = math.degrees(math.asin(b/a * math.sin(math.radians(A))))
        D = 180 - B

        return 2 * D

    def minimum_FoV(self, alt: float) -> float:
        """minimum FoV within model from the observer for a given altitude [km]

        Args:
            alt: altitude [km]

        Returns:
            Field of view [degrees]
        """
        return self._FoV_relative_to_observer(2 * min(self.width * self.x_width/2, self.height * self.y_width/2), alt)

    def equivalent_FoV(self, alt) -> float:
        """area effective FoV within model from the observer for a given altitude [km]

        this is an equivalent FoV based on the area of the square projection if it was a circle and gives a better idea of the amount of visible sky 

        Args:
            alt: altitude [km]

        Returns:
            Field of view
        """
        return self._FoV_relative_to_observer(0.5 * math.sqrt(math.pi * ((self.width * self.x_width)**2 + (self.height * self.y_width)**2)), alt)


class TopocentricProjectionModel(BaseProjectionModel):
    """Topocentric Grid about an origin on the surface of the Earth where each row and col represents a specified change in degrees North and East"""
    name = "topo"

    def info(self) -> str:
        lat = self.origin.latitude.degrees
        lon = self.origin.longitude.degrees
        lat_str = f"{lat:.2f}°N" if lat > 0 else f"{abs(lat):.2f}°S"
        lon_str = f"{lon:.2f}°E" if lon > 0 else f"{abs(lon):.2f}°W"

        return f"Topocentric Projection\n  observer: {lat_str}, {lon_str}\n  cell width: {self.y_width:.2f}°N/S, {self.x_width:.2f}°E/W\n  minimum FoV: {self.minimum_FoV():.2f}°\n  equivalent FoV: {self.equivalent_FoV():.2f}°\n"

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
        """checks whether each sat in sats falls with the grid box when progtated to a given time defined about the origin (topocentric), where the angels are perpendicular to themselves in the North and East directions. This gives an effective field of view from the origin/observer, given by north and south angles normal to the origin/observers point on the Earth.

        If the sat falls within this grid the supplied function fn is added to the SatFrame and returned where the top left cell is given the position (0, 0).

        Args:
            t: propogation time for sat.
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
            alt_distance = math.sqrt(
                distance**2 + EARTH_RADIUS**2 - 2 * distance *
                EARTH_RADIUS * math.cos(math.radians(alt + 90))
            ) - EARTH_RADIUS

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

    def equivalent_FoV(self) -> float:
        """effective FoV using a geometric approximation of the area of the projected region

        Returns:
            FoV measured in degrees
        """
        return 0.5 * math.sqrt(math.pi * ((self.width * self.x_width)**2 + (self.height * self.y_width)**2))
