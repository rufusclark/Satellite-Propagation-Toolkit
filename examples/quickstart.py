"""quickstart script for generating an image of the current satellites above your heads"""

import init
from src import *

# observer = wgs84.latlon(0, 0)
observer = get_estimated_latlon()
"""
define the observer location from estimated ip location.

you can set your location manually with:
>>> observer = wgs84.latlon(lat, lon)
"""

# modifier = Modifiers(AlwaysPixelModifier(RGB(255, 255, 255)))  # All white
modifier = Modifiers(
    CustomPixelModifier(  # Geostationary Satellites - Solid White
        WHITE, "Geostationary",
        lambda x: (
            x.orbital_position.is_geo()
            # and x.orbital_position.is_above_horizon(obs_mecd)
        )
    ),
    CustomPixelModifier(  # Visible Satellites (from observer) - Grey
        WHITE*0.35, "Visible",
        lambda x: (
            x.orbital_position.is_above_horizon(observer)
            and not x.orbital_position.is_geo()
        )
    ),
    CustomPixelModifier(  # All other Satellites - Faint Grey
        WHITE*0.075, "Remaining",
        lambda x: (
            not x.orbital_position.is_above_horizon(observer)
            and not x.orbital_position.is_geo()
        )
    )
)
"""
define modifier to render image with.

if the modifier is satisfied the pixel value of the corresponding sat is added to the supplied RGB value.

this can be a list of any objects that inherit BasePixelModifier, see `analysis.py` for all available or define your own.
"""

FoV = 400
"""
set the field of view of the projection.

this FoV is the effective field of view of your image if your projection was circle to account for the variable FoV of your rectangular projection.
"""

t = ts.now()
"""
set the propagation time to the current time.

please note propagations more than 2 weeks from the last satellite track are inaccurate due to the instantaneous nature of radar tracking

this can be set manually as follows:
>>> import datetime
>>> dt = datetime.datetime(2024, 8, 7, 10, 13, 1, tzinfo=utc)
>>> t = ts.from_datetime(dt)
"""

sats = init_sats()
"""
load all sats from memory, clean data and combine datasets.

if no data is cached or the cache has expired new data will downloaded.

greater control of data being imported is available, see `datasources.py` and `init_sats` for details.
"""

# years = 50
# MOCAT_data = MOCATReader(
#     "./data/MOCAT/results_Su_predict_launch_mega_2025.csv")
# sats = MOCAT_data.read_yrs(years).to_SatelliteSet(sats)
"""
uncomment this section to use create a new selection of satellites based on the current distribution of satellites and MOCAT (https://github.com/ARCLab-MIT/MOCAT-SSEM) future capacity data.

this future satellite model assumes all planned mega constellations (Starlink, Leo, etc) are launched inline with public plans.

please note that MOCAT only predicts the number of satellites below 2000km.

values in years between 0 and 100 are allowed
"""

sats.print_all_categories()
# sats.print_all_tags()
"""
print a list of all tags in the satellite dataset with the number of occurrences
"""

matrix = Matrix(800, 800)
"""
define the pixel size of your matrix.

this may be either the size of your image output or your LED display if this is being sent to an external device.
"""

propagation_model = SGP4Propagation()
"""
define a propagation model to use

this is the method used to calculate where the satellites are"""

orbital_positions = propagation_model.propagate(sats, t)
"""
calculate the satellite positions using the defined satellite model, provided `SatelliteSet` and `Time`
"""

model = TopocentricProjection.from_FoV(matrix, observer, FoV)
# model = GeocentricProjectionModel.from_FoV(matrix, observer, FoV)
"""
define a topocentric projection model combining the matrix, observer and FoV.

geocentric projections are also available using the `GeocentricProjectionModel` class which implements with exactly the same interface.
"""

sat_frame = model.project(orbital_positions)
"""
project the orbital position data for the satellites onto a 2D frame using the above model.
"""

image_frame = sat_frame.render(modifier)
"""
render the sat frame with the modifiers defined above to create an `ImageFrame` (2D matrix with pixel values).

this `ImageFrame` can be saved or sent to an external device.
"""

print(image_frame.key_info())
"""
print contextual information about the `ImageFrame` that has been generated including the satellites that are included within the frame.
"""

image_frame.to_png("quickstart.png", _pixel_width_per_object=3)
"""
save the `ImageFrame` as a png file as "quickstart.png" 
"""
