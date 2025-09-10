# TODO: Write documentation
from sys import version_info
if version_info[0] != 3 or version_info[1] < 9:
    raise RuntimeWarning(
        "\n\nThis package has been designed to support python version 3.9+,\nplease install python version 3.9 or higher to run this package\n")

from skyfield.api import wgs84, utc

from .models import ts, Orbits, Satellite, SatelliteSet
from .datasources import NORAD, SATCAT, init_sats
from .matrix import Matrix, ImageFrame
from .rgb import *
from .analysis import AlwaysPixelModifier, LaunchDateModifier, TagPixelModifier, NotTagPixelMofidier, AltitudeModifier, DistanceModifier, Modifiers, FuzzyTagPixelModifier, FuzzyNotTagPixelModifier, CustomPixelModifier
from .device import *
from .projection import TopocentricProjection, GeocentricProjection
from .progress import LapTimer
from .utility import get_estimated_latlon, factory_reset_device, reset_device
from .propagation import SGP4Propagation, KeplerianPropagation, CubicInterpolation, HybridPropagation, BasePropagation, OrbitalPosition
from .chart import plot_interpolation_analysis, plot_on_Earth, plot_orbital_overview
from .manager import Manager
from .future import MOCATReader
from .report import dict_to_pdf
