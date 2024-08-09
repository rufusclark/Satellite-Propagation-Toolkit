"""This script can be used to control the Pico in tethered mode (live)"""
import init

from src import *

from pathlib import Path
import time
import datetime

SRC_DIR = f"images/{int(time.time())}/"
DST_DIR = "images"

# Change this to change what information is dipslayed for satellites in the project
# Each individual modifier corrosponds to a different button on the device
modifiers = [
    # Always display as white RGB(255, 255, 255)
    [
        AlwaysPixelModifier(RGB(255, 255, 255))
    ],
    # Set the colour based on when the satellite was launched
    [
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
    ],
    # Set the colour based on satellite type and brightness based on number of satellites
    [
        TagPixelModifier("communications", RGB(100, 0, 0)),
        TagPixelModifier("weather & earth resources", RGB(0, 100, 0)),
        TagPixelModifier("navigation", RGB(0, 0, 100))
    ],
    # Set the colour based on the satellite altitude and brightness based on number of satellites
    [
        AltitudeModifier(0, 1000, RGB(100, 0, 0)),
        AltitudeModifier(1000, 3000, RGB(0, 100, 0)),
        AltitudeModifier(3000, 100000, RGB(0, 0, 100))
    ]
]

# Change this to change the FoV of your display
FoV = 50

# Change to change the start and end time
# Please note that this should be within 2 weeks of the current date to get accurate projections
dt_start = datetime.datetime(2024, 8, 6, tzinfo=utc)
duration = datetime.timedelta(seconds=10)
dt_end = dt_start + duration

# set observer location
obs = get_estimated_latlon()

# load all sats
sats = init_sats()

# get width and height of display
width, height = LiveInterface().get_display_dimensions()

# define matrix
matrix = Matrix(width, height)

# define projection model
model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, FoV)

# create file structure to save images
print("Generating file system for generated images")
for path in [f"{SRC_DIR}/{width}x{height}/{idx}" for idx, _ in enumerate(modifiers)]:
    Path(path).mkdir(parents=True, exist_ok=True)

print("Generating projection images for device")

timer = LapTimer()

# convert datetime to skyfield time scale
t_start = ts.from_datetime(dt_start)
t_end = ts.from_datetime(dt_end)
t = t_start

try:
    while t < t_end:
        # propogate sat positions
        sat_frame = model.generate_sat_frame(t)

        # generate image frame for each modifier and save
        for idx, modifer in enumerate(modifiers):
            path = f"{SRC_DIR}/{width}x{height}/{idx}/{sat_frame.unix_timestamp_seconds}.png"
            frame = sat_frame.render(modifer)
            frame.to_png(path)

        # increment propogation time
        t += datetime.timedelta(seconds=1)

        timer.lap()
        print(timer.info() + " "*20, end="\r")
except KeyboardInterrupt:
    print("\nProccess stopped")

print("Generated all frames")
print("Starting upload to device")

# copy to remote device
device = RemoteInterface().copy_file_structure(
    f"{SRC_DIR}/{width}x{height}", DST_DIR)

print("Upload complete")
