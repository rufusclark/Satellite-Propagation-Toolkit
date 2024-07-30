"""contains useful utilities"""
from skyfield.toposlib import GeographicPosition
from skyfield.api import wgs84
from .projectionmodels import BaseProjectionModel


def dirname(model: BaseProjectionModel) -> str:
    """function for consistent directory naming

    Args:
        matrix: Matrix object
        model: Model object

    Returns:
        formatted directory name
    """
    return f"./images/{model.name}{model.width}x{model.height}({model.x_width}x{model.y_width}deg per cell)/"


def get_estimated_latlon() -> GeographicPosition:
    """return a skyfield GeographicPosition of your estimated location using ip information

    Returns:
        GeographicPosition
    """
    import geocoder
    return wgs84.latlon(*geocoder.ip('me').latlng)
