"""This script can be used to load data onto the Pico so it can run in untethered mode (standalone)"""
import init

from src import *
import datetime

# Change this to change what information is dipslayed for satellites in the project
# Each individual modifier corrosponds to a different button on the device
modifiers = [
    # Always display as white RGB(255, 255, 255)
    Modifiers(
        AlwaysPixelModifier(RGB(255, 255, 255))
    ),
    # Set the colour based on when the satellite was launched
    Modifiers(
        LaunchDateModifier(
            datetime.datetime(1960, 1, 1), datetime.datetime(
                2000, 1, 1), RGB(255, 0, 0)
        ),
        LaunchDateModifier(
            datetime.datetime(2000, 1, 1), datetime.datetime(
                2020, 1, 1), RGB(0, 255, 0)
        ),
        LaunchDateModifier(
            datetime.datetime(2020, 1, 1), datetime.datetime(
                2040, 1, 1), RGB(0, 0, 255)
        )
    ),
    # Set the colour based on satellite type and brightness based on number of satellites
    Modifiers(
        TagPixelModifier("communications", RGB(100, 0, 0)),
        TagPixelModifier("weather & earth resources", RGB(0, 100, 0)),
        TagPixelModifier("navigation", RGB(0, 0, 100))
    ),
    # Set the colour based on the satellite altitude and brightness based on number of satellites
    Modifiers(
        AltitudeModifier(0, 1000, RGB(100, 0, 0)),
        AltitudeModifier(1000, 3000, RGB(0, 100, 0)),
        AltitudeModifier(3000, 100000, RGB(0, 0, 100))
    )
]

# Change this to change the FoV of your display
FoV = 50

# Change to change the start and end time
# Please note that this should be within 2 weeks of the current date to get accurate projections
dt_start = datetime.datetime(2024, 8, 6, tzinfo=utc)
duration = datetime.timedelta(seconds=10)

# set observer location
obs = get_estimated_latlon()

# load all sats
sats = init_sats()

# connect to remote device
remote = RemoteInterface()

# define matrix
matrix = Matrix(*remote.get_display_dimensions())

# define projection model
model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, FoV)

# define propagation times
propagation_times = [
    dt_start + datetime.timedelta(seconds=x) for x in range(int(duration.total_seconds()))
]

# generate propagation data and send to device
remote.generate_images_to_device(model, modifiers, propagation_times)

# print description of model
print(model.info(), end="")

# print view for each view
for idx, modifier in enumerate(modifiers):
    print(f"View {idx+1} {modifier.key()}")
print("You can change views on your device by pressing the buttons on your device, see \n\thttps://github.com/rufusclark/Satellite-Propagation-Toolkit?tab=readme-ov-file#hardware-operations\nfor more details")
