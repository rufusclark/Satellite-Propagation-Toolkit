"""contains useful utilities"""
from typing import Literal

from skyfield.toposlib import GeographicPosition
from skyfield.api import utc, wgs84
from src import *
import datetime


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


def reset_device(device: Literal["displaypack", "stellarunicorn", "unicornpack", "displaypack2.8"]) -> None:
    """regenerated filesystem structure and copy code

    does not delete any data or images but will overwrite code files"""
    remote = RemoteInterface()
    remote.put("./src/hardware/core.py", "core.py")
    remote.put(f"./src/hardware/{device}.py", "main.py")
    remote._create_dir_if_not_exist("images")
    remote._create_dir_if_not_exist("backup_images")


def factory_reset_device(device: Literal["displaypack", "stellarunicorn", "unicornpack"], _generate_backup_images: bool = True) -> None:
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
                # Always display as white RGB(255, 255, 255)
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
            # Set the colour based on satellite type
            Modifiers(
                TagPixelModifier("communications", RGB(255, 0, 0)),
                TagPixelModifier("weather & earth resources", RGB(0, 255, 0)),
                TagPixelModifier("navigation", RGB(0, 0, 255))
            ),
            # Set the colour based on the satellite altitude
            Modifiers(
                AltitudeModifier(0, 1000, RGB(255, 0, 0)),
                AltitudeModifier(1000, 3000, RGB(0, 255, 0)),
                AltitudeModifier(3000, 100000, RGB(0, 0, 255))
            )
        ]

        # Change this to change the FoV of your display
        FoV = 50

        # Set start time and duration for projection
        start_time = datetime.datetime.now(tz=utc)
        # duration = datetime.timedelta(minutes=1)

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

        # define projection model
        model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, FoV)

        # define propagation times
        propagation_times = [
            start_time + datetime.timedelta(seconds=x) for x in range(60)
        ]

        # generate propagation data and send to device
        remote.generate_images_to_device(
            model,
            modifiers,
            propagation_times,
            _backup=True
        )

        # print view for each view
        for idx, modifier in enumerate(modifiers):
            print(f"View {idx+1} {modifier.key()}")
        print("You can change views on your device by pressing the buttons on your device, see \n\thttps://github.com/rufusclark/Satellite-Propagation-Toolkit?tab=readme-ov-file#hardware-operations\nfor more details")

    del remote

    print("Please reinsert your device to complete setup")
