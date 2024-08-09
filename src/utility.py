"""contains useful utilities"""
from skyfield.api import utc
from time import monotonic
from pathlib import Path
from typing import Literal

from skyfield.toposlib import GeographicPosition
from skyfield.api import wgs84
from .projectionmodels import BaseProjectionModel
from src import *
import datetime


class LapTimer:
    """LapTimer supports timing and counting loops
    """

    def __init__(self) -> None:
        self.n = 0
        """lap count"""
        self.t00 = 0
        """start time"""
        self.t0 = 0
        """lap start time"""
        self.d0 = 0
        """lap time"""
        self.reset()

    def reset(self) -> None:
        """reset and start the timer

        this call is redundent if `__init__` has just been called
        """
        self.n = 0
        t = monotonic()
        self.t00 = t
        self.t0 = t

    def lap(self) -> None:
        """lap the timer

        this increments the timer and saves the time of the last lap
        """
        self.n += 1
        t = monotonic()
        self.d0 = t - self.t0
        self.t0 = t

    @property
    def last(self) -> float:
        """last lap time"""
        return self.d0

    @property
    def avg(self) -> float:
        """average lap time since start"""
        return (self.t0 - self.t00)/self.n

    @property
    def rate(self) -> float:
        """average rate since start"""
        return 1/self.avg

    def info(self) -> str:
        """return a str output containing the last, avg and rate for printing

        Returns:
            formatted string ready to print
        """
        avg = (self.t0 - self.t00)/self.n
        return f"Last: {self.d0:.3f}s, Avg: {avg:.3f}s, Rate: {1/avg:.3f}/s"


def dirname(model: BaseProjectionModel) -> str:
    """function for consistent directory naming

    Args:
        matrix: Matrix object
        model: Model object

    Returns:
        formatted directory name
    """
    return f"./images/{model.name}{model.width}x{model.height}({model.x_width}x{model.y_width}deg per cell)/"


def get_estimated_latlon() -> GeographicPosition:
    """return a skyfield GeographicPosition of your estimated location using ip information

    Returns:
        GeographicPosition
    """
    import geocoder
    return wgs84.latlon(*geocoder.ip('me').latlng)


def png_to_gif(png_path: str, gif_filename: str = "./images/out.gif", duration_ms: int = 1000):
    # TODO: Proper support for generating GIF's
    import imageio.v3 as iio
    import numpy as np
    from os import listdir
    from os.path import isfile, join

    filenames = ["" for _ in range(100)]
    for f in listdir(png_path):
        if isfile(join(png_path, f)):
            filenames[int(f.strip(".png"))] = png_path + "/" + f

    # save frames from images
    frames = np.stack([iio.imread(filename) for filename in filenames])

    # generate gif
    iio.imwrite(gif_filename, frames, duration=duration_ms, loop=0)


def create_backup_images() -> None:
    """generates backup data for the next 60 seconds and sends to the device
    """
    import time
    SRC_DIR = f"images/backup{int(time.time())}"
    DST_DIR = "backup_images"

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
        # Set the colour based on satellite type
        [
            TagPixelModifier("communications", RGB(255, 0, 0)),
            TagPixelModifier("weather & earth resources", RGB(0, 255, 0)),
            TagPixelModifier("navigation", RGB(0, 0, 255))
        ],
        # Set the colour based on the satellite altitude
        [
            AltitudeModifier(0, 1000, RGB(255, 0, 0)),
            AltitudeModifier(1000, 3000, RGB(0, 255, 0)),
            AltitudeModifier(3000, 100000, RGB(0, 0, 255))
        ]
    ]

    # Change this to change the FoV of your display
    FoV = 50

    # Set start time and duration for projection
    start_time = datetime.datetime.now(tz=utc)
    duration = datetime.timedelta(seconds=60)
    end_time = start_time + duration

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

    # set time
    t_start = ts.from_datetime(start_time)
    t_end = ts.from_datetime(end_time)
    t = t_start

    timer = LapTimer()

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

    print("Generated all frames")
    print("Starting upload to device")

    # copy to remote device
    RemoteInterface().copy_file_structure(
        f"{SRC_DIR}/{width}x{height}", DST_DIR)

    print("Upload complete")


def reset_device(device: Literal["displaypack", "stellarunicorn", "unicornpack", "displaypack2.8"]) -> None:
    """regenerated filesystem structure and copy code

    does not delete any data or images but will overwrite code files"""
    remote = RemoteInterface()
    remote.put("./src/hardware/core.py", "core.py")
    remote.put(f"./src/hardware/{device}.py", "main.py")
    remote._create_dir_if_not_exist("images")
    remote._create_dir_if_not_exist("backup_images")


def factory_reset_device(device: Literal["displaypack", "stellarunicorn", "unicornpack"], generated_backup_images: bool = True) -> None:
    """delete all files and start from scratch

    should be called when setting up devices"""
    remote = RemoteInterface()
    remote.delete_dir_and_contents("")
    remote.put("./src/hardware/core.py", "core.py")
    remote.put(f"./src/hardware/{device}.py", "main.py")

    print("Source code uploaded")

    remote._create_dir_if_not_exist("images")
    remote._create_dir_if_not_exist("backup_images")
    del remote

    print("Filesystem generated")

    if generated_backup_images:
        input("Please reinsert your device and press enter to continue")
        print("Generating backup image data (this may take up to a few mins)")

        create_backup_images()

        print("\nPlease reinsert your device to complete setup")
