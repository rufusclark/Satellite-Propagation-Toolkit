"""contains code for analysing propogation data"""
from typing import TYPE_CHECKING

from .rgb import RGB
from .models import SatPosition
from datetime import datetime
if TYPE_CHECKING:
    from .projectionmodels import SatFrame


class BasePixelModifier:
    """base class for modifiers that change rgb values based on Sat tags or otherwise
    """

    modifier: RGB

    def _is_match(self, sat: SatPosition) -> bool:
        raise NotImplementedError

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        """handle the modifier, check if the sat fits the criterium and return the new rgb values as appropriately

        Args:
            sat: Sat object
            rgb: old pixel RGB object

        Returns:
            new pixel RGB object
        """
        if self._is_match(sat):
            rgb += self.modifier
        return rgb

    def info(self) -> str:
        raise NotImplementedError()


class AlwaysPixelModifier(BasePixelModifier):
    """always changes rgb value of pixel for sat"""

    def __init__(self, modifier: RGB) -> None:
        """create a new pixel modifier that will always change the colour of the pixel by adding the modifier to the current pixel if any of the tags match the sat"""
        self.modifier = modifier

    def _is_match(self, sat: SatPosition) -> bool:
        return True

    def info(self) -> str:
        return f"{self.modifier.info()} for all sats"


class TagPixelModifier(BasePixelModifier):
    """change rgb value of pixel based on sat tags (exact match)
    """

    def __init__(self, tags: list[str] | str, modifier: RGB) -> None:
        """create a new pixel modifier that will change the colour of the pixel by adding the modifier to the current pixel if any of the tags match the sat

        Args:
            tags: string or list of string tags
            modifier: RGB object
        """
        if isinstance(tags, str):
            self.tags = [tags.lower()]
        else:
            self.tags = [tag.lower() for tag in tags]
        self.modifier = modifier

    def _is_match(self, sat: SatPosition) -> bool:
        return any(tag in sat.sat.tags for tag in self.tags)

    def info(self) -> str:
        return f"{self.modifier.info()} if sat includes one of following tags: {', '.join(self.tags)}"


class NotTagPixelMofidier(TagPixelModifier):
    """change rgb value based on not including any of these sat tags"""

    def _is_match(self, sat: SatPosition) -> bool:
        return not super()._is_match(sat)

    def info(self) -> str:
        return f"{self.modifier.info()} if sat doesn't include any of following tags: {', '.join(self.tags)}"


class FuzzyTagPixelModifier(TagPixelModifier):
    """change rgb value of pixel based on sat tags (if sat tag is within one of the given search tags)

    i.e. "comm" would match to "communication" and "navigation and communication" """

    def _is_match(self, sat: SatPosition) -> bool:
        sat_tags = sat.sat.tags
        search_tags = self.tags
        return any(search_tag in sat_tag for search_tag in search_tags for sat_tag in sat_tags)

    def info(self) -> str:
        return f"{self.modifier.info()} if sat is within one of following tags: {', '.join(self.tags)}"


class FuzzyNotTagPixelModifier(FuzzyTagPixelModifier):
    """change rgb value of pixel based on sat tags (if sat tag is not within one of the given search tags)"""

    def _is_match(self, sat: SatPosition) -> bool:
        return not super()._is_match(sat)

    def info(self) -> str:
        return f"{self.modifier.info()} if sat is not within one of following tags: {', '.join(self.tags)}"


class LaunchDateModifier(BasePixelModifier):
    def __init__(self, min_datetime: datetime, max_datetime: datetime, modifier: RGB) -> None:
        """create a new pixel modifier that will change the colour of the pixel by adding the modifier to the current pixel if the object was launched between the given datetimes

        Please note not all objects have launch tags attached, and these objects will be ignored

        Args:
            min_datetime: start datetime
            max_datetime: end datetime
            modifier: RGB modifier
        """
        self.min_datetime = min_datetime
        self.max_datetime = max_datetime
        self.modifier = modifier

    def _is_match(self, sat: SatPosition) -> bool:
        if not sat.sat.launch_date:
            return False
        return self.min_datetime < sat.sat.launch_date and self.max_datetime > sat.sat.launch_date

    def info(self) -> str:
        return f"{self.modifier.info()} if a sats launch date is between {self.min_datetime.date().isoformat()} and {self.max_datetime.date().isoformat()}"


class AltitudeModifier(BasePixelModifier):
    def __init__(self, min_alt: float, max_alt: float, modifier: RGB) -> None:
        """create a new pixel modifier that will change the colour of the pixel by adding the modifier to the current pixel if the object has an orbital alitutde between the given altitude measured in km

        Args:
            min_alt: minimum altitude [km]
            max_alt: maximum altitude [km]
            modifier: RGB modifier
        """
        self.min_alt = min_alt
        self.max_alt = max_alt
        self.modifier = modifier

    def _is_match(self, sat: SatPosition) -> bool:
        if sat.altitude == -1:
            raise Warning(
                "No altitude specified with sat, orbit altitude modifier is not support for this reference frame")
            return False
        return self.min_alt < sat.altitude and self.max_alt > sat.altitude

    def info(self) -> str:
        return f"{self.modifier.info()} if a sats altitude is between {self.min_alt}km and {self.max_alt}km"


class DistanceModifier(BasePixelModifier):
    def __init__(self, min_distance: float, max_distance: float, modifier: RGB) -> None:
        """create a new pixel modifier that will change the colour of the pixel by adding the modifier to the current pixel if the object has a distance from the observer between the given distances in km

        Args:
            min_distance: minimum distance [km]
            max_distance: maximum distance [km]
            modifier: RGB modifier
        """
        self.min_distance = min_distance
        self.max_distance = max_distance
        self.modifier = modifier

    def _is_match(self, sat: SatPosition) -> bool:
        if sat.distance == -1:
            raise Warning(
                "No distance specified with sat, orbit altitude modifier is not support for this reference frame")
            return False
        return self.min_distance < sat.distance and self.max_distance > sat.distance

    def info(self) -> str:
        return f"{self.modifier.info()} if a sats distance from observer is between {self.min_distance}km and {self.max_distance}km"


class Modifiers:
    """Container class for modifiers"""

    def __init__(self, *modifiers: BasePixelModifier) -> None:
        self.modifiers = modifiers

    def key(self) -> str:
        """return a string formatted key ready to be printed for the included modifiers"""
        return "Key\n\t" + "\n\t".join([modifier.info() for modifier in self.modifiers])

    def key_with_analysis(self, sat_frame: "SatFrame") -> str:
        """return a sring formatted key with included breakdown of the data in the SatFrame"""
        return f"Key (total sats = {sat_frame.number_of_sats})\n\t" + "\n\t".join([
            modifier.info() + f" (sats = {sum([modifier.handle(sat, RGB()) != RGB() for sat in sat_frame.sats])})" for modifier in self.modifiers
        ])
