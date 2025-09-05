"""quickstart file for creating output videos, images, gifs and reports

all methods in this example have extensive parameters to alter the outputs

see `quickstart.py` for internal workings and how to extend code alongside self-documenting docstrings"""

import init
from src import *
from datetime import timedelta

manager = Manager()
"""generates a new manager object which loads all active satellites"""

manager.generate_report()
"""generate a pdf report from all the satellites from the projected view.

this report contains an overview of everything in the view, details on all satellites and the output image itself"""


manager.generate_image(
    FoV=400,
    observer=wgs84.latlon(0, 0),
    matrix=Matrix(640, 640),
)
"""generates a image using default arguments which has default fields.

this has been customised as a resolution of 640x640 pixels showing all satellites with a 400deg field of view from a latitude and longitude of (0, 0)"""

manager.generate_gif()
"""generates a gif using all default arguments

this uses an identical API to `Manager.generate_video()` for compatibility"""


manager.generate_video(
    video_duration=60,
    video_fps=1,
    propagation_time_interval=timedelta(seconds=1)
)
"""generates a minute long video (with 1 fps) and runs in realtime using the default fields"""

manager.plot_orbital_overview()
"""plot an interactive popup showing an overview of all satellites at a given time"""
