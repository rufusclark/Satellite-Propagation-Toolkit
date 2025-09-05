"""contains grids for projecting satellite locations onto rectangular grids"""
from typing_extensions import Self, Sequence

import math

from skyfield.toposlib import GeographicPosition
from skyfield.timelib import Time

from .models import SatelliteSet, Satellite
from .matrix import Matrix, ImageFrame
from .analysis import BasePixelModifier, Modifiers
from .propagation import OrbitalPosition

EARTH_RADIUS = 6371  # [km] mean radius


class FramePosition:
    """Represents a satellite at an instantaneous time and it's location within an intantaneous 2D frame"""

    def __init__(self, orbital_position: OrbitalPosition, x: float, y: float) -> None:
        self.orbital_position = orbital_position
        self.x = x
        self.y = y

    @property
    def sat(self) -> Satellite:
        return self.orbital_position.sat

    @property
    def x_idx(self) -> int:
        return int(self.x)

    @property
    def y_idx(self) -> int:
        return int(self.y)

    def to_dict(self) -> dict:
        out = self.orbital_position.to_dict()
        out["frame position"] = {
            "time": self.orbital_position.time.utc_iso(),
            "x": self.x,
            "y": self.y
        }
        return out

    def info(self) -> str:
        from pprint import pformat
        return pformat(self.to_dict())


class SatFrame:
    """SatFrame is a frame with the same dimension as the matrix in it's constructor and contains all the sats that fall within the frame area in its specified model.

    use the `generate_sat_frame` method from models to create a new sat frame.

    sat frames can be used for analysis in place or for generating ImageFrame using the `render` method
    """

    def __init__(self, model: "BaseProjection") -> None:
        self._model = model
        self._frame_positions: list[FramePosition] = []

    @property
    def frame_positions(self) -> list[FramePosition]:
        return self._frame_positions

    def add_frame_position(self, frame_position: FramePosition) -> None:
        self._frame_positions.append(frame_position)

    @property
    def model(self) -> "BaseProjection":
        return self._model

    @property
    def matrix(self) -> Matrix:
        return self._model._matrix

    @property
    def time(self) -> Time:
        """returns the time [skyfield Time object] for the first satellite position frame.

        This does not account for FramePositions with different times within the same SatFrame"""
        if not self.frame_positions:
            raise Warning(
                "No satellites within the SatFrame so no times is returned")
        return self._frame_positions[0].orbital_position.time

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
        return len(self._model._matrix)

    @property
    def density(self) -> float:
        """average cell density"""
        return self.number_of_sats / self.cells

    @property
    def number_of_sats(self) -> int:
        return len(self._frame_positions)

    def details_to_dict(self) -> dict:
        return {
            "time": self.time.utc_iso(),
            "width": self.matrix.width,
            "height": self.matrix.height,
            "density [sats/cell]": self.density,
            "number of sats": self.number_of_sats
        }

    def to_dict(self) -> dict:
        out = {
            "projection model": self.model.to_dict(),
            "satellite frame": self.details_to_dict(),
            "satellites": [frame_position.to_dict()
                           for frame_position in self.frame_positions]
        }
        return out

    def info(self) -> str:
        """outputs useful information about the SatFrame and the sat's within it

        Returns:
            str information output
        """
        from pprint import pformat
        return pformat(self.to_dict())

    def render(self, modifiers: Modifiers) -> ImageFrame:
        """render a new ImageFrame object from this object based on the sats in this frame and their tags and other data

        Args:
            modifiers: list of modifiers to apply to sats

        Returns:
            New ImageFrame object
        """
        return ImageFrame(self, modifiers)


class BaseProjection:
    # ! These objects (and children) should be stateless except for configuration variables
    name: str

    def __init__(self, matrix: Matrix, observer: GeographicPosition, x_width: float = 0.5, y_width: float = 0.5) -> None:
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
        self.origin = observer
        self.x_width = x_width
        self.y_width = y_width

    @classmethod
    def from_FoV(cls, matrix: Matrix, observer: GeographicPosition, FoV: float) -> Self:
        """create a new projection model

        Args:
            matrix: Matrix object representing the size of output
            sats: Sats object containing all the sats to include in analysis
            observer: GeographicPosition of the observer. note the origin may differ depending on type of model.
            FoV: FoV of the observer in degrees
        """
        return cls(matrix, observer, *cls._cell_width_and_height_from_FoV(matrix, FoV))

    def project(self, orbital_positions: OrbitalPosition | list[OrbitalPosition]) -> SatFrame:
        """projects the orbital_positions onto a 2D plane based on the Projection Model and it's configurations
        """
        if isinstance(orbital_positions, OrbitalPosition):
            orbital_positions = [orbital_positions]
        return self._project(orbital_positions)

    def _project(self, orbital_positions: list[OrbitalPosition]) -> SatFrame:
        raise NotImplementedError()

    @classmethod
    def _cell_width_and_height_from_FoV(cls, matrix: Matrix, FoV: float) -> tuple[float, float]:
        raise NotImplementedError()

    def to_dict(self) -> dict:
        raise NotImplementedError()

    def info(self) -> str:
        from pprint import pformat
        return pformat(self.to_dict())

    @property
    def width(self) -> int:
        return self._matrix.width

    @property
    def height(self) -> int:
        return self._matrix.height

    @property
    def fmt_lat(self) -> str:
        lat = self.origin.latitude.degrees
        return f"{lat:.2f}°N" if lat > 0 else f"{abs(lat):.2f}°S"

    @property
    def fmt_lon(self) -> str:
        lon = self.origin.longitude.degrees
        return f"{lon:.2f}°E" if lon > 0 else f"{abs(lon):.2f}°W"

    @property
    def fmt_lat_lon(self) -> str:
        return f"{self.fmt_lat} {self.fmt_lon}"


class GeocentricProjection(BaseProjection):
    """Geocentric Grid above an observer on the surface of the Earth and about the surface of the Earth where each row and col represents a given number of degrres change in latitude and longitude respectively"""
    name = "geo"

    def to_dict(self) -> dict:
        from .models import Orbits
        return {
            "model": "Geocentric",
            "origin": self.fmt_lat_lon,
            "orbits": [
                {
                    "name": orbit.name,
                    "altitude [km]": orbit.alt,
                    "minimum FoV [deg]": self.minimum_FoV(orbit.alt),
                    "area equivalent FoV [deg]": self.equivalent_FoV(orbit.alt)
                }
                for orbit in Orbits().orbits
            ]
        }

    def _project(self, orbital_positions: list[OrbitalPosition]) -> SatFrame:
        out_frame = SatFrame(self)

        for position in orbital_positions:
            # get position data for each sat
            lat = position.geo.lat
            lon = position.geo.lon
            alt = position.geo.alt

            # ignore sat if the position is invalid
            if math.isnan(lat) or math.isnan(lon) or math.isnan(alt):
                continue

            # calculate idx (float) within the frame and ignore if not in the frame
            x = (lon - self.origin.latitude.degrees) / \
                self.x_width + self.width/2
            if x < 0 or x >= self.width:
                continue

            y = self.height - (lat - self.origin.latitude.degrees) / \
                self.y_width + self.height/2
            if y < 0 or y >= self.height:
                continue

            out_frame.add_frame_position(FramePosition(position, x, y))

        return out_frame

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


class TopocentricProjection(BaseProjection):
    """Topocentric Grid about an origin on the surface of the Earth where each row and col represents a specified change in degrees North and East"""
    name = "topo"

    def to_dict(self) -> dict:
        return {
            "model": "Topocentric",
            "origin": self.fmt_lat_lon,
            "minimum FoV [deg]": self.minimum_FoV(),
            "area equivalent FoV [deg]": self.equivalent_FoV(),
            "cell height [deg/cell]": self.y_width,
            "cell width [deg/cell]": self.x_width
        }

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

    def _project(self, orbital_positions: list[OrbitalPosition]) -> SatFrame:
        out_frame = SatFrame(self)

        for position in orbital_positions:
            # get position data for each sat
            alt, azi, distance = position.topo.altitude_azimuth_and_distance(
                self.origin
            )

            # ignore sat if the position is invalid
            if math.isnan(alt) or math.isnan(azi) or math.isnan(distance):
                continue

            # tinker with azimuth so North is up
            azi += 90

            # calculate north and east postion from alt/azi
            N = (90 - alt) * math.sin(math.radians(azi))
            E = (90 - alt) * math.cos(math.radians(azi))

            # calculate idx (float) within the frame and ignore if not in the frame
            x = E/self.x_width + self.width/2
            if x < 0 or x >= self.width:
                continue

            y = N/self.y_width + self.height/2
            if y < 0 or y >= self.height:
                continue

            out_frame.add_frame_position(FramePosition(position, x, y))

        return out_frame

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
