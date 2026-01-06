"""contains useful utilities"""
from typing import Literal

from skyfield.toposlib import GeographicPosition
from skyfield.api import utc, wgs84, Time
from src import *
import datetime
import time
import traceback
import sys
from functools import lru_cache

ACCEPTABLE_TIME_TYPES = Time | datetime.datetime | list[datetime.datetime]


def accept_any_datetime(t: ACCEPTABLE_TIME_TYPES) -> Time:
    """utility function to convert datetime to `skyfield` time zone aware `Time` object"""
    match t:
        case Time():
            return t
        case datetime.datetime():
            if t.tzinfo is None:
                t = t.replace(tzinfo=utc)
            return ts.from_datetime(t)
        case [datetime.datetime() as first, *rest]:
            new_t = [None for _ in range(len(t))]  # type: ignore
            for i, item in enumerate(t):
                new_t[i] = item.replace(  # type: ignore
                    tzinfo=utc) if item.tzinfo is None else item
            return ts.from_datetimes(new_t)
        case _:
            raise TypeError(
                f"t is not a valid type. provided: {type(t)}, valid types: {ACCEPTABLE_TIME_TYPES}")

    # if t.tzinfo is None:
    #     t = t.replace(tzinfo=utc)
    # return ts.from_datetime(t)


class ProgressBar:
    def __init__(self, tasks: int) -> None:
        self.tasks = tasks
        self.start_time = time.time()
        self.update(0)

    def update(self, tasks_completed: int) -> None:
        percent = tasks_completed/self.tasks
        elapsed = time.time() - self.start_time

        bar_width = 20
        filled = int(bar_width * percent)
        bar = "#" * filled + " " * (bar_width - filled)

        remaining = (elapsed / tasks_completed) * (
            self.tasks - tasks_completed) if tasks_completed else 0

        sys.stdout.write(
            f"\r[{bar}] {percent:.2%} (eta: {datetime.timedelta(seconds=int(remaining))})")
        sys.stdout.flush()

        if self.tasks == tasks_completed:
            sys.stdout.write(f"\n")
            sys.stdout.flush()


@lru_cache(maxsize=1)
def get_estimated_latlon() -> GeographicPosition:
    """return a skyfield GeographicPosition of your estimated location using ip information

    Returns:
        GeographicPosition
    """
    try:
        import geocoder
        return wgs84.latlon(*geocoder.ip('me').latlng)
    except Exception as e:
        print("Could not get location from ip, defaulting to 0,0")
        traceback.print_tb(e.__traceback__)
        print("Continuing...")
        return wgs84.latlon(0, 0)


SUPPORTED_DEVICES = Literal[
    "displaypack", "stellarunicorn", "unicornpack", "displaypack2.8"
]


def reset_device(device: SUPPORTED_DEVICES) -> None:
    """regenerated filesystem structure and copy code

    does not delete any data or images but will overwrite code files"""
    remote = RemoteInterface()
    remote.put("./src/hardware/core.py", "core.py")
    remote.put(f"./src/hardware/{device}.py", "main.py")
    remote._create_dir_if_not_exist("images")
    remote._create_dir_if_not_exist("backup_images")


def factory_reset_device(device: SUPPORTED_DEVICES, _generate_backup_images: bool = True) -> None:
    """delete all files and start from scratch

    should be called when setting up devices"""
    remote = RemoteInterface()
    remote.delete_dir_and_contents("")
    remote.put("./src/hardware/core.py", "core.py")
    remote.put(f"./src/hardware/{device}.py", "main.py")

    print("Source code uploaded")

    remote._create_dir_if_not_exist("images")
    remote._create_dir_if_not_exist("backup_images")
    print("Filesystem generated")
    del remote

    print("Device restarted")

    if _generate_backup_images:
        print("Generating backup image data (this may take up to a few mins)")

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
                FuzzyNotTagPixelModifier(
                    ["comm", "weather", "earth", "nav"], WHITE)
            ),
            Modifiers(
                AltitudeModifier(0, 1000, RED),
                AltitudeModifier(1000, 3000, GREEN),
                AltitudeModifier(3000, 100000, BLUE)
            )
        ]

        # Change this to change the FoV of your display
        FoV = 50

        # Set start time and duration for projection
        start_time = datetime.datetime.now(tz=utc)
        duration = datetime.timedelta(minutes=1)

        # set observer location
        obs = get_estimated_latlon()

        print("Loading tracking data")

        # load all sats
        sats = init_sats()

        # connect to remote device
        remote = RemoteInterface()

        # get width and height of display
        width, height = remote.get_display_dimensions()

        # define matrix
        matrix = Matrix(width, height)

        propagation_model = SGP4Propagation()
        # define propagation model

        # define projection model
        propjection_model = TopocentricProjection.from_FoV(matrix, obs, FoV)

        # define propagation times
        propagation_times = [
            start_time + datetime.timedelta(seconds=x) for x in range(int(duration.total_seconds()))
        ]

        # generate propagation data and send to device
        remote.generate_images_to_device(
            sats,
            propagation_model,
            propjection_model,
            modifiers,
            propagation_times,
            _backup=True
        )

        del remote

        # print view for each view
        for idx, modifier in enumerate(modifiers):
            print(f"View {idx+1} {modifier.key()}")
        print("You can change views on your device by pressing the buttons on your device, see \n\thttps://github.com/rufusclark/Satellite-Propagation-Toolkit?tab=readme-ov-file#hardware-operations\nfor more details")

    print("Please reinsert your device to complete setup")
