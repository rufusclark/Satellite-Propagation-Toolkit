"""This script can be used to load data onto the Pico so it can run in untethered mode (standalone)"""
import init

from src import *
import datetime

obs = get_estimated_latlon()
"""
define the observer location from estimated ip location.

you can set your location manually with:
>>> observer = wgs84.latlon(lat, lon)
"""

dt_start = datetime.datetime.now(tz=utc)
duration = datetime.timedelta(minutes=2)
"""
define the start time of the generated images and the duration that the images should show.

please note that this should be within 2 weeks of the current date to get accurate propagation data and projections.

durations should be less than 15 minutes to prevent using all the storage space on 4MB of less based Pico devices. If you are using a device with more storage you can increase this number. Increases to the duration will linearily increase the time to generate the projection data.
"""

modifiers = [
    Modifiers(
        AlwaysPixelModifier(WHITE)
    ),
    Modifiers(
        LaunchDateModifier(
            datetime.datetime(1960, 1, 1), datetime.datetime(
                2000, 1, 1), RED
        ),
        LaunchDateModifier(
            datetime.datetime(2000, 1, 1), datetime.datetime(
                2020, 1, 1), GREEN
        ),
        LaunchDateModifier(
            datetime.datetime(2020, 1, 1), datetime.datetime(
                2040, 1, 1), BLUE
        )
    ),
    Modifiers(
        FuzzyTagPixelModifier("comm", RED),
        FuzzyTagPixelModifier(["weather", "earth"], GREEN),
        FuzzyTagPixelModifier("nav", BLUE),
        FuzzyNotTagPixelModifier(["comm", "weather", "earth", "nav"], WHITE)
    ),
    Modifiers(
        AltitudeModifier(0, 1000, RED),
        AltitudeModifier(1000, 3000, GREEN),
        AltitudeModifier(3000, 100000, BLUE)
    )
]
"""
define a set of `Modifers` objects which each represent the instruction to render an image from projected satellite positions.

each `Modifiers` objects represents a different view. These different views can be selected on the Pico device by selecting them with the devices buttons. The buttons are assigned in alphabetical order such that `modifiers[0]` corrosponds to "Button A", `modifiers[1] corropsonds to "Button B", etc.

Please note proving more `Modifiers` then buttons exist on the device will waste comupational and storage resources and will not be available to view on the Pico device.

For more information about how the modifiers work please see `analysis.py`.

contextual keys for each of the defined `Modifiers` are provided by the `Modifiers.key()` method at the end of this function which explains how all of the above `Modifiers` objects work.
"""

FoV = 90
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

remote = RemoteInterface()
"""
establish a connection to the Pico device using the `RemoteInterface` using serial repl over USB.

this interface allows the Pico device's filesytem to be directly controlled over serial.
"""

# !: Was this an issue where the hardware device was not flashed with the most recent hardware
# TODO: Hardcode the width and height of the display instead
# matrix = Matrix(*remote.get_display_dimensions())
matrix = Matrix(16, 16)
"""
define the pixel size of the matrix on the Pico device

this line retreives the dimensions of the device display from the device before defining the matrix.

occasionally this line may result in the program halting or freezing. this can be resolved be reinserting the device and running the script again.
"""

propagation_model = SGP4Propagation()
"""
define a propagation model to use

this is the method used to calculate where the satellites are"""

projection_model = TopocentricProjection.from_FoV(matrix, obs, FoV)
"""
create the topocentric projection model combining the matrix, sats, observer and FoV.

geocentric projections are also available using the `GeocentricProjectionModel` class which implements with exactly the same interface.
"""

propagation_times = [
    dt_start + datetime.timedelta(seconds=x) for x in range(int(duration.total_seconds()))
]
"""
generate a list of propagation times.

this line generates the list of propagation times based on `dt_start` and `duration` defined at the start of this script and assumes a 1 second interval for generating new frames.

please note the current client code on the Pico devices does not support differentiating between different images in milliseconds or fractions of a second and thus the smallest interval supported is 1 second.

please note this is a list of 'datetime.datetime' objects however most other methods throughout this project required a 'skyfield.Time' object instead and will otherwise throw an error. please type hints and docstrings for specific method arguments.
"""

remote.generate_images_to_device(
    sats,
    propagation_model,
    projection_model,
    modifiers,
    propagation_times
)
"""
`RemoteInterface` method that obfiscates the usual propagation, rendering and transfer proccess to send new images to Pico device.

this method uses all the supplied arguments to generated a `SatFrame` for each provided propagation frame. then an image is rendered for each provided modifer before finnaly uploading these images to the Pico device.

this method also manages the local filesystem by cleaning temporarily generated images the Pico device filesystem by removing old data that may interfere with the new data.

this method also prints contextual performance data to provide an estimated progress percentage and remaining time to the user.

it is not recommended to change the _ (underscore) arguments of this method as they may lead to unexpected side effects.
"""

print(projection_model.info(), end="")
"""
print contextual information about the model that has been generated including the matrix dimensions, FoV, origin, projection method, and angles per cell.
"""

for idx, modifier in enumerate(modifiers):
    print(f"View {idx+1} {modifier.key()}")
print("You can change views on your device by pressing the buttons on your device, see \n\thttps://github.com/rufusclark/Satellite-Propagation-Toolkit?tab=readme-ov-file#hardware-operations\nfor more details")
"""
print additional contextual information about the modifiers that have been used and a key that can be used to understand the images generated and then shown on the Pico device
"""
