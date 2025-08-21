"""This script can be used to control the Pico in tethered mode (live)"""
import init

from src import *
from datetime import datetime

observer = get_estimated_latlon()
"""
define the observer location from estimated ip location.

you can set your location manually with:
>>> observer = wgs84.latlon(lat, lon)
"""

modifier = Modifiers(
    LaunchDateModifier(
        datetime(1960, 1, 1), datetime(2000, 1, 1), RGB(255, 0, 0)
    ),
    LaunchDateModifier(
        datetime(2000, 1, 1), datetime(2020, 1, 1), RGB(0, 255, 0)
    ),
    LaunchDateModifier(
        datetime(2020, 1, 1), datetime(2040, 1, 1), RGB(0, 0, 255)
    )
)
"""
define modifier to render image with.

if the modifier is satisfied the pixel value of the corrosponding sat is added to the supplied RGB value.

this can be a list of any objects that inherit BasePixelModifier, see `analysis.py` for all available or define your own.
"""

FoV = 50
"""
set the field of view of the projection.

this FoV is the effective field of view of your image if your projection was circle to account for the variable FoV of your rectangular projection.
"""

sats = init_sats()
"""
load all sats from memory, clean data and combine datasets.

if no data is cached or the cache has expired new data will downloaded.

greater control of data being imported is available, see `datasources.py` and `init_sats` for details.
"""

device = LiveInterface()
"""
establish a connection to the Pico device using the `LiveInterface` using serial over USB.
"""

matrix = Matrix(*device.get_display_dimensions())
"""
define the pixel size of the matrix on the Pico device

this line retreives the dimensions of the device display from the device before defining the matrix.

occasionally this line may result in the program halting or freezing. this can be resolved be reinserting the device and running the script again.
"""

propagation_model = SGP4Propagation()
"""
define a propagation model to use

this is the method used to calculate where the satellites are"""

projection_model = TopocentricProjection.from_FoV(matrix, observer, FoV)
"""
create the topocentric projection model combining the matrix, sats, observer and FoV.

geocentric projections are also available using the `GeocentricProjectionModel` class which implements with exactly the same interface.
"""
print("Starting live update to device")

timer = LapTimer()
"""
initiate a timer object to record execution information about the propagation and give context to the user
"""

try:
    while True:
        t = ts.now()
        """
        set the propagation time to the current time.
        """

        orbital_positions = propagation_model.propagate(sats, t)
        """propagate satellites"""

        frame = projection_model.project(orbital_positions).render(modifier)
        """
        generate an image from the propagated sat locations using the supplied modifier.

        this line can be broken down into 2 functions the first returns a `SatFrame` containing the location of all sats that fall within its bounds as defined by the model. The second of these then creates an `ImageFrame` by rendering this `SatFrame` with the `Modifier` object.
        """

        device.update_display(frame)
        """
        update the display of the Pico device with the new `ImageFrame`.

        this method uses the `LiveInterface` to send a series of instructions to the Pico device to change only the pixels that are different between this frame and the last frame sent. this effecient transfer mechanism minimises the time required to upadte the display on the device.
        """

        timer.lap()
        print(f"{timer.info():<80}", end="\r")
        """
        timing code to measure the time to generate 1 frame and then print contextual performance information
        """

except KeyboardInterrupt:
    print("\nStopping live update to device")
