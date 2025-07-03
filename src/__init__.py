# TODO: Write documentation
from sys import version_info
if version_info[0] != 3 or version_info[1] < 9:
    raise RuntimeWarning(
        "\n\nThis package has been designed to support python version 3.9+,\nplease install python version 3.9 or higher to run this package\n")

from skyfield.api import wgs84, utc

from .models import ts, Orbits
from .datasources import NORAD, SATCAT, init_sats
from .matrix import Matrix, ImageFrame
from .rgb import RGB, BLACK
from .analysis import AlwaysPixelModifier, LaunchDateModifier, TagPixelModifier, NotTagPixelMofidier, AltitudeModifier, DistanceModifier, Modifiers
from .device import *
from .projectionmodels import TopocentricProjectionModel, GeocentricProjectionModel
from .progress import LapTimer
from .utility import get_estimated_latlon, factory_reset_device, reset_device
