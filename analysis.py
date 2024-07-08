"""contains code for analysing propogation data"""
from rgb import RGB
from models import Sat


class BasePixelModifier:
    """base class for modifiers that change rgb values based on Sat tags or otherwise
    """

    def handle(self, sat: Sat, rgb: RGB) -> RGB:
        """handle the modifier, check if the sat fits the criterium and return the new rgb values as appropriately

        Args:
            sat: Sat object
            rgb: old pixel RGB object

        Returns:
            new pixel RGB object
        """
        raise NotImplementedError


class TagPixelModifier(BasePixelModifier):
    """change rgb value of pixel based on sat tags
    """

    def __init__(self, tags: list[str] | str, modifer: RGB) -> None:
        """create a new pixel modifier that will change the colour of the pxiel by adding the modifier to the current pixel if any of the tags match the sat

        Args:
            tags: string or list of string tags
            modifer: RGB object
        """
        if isinstance(tags, str):
            self.tags = [tags.lower()]
        else:
            self.tags = [tag.lower() for tag in tags]
        self.modifer = modifer

    def handle(self, sat: Sat, rgb: RGB) -> RGB:
        if any(tag in sat.tags for tag in self.tags):
            rgb += self.modifer
        return rgb


class NotTagPixelMofidier(TagPixelModifier):
    """change rgb value based on not including any of these sat tags"""

    def __init__(self, tags: list[str] | str, modifer: RGB) -> None:
        """create a new pixel modifier that wil change the colour of the pixel by adding the modifier to the current pixel if none of the tags match with the sat tags

        Args:
            tags: string or list of string tags
            modifier: RGB object
        """
        super().__init__(tags, modifer)

    def handle(self, sat: Sat, rgb: RGB) -> RGB:
        if not any(tag in sat.tags for tag in self.tags):
            rgb += self.modifer
        return rgb


class LaunchDateModifier(BasePixelModifier):
    def __init__(self) -> None:
        raise NotImplementedError()

    def handle(self, sat: Sat, rgb: RGB) -> RGB:
        raise NotImplementedError()
