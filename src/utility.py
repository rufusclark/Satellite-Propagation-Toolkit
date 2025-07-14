"""contains useful utilities"""
from typing import Literal, Optional

from skyfield.toposlib import GeographicPosition
from skyfield.api import utc, wgs84
from src import *
from .projectionmodels import BaseProjectionModel
from .models import Sat
import datetime
import time
import random
import string
import pathlib
import shutil
import sys


class ProgressBar:
    def __init__(self, tasks: int) -> None:
        self.tasks = tasks
        self.start_time = time.time()

    def update(self, tasks_completed: int) -> None:
        percent = tasks_completed/self.tasks
        elapsed = time.time() - self.start_time

        bar_width = 20
        filled = int(bar_width * percent)
        bar = "#" * filled + " " * (bar_width - filled)

        eta = (elapsed / tasks_completed) * (self.tasks -
                                             tasks_completed) if tasks_completed else 0

        sys.stdout.write(
            f"\r[{bar}] {percent:.2%} (eta: {datetime.timedelta(seconds=int(eta))})")
        sys.stdout.flush()

        if self.tasks == tasks_completed:
            sys.stdout.write(f"\n")
            sys.stdout.flush()


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

        # define projection model
        model = TopocentricProjectionModel.from_FoV(matrix, sats, obs, FoV)

        # define propagation times
        propagation_times = [
            start_time + datetime.timedelta(seconds=x) for x in range(int(duration.total_seconds()))
        ]

        # generate propagation data and send to device
        remote.generate_images_to_device(
            model,
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


def generate_video(
    model: BaseProjectionModel,
    modifiers: Modifiers,
    start_time: datetime.datetime,
    video_duration_secs: int,
    propogation_duration_secs: int,
    name: str = "projection_video",
    *,
    fps: int = 10,
    _background_colour: Optional[RGB] = None,
    _pixel_width_per_object: Optional[int] = None
):
    import cv2
    # TODO: Multithread the image generation
    # enforce tzinfo on the datetime
    start_time = start_time.replace(tzinfo=utc)
    vid_path = f"./images/video/{name}.mp4"
    metadata_path = f"./images/video/{name}-metadata.txt"

    total_frames = fps * video_duration_secs
    frame_interval = propogation_duration_secs / total_frames

    # create the temp directory
    dir_path = pathlib.Path(
        f"./images/temp/{''.join(random.choices(string.ascii_letters + string.digits, k=10))}")
    dir_path.mkdir(parents=True, exist_ok=True)
    print("Creating temporary working directory")

    images: list[str] = []
    sats: list[Sat] = []

    # create all the images
    print("Generating static images")
    timer = ProgressBar(total_frames)
    for i in range(total_frames):
        # propogation time
        t = ts.from_datetime(
            start_time + datetime.timedelta(seconds=i * frame_interval))

        # image file path
        images.append(str(dir_path / f"{i:06}.png"))

        # propogate, render and save image
        f = model.generate_sat_frame(t).render(modifiers)
        f.to_png(
            images[-1],
            _background_colour=_background_colour, _pixel_width_per_object=_pixel_width_per_object,
            _print=False
        )

        # save metadata
        for satPosition in f._sat_frame.sats:  # type:ignore
            sat = satPosition.sat
            if sat not in sats:
                sats.append(sat)

        timer.update(i+1)

    # generate video
    # get dimensions from the first frame
    print("Generating video")
    timer = ProgressBar(total_frames)
    f_0 = cv2.imread(images[0])
    height, width, _ = f_0.shape  # type:ignore

    # video writer
    # You can use 'XVID' or 'avc1' for compatibility
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # type:ignore
    out = cv2.VideoWriter(vid_path, fourcc, fps, (width, height))

    for i, img_name in enumerate(images):
        frame = cv2.imread(img_name)
        out.write(frame)  # type:ignore
        timer.update(i+1)

    out.release()
    print(f"Video saved to {vid_path}")

    # save the metadata to file
    with open(metadata_path, "w") as f:
        f.write(
            f"Total Sats: {len(sats)}\nFPS: {fps}\nVideo duration: {video_duration_secs}s\nPropogation duration: {propogation_duration_secs}s\nStart time: {start_time}\n")
        for sat in sats:
            f.write(f"{sat.info()}\n")
    print(f"Metadata saved to {metadata_path}")

    # delete the temp directory
    if dir_path.exists() and dir_path.is_dir():
        shutil.rmtree(dir_path)
    print("Deleted temporary working directory")
