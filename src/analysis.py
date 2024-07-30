"""contains code for analysing propogation data"""
from .rgb import RGB
from .models import Sat, SatPosition
from datetime import datetime
from typing import Any


class BasePixelModifier:
    """base class for modifiers that change rgb values based on Sat tags or otherwise
    """

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        """handle the modifier, check if the sat fits the criterium and return the new rgb values as appropriately

        Args:
            sat: Sat object
            rgb: old pixel RGB object

        Returns:
            new pixel RGB object
        """
        raise NotImplementedError

    def info(self) -> str:
        raise NotImplementedError()


class AlwaysPixelModifier(BasePixelModifier):
    """always changes rgb value of pixel for sat"""

    def __init__(self, modifier: RGB) -> None:
        """create a new pixel modifier that will always change the colour of the pixel by adding the modifier to the current pixel if any of the tags match the sat"""
        self.modifier = modifier

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        return rgb + self.modifier

    def info(self) -> str:
        return f"{self.modifier.info()} always"


class TagPixelModifier(BasePixelModifier):
    """change rgb value of pixel based on sat tags
    """

    def __init__(self, tags: list[str] | str, modifer: RGB) -> None:
        """create a new pixel modifier that will change the colour of the pixel by adding the modifier to the current pixel if any of the tags match the sat

        Args:
            tags: string or list of string tags
            modifer: RGB object
        """
        if isinstance(tags, str):
            self.tags = [tags.lower()]
        else:
            self.tags = [tag.lower() for tag in tags]
        self.modifer = modifer

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        if any(tag in sat.sat.tags for tag in self.tags):
            rgb += self.modifer
        return rgb

    def info(self) -> str:
        return f"{self.modifer} if includes one of following tags: {', '.join(self.tags)}"


class NotTagPixelMofidier(TagPixelModifier):
    """change rgb value based on not including any of these sat tags"""

    def __init__(self, tags: list[str] | str, modifer: RGB) -> None:
        """create a new pixel modifier that wil change the colour of the pixel by adding the modifier to the current pixel if none of the tags match with the sat tags

        Args:
            tags: string or list of string tags
            modifier: RGB object
        """
        super().__init__(tags, modifer)

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        if not any(tag in sat.sat.tags for tag in self.tags):
            rgb += self.modifer
        return rgb

    def info(self) -> str:
        return f"{self.modifer} if doesn't include any of following tags: {', '.join(self.tags)}"


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

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        if not sat.sat.launch_date:
            return rgb
        if self.min_datetime < sat.sat.launch_date and self.max_datetime > sat.sat.launch_date:
            rgb += self.modifier
        return rgb

    def info(self) -> str:
        return f"{self.modifier.info()} if launch date is between {self.min_datetime.date().isoformat()} and {self.max_datetime.date().isoformat()}"


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

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        if sat.altitude == -1:
            raise Warning(
                "No altitude specified with sat, orbit altitude modifier is not support for this reference frame")
            return rgb
        if self.min_alt < sat.altitude and self.max_alt > sat.altitude:
            rgb += self.modifier
        return rgb

    def info(self) -> str:
        return f"{self.modifier.info()} if altitude is between {self.min_alt}km and {self.max_alt}km"


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

    def handle(self, sat: SatPosition, rgb: RGB) -> RGB:
        if sat.distance == -1:
            raise Warning(
                "No distance specified with sat, orbit altitude modifier is not support for this reference frame")
            return rgb
        if self.min_distance < sat.distance and self.max_distance > sat.distance:
            rgb += self.modifier
        return rgb

    def info(self) -> str:
        return f"{self.modifier.info()} if distance from observer is between {self.min_distance}km and {self.max_distance}km"
