"""This script can be used to control the Pico in tethered mode (live)"""
from src import *

from time import monotonic
from datetime import datetime

# Change this to change what information is dipslayed for satellites in the project
modifier = [
    LaunchDateModifier(
        datetime(1960, 1, 1), datetime(2000, 1, 1), RGB(255, 0, 0)
    ),
    LaunchDateModifier(
        datetime(2000, 1, 1), datetime(2020, 1, 1), RGB(0, 255, 0)
    ),
    LaunchDateModifier(
        datetime(2020, 1, 1), datetime(2040, 1, 1), RGB(0, 0, 255)
    )
]

# Change this to change the FoV of your display
FoV = 50

# set observer location
obs = get_estimated_latlon()

# load all sats
sats = init_sats()

# connect to device and init
device = LiveInterface()

# define matrix
matrix = Matrix(*device.get_display_dimensions())

# define projection model
model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, FoV)

print("Starting live update to device")

timer = LapTimer()

try:
    while True:
        # time of propogation
        t = ts.now()

        # generate image frame
        frame = model.generate_sat_frame(t).render(modifier)

        # send to device
        device.update_display(frame)

        timer.lap()
        print(timer.info() + ''*20, end="/r")

except KeyboardInterrupt:
    print("\nStopping live update to device")
