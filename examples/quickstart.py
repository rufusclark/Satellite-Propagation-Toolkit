"""quickstart script for generating an image of the current satellites above your heads"""
import init

from src import *


observer = get_estimated_latlon()
"""
define the observer location from estimated ip location.

you can set your location manually with:
>>> observer = wgs84.latlon(lat, lon)
"""

modifiers = [
    AlwaysPixelModifier(RGB(255, 255, 255))
]
"""
define modifiers to render image with.

if the modifier is satisfied the pixel value of the corrosponding sat is added to the supplied RGB value.

this can be a list of any objects that inherit BasePixelModifier, see `analysis.py` for all available or define your own.
"""

FoV = 120
"""
set the field of view of the projection.

this FoV is the effective field of view of your image if your projection was circle to account for the variable FoV of your rectangular projection.
"""

t = ts.now()
"""
set the propagation time.

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

matrix = Matrix(128, 128)
"""
define the pixel size of your matrix.

this may be either the size of your image output or your LED display if this is being sent to an external device.
"""

model = TopocentricProjectionModel.from_FoV(matrix, sats, observer, FoV)
"""
create the topocentric projection model combining the matrix, sats, observer and FoV.

geocentric projections are also available using the `GeocentricProjectionModel` class which implements with exactly the same interface.
"""

sat_frame = model.generate_sat_frame(t)
"""
propogate all the sats and generate a `SatFrame` (2D matrix containing all sats that fall within it's bounds after being projected).
"""

image_frame = sat_frame.render(modifiers)
"""
render the sat frame with the modifiers defined above to create an `ImageFrame` (2D matrix with pixel values).

this `ImageFrame` can be saved or sent to an external device.
"""

print(image_frame.info())
"""
print contextual information about the `ImageFrame` that has been generated including the satellites that are included within the frame.
"""

image_frame.to_png("quickstart.png")
"""
save the `ImageFrame` as a png file as "quickstart.png" 
"""
