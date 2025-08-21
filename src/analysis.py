"""contains code for analysing propogation data"""
from typing import TYPE_CHECKING

from .rgb import RGB
from datetime import datetime
if TYPE_CHECKING:
    from .projection import SatFrame, FramePosition


class BasePixelModifier:
    """base class for modifiers that change rgb values based on Sat tags or otherwise
    """

    modifier: RGB
    name: str

    def _is_match(self, sat: "FramePosition") -> bool:
        raise NotImplementedError

    def description(self) -> str:
        raise NotImplementedError()

    def handle(self, sat: "FramePosition", rgb: RGB) -> RGB:
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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "modifier": self.modifier,
            "description": self.description()
        }

    def info(self) -> str:
        from pprint import pformat
        return pformat(self.to_dict())


class AlwaysPixelModifier(BasePixelModifier):
    """always changes rgb value of pixel for sat"""
    name = "AlwaysPixelModifier"

    def __init__(self, modifier: RGB) -> None:
        """create a new pixel modifier that will always change the colour of the pixel by adding the modifier to the current pixel if any of the tags match the sat"""
        self.modifier = modifier

    def _is_match(self, sat: "FramePosition") -> bool:
        return True

    def description(self) -> str:
        return "applied to all satellites"


class TagPixelModifier(BasePixelModifier):
    """change rgb value of pixel based on sat tags (exact match)
    """
    name = "TagPixelModifier"

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

    def _is_match(self, sat: "FramePosition") -> bool:
        return any(tag in sat.sat.tags for tag in self.tags)

    def description(self) -> str:
        return f"applied to all satellites if they include one of the following tags: {', '.join(self.tags)}"


class NotTagPixelMofidier(TagPixelModifier):
    """change rgb value based on not including any of these sat tags"""

    def _is_match(self, sat: "FramePosition") -> bool:
        return not super()._is_match(sat)

    def description(self) -> str:
        return f"applied to all satellites if they don't include any of the following tags: {', '.join(self.tags)}"


class FuzzyTagPixelModifier(TagPixelModifier):
    """change rgb value of pixel based on sat tags (if sat tag is within one of the given search tags)

    i.e. "comm" would match to "communication" and "navigation and communication" """

    def _is_match(self, sat: "FramePosition") -> bool:
        sat_tags = sat.sat.tags
        search_tags = self.tags
        return any(search_tag in sat_tag for search_tag in search_tags for sat_tag in sat_tags)

    def description(self) -> str:
        return f"applied to all satellites where satellites tags are within any of the following tags: {', '.join(self.tags)}"


class FuzzyNotTagPixelModifier(FuzzyTagPixelModifier):
    """change rgb value of pixel based on sat tags (if sat tag is not within one of the given search tags)"""

    def _is_match(self, sat: "FramePosition") -> bool:
        return not super()._is_match(sat)

    def description(self) -> str:
        return f"applied to all satellites where satellites tags are not within any of the following tags: {', '.join(self.tags)}"


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

    def _is_match(self, sat: "FramePosition") -> bool:
        if not sat.sat.launch_date:
            return False
        return self.min_datetime < sat.sat.launch_date and self.max_datetime > sat.sat.launch_date

    def description(self) -> str:
        return f"applied to all satellites which were launched between {self.min_datetime.date().isoformat()} and {self.max_datetime.date().isoformat()}"


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

    def _is_match(self, sat: "FramePosition") -> bool:
        alt = sat.orbital_position.geo.alt  # [km]
        return self.min_alt < alt and self.max_alt > alt

    def description(self) -> str:
        return f"applied to all satellites which have an altitude between {self.min_alt}km and {self.max_alt}km"


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

    def _is_match(self, sat: "FramePosition") -> bool:
        distance = sat.orbital_position.topo.distance
        if not distance:
            raise Warning(
                "Distance is only calculated from an observer when using Topocentric projections. Perhaps use Altitude instead if this is the case"
            )

        return self.min_distance < distance and self.max_distance > distance

    def description(self) -> str:
        return f"applied to all satellites which have a distance from observer between {self.min_distance}km and {self.max_distance}km"


class Modifiers:
    """Container class for modifiers"""

    def __init__(self, *modifiers: BasePixelModifier) -> None:
        self.modifiers = modifiers

    def key_to_dict(self) -> list:
        """return a list of dictionaries explaining the key for the Image and modifiers"""
        return [modifier.to_dict() for modifier in self.modifiers]

    def key_with_analysis_to_dict(self, sat_frame: "SatFrame") -> list:
        """return a list of dictionaries explaining the key for the Image and modifiers alongs with the number in each category"""
        out = []
        for modifier in self.modifiers:
            item = modifier.to_dict()
            item["count"] = sum(
                [modifier.handle(sat, RGB()) != RGB()
                 for sat in sat_frame.frame_positions]
            )
            out.append(item)
        return out

    def info(self) -> str:
        from pprint import pformat
        return pformat(self.key_to_dict())

    def key(self) -> str:
        """return a string formatted key ready to be printed for the included modifiers"""
        raise NotImplementedError()
        return "Key\n\t" + "\n\t".join([modifier.info() for modifier in self.modifiers])

    def key_with_analysis(self, sat_frame: "SatFrame") -> str:
        """return a sring formatted key with included breakdown of the data in the SatFrame"""
        raise NotImplementedError()
        return f"Key (total sats = {sat_frame.number_of_sats})\n\t" + "\n\t".join([
            modifier.info() + f" (sats = {sum([modifier.handle(sat, RGB()) != RGB() for sat in sat_frame.frame_positions])})" for modifier in self.modifiers
        ])
