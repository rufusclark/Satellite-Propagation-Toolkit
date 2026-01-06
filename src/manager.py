"""manager is a object for managing the entire output generation process to images, videos, gifs and more whilst obfuscating the complexity away"""

from datetime import timedelta
from pathlib import Path
from shutil import rmtree
from random import choices
from string import ascii_letters, digits
from typing import Optional

from skyfield.toposlib import GeographicPosition
from skyfield.api import Time

from .rgb import RGB
from .models import ts, SatelliteSet
from .matrix import Matrix, ImageFrame
from .datasources import init_sats
from .utility import get_estimated_latlon
from .propagation import BasePropagation, SGP4Propagation,  CubicInterpolation
from .projection import BaseProjection, GeocentricProjection, TopocentricProjection
from .analysis import Modifiers, AlwaysPixelModifier
from .utility import ProgressBar
from .chart import plot_orbital_overview
from .report import dict_to_pdf
from src import WHITE, BLACK

import numpy as np


class Manager:
    """Manager is an object that assists with generating outputs from the NORAD and SATCAT datasets using helpful methods with sensible default options

    generate_XXXXX methods provide simplified access to variables and include sensible defaults
    generate_XXXXX_core methods provide direct access to all variables
    """

    def _handle_observer_input(self, observer: Optional[GeographicPosition]) -> GeographicPosition:
        if observer is None:
            return get_estimated_latlon()
        else:
            return observer

    def __init__(
        self,
        sats: Optional[SatelliteSet] = None
    ) -> None:
        """create a new generator object.

        provide your own processed `SatelliteSet` object or leave it blank to use all available satellites as default

        Args:
            sats: `SatelliteSet` to use. Defaults to init_sats().
        """
        if sats:
            self.sats = sats
        else:
            self.sats = init_sats()

    def generate_image(
        self,
        observer: Optional[GeographicPosition] = None,
        FoV: float = 120,
        time: Time = ts.now(),
        propagation_model: BasePropagation = SGP4Propagation(),
        matrix: Matrix = Matrix(128, 128),
        projection_model_class: type[BaseProjection] = TopocentricProjection,
        modifiers: Modifiers = Modifiers(AlwaysPixelModifier(WHITE)),
        filename: str = "./images/out.png",
        *,
        background_colour: RGB = BLACK,
        pixel_width_per_object: int = 1
    ) -> None:
        """generate image generates a single images based on the following parameters.

        this methods uses sensible defaults so you only need to change the minimum amount of parameters for your desired output rather than configuring everything.

        Args:
            observer: `GeographicPosition` of the observer. Defaults to get_estimated_latlon() (estimate your current location based on your ip address).
            FoV: field of view of the observer [degrees]. Defaults to 120.
            time: propagation time (time for position of satellites). Defaults to ts.now() (the current time).
            propagation_model: `BasePropagation` object that is the internal method for coming up with the satellite positions. Defaults to SGP4Propagation().
            matrix: `Matrix` is the 2d frame used for projections with a defined size. Defaults to Matrix(128, 128).
            projection_model_class: `BaseProjection` is the projection model used to generate the image. This is either `GeocentricProjection` or `TopocentricProjection` Defaults to TopocentricProjection.
            modifiers: `Modifiers` highlight information with different colours in the output image. Defaults to Modifiers(AlwaysPixelModifier(WHITE)) (all satellites are white).
            filename: relative location and filename of the image. Defaults to "images/out.png".
            background_colour: `RGB` background colour of the image. Defaults to BLACK.
            pixel_width_per_object: the number of pixels per satellite (only odd numbers are supported). Defaults to 1.
        """
        self.generate_image_core(
            propagation_model=propagation_model,
            projection_model=projection_model_class.from_FoV(
                matrix=matrix,
                observer=self._handle_observer_input(observer),
                FoV=FoV
            ),
            modifiers=modifiers,
            time=time,
            filename=filename,
            background_colour=background_colour,
            pixel_width_per_object=pixel_width_per_object
        )

    def generate_image_core(
            self,
            propagation_model: BasePropagation,
            projection_model: BaseProjection,
            modifiers: Modifiers,
            time: Time,
            filename: str,
            *,
            background_colour: RGB = BLACK,
            pixel_width_per_object: int = 1,
            _print: bool = True
    ) -> ImageFrame:
        """helper method to generate a single image with the following parameters

        Args:
            propagation_model: propagation model to use
            projection_model: projection model to use (created with a matrix, observer and FoV or cell_width)
            modifiers: modifiers to highlight information with different colours in the output image
            time: propagation time (for satellite positions)
            filename: output filename
            background_colour: background colour of 'empty' pixels. Defaults to BLACK.
            pixel_width_per_object: the number of pixels per satellite (only odd numbers are supported). Defaults to 1.
        """
        # propagate satellite positions
        orbital_positions = propagation_model.propagate(self.sats, time)

        # project satellite positions onto a 2d plane
        sat_frame = projection_model.project(orbital_positions)

        # render key and highlight information onto a 2d image (internal)
        image_frame = sat_frame.render(modifiers)

        # convert the internal image to a png image
        image_frame.to_png(
            filename,
            _background_colour=background_colour,
            _pixel_width_per_object=pixel_width_per_object,
            _print=_print
        )

        return image_frame

    def generate_images_core(
        self,
        propagation_model: BasePropagation,
        projection_model: BaseProjection,
        modifiers: Modifiers,
        image_start_time: Time,
        image_time_interval: timedelta,
        number_of_images: int,
        path: str,
        *,
        background_colour: RGB = BLACK,
        pixel_width_per_object: int = 1,
    ) -> tuple[list[str], list[ImageFrame]]:

        image_paths: list[str] = []
        image_frames: list[ImageFrame] = []

        # generate output directory
        self._create_working_directory(path)
        dir_path = Path(path)

        # create all images
        print("Generating static images")
        timer = ProgressBar(number_of_images)
        for i in range(number_of_images):
            # propogation time
            time = image_start_time + i*image_time_interval

            # image file path
            image_paths.append(str(dir_path / f"{i:08}.png"))

            # propogate, render and save image
            image_frames.append(self.generate_image_core(
                propagation_model=propagation_model,
                projection_model=projection_model,
                modifiers=modifiers,
                time=time,
                filename=image_paths[-1],
                background_colour=background_colour,
                pixel_width_per_object=pixel_width_per_object,
                _print=False,
            ))

            timer.update(i+1)

        return image_paths, image_frames

    def generate_video_core(
        self,
        propagation_model: BasePropagation,
        projection_model: BaseProjection,
        modifiers: Modifiers,
        propagation_start_time: Time,
        propagation_time_interval: timedelta,
        video_fps: int,  # secs
        video_duration: int,
        video_path: str,
        *,
        background_colour: RGB = BLACK,
        pixel_width_per_object: int = 1,
    ) -> None:
        # TODO: Add docstring
        temp_dir = f"./images/temp/{''.join(choices(ascii_letters + digits, k=10))}"

        # generate images
        image_paths, _ = self.generate_images_core(
            propagation_model=propagation_model,
            projection_model=projection_model,
            modifiers=modifiers,
            image_start_time=propagation_start_time,
            image_time_interval=propagation_time_interval,
            number_of_images=video_fps * video_duration,
            path=temp_dir,
            background_colour=background_colour,
            pixel_width_per_object=pixel_width_per_object
        )

        # generate video
        self._generate_video_core(
            image_paths=image_paths,
            video_path=video_path,
            fps=video_fps
        )

        # remove temp dir
        self._remove_working_directoey(temp_dir)

    def generate_video(
        self,
        observer: Optional[GeographicPosition] = None,
        FoV: float = 120,
        propagation_start_time: Time = ts.now(),
        propagation_time_interval: timedelta = timedelta(milliseconds=100),
        video_fps: int = 10,
        video_duration: int = 60,
        propagation_model: BasePropagation = SGP4Propagation(),
        matrix: Matrix = Matrix(128, 128),
        projection_model_class: type[BaseProjection] = GeocentricProjection,
        modifiers: Modifiers = Modifiers(AlwaysPixelModifier(WHITE)),
        filename: str = "./images/out.mp4",
        *,
        background_colour: RGB = BLACK,
        pixel_width_per_object: int = 1
    ) -> None:
        # TODO: Write a docstring
        self.generate_video_core(
            propagation_model=propagation_model,
            projection_model=projection_model_class.from_FoV(
                matrix=matrix,
                observer=self._handle_observer_input(observer),
                FoV=FoV
            ),
            modifiers=modifiers,
            propagation_start_time=propagation_start_time,
            propagation_time_interval=propagation_time_interval,
            video_fps=video_fps,
            video_duration=video_duration,
            video_path=filename,
            background_colour=background_colour,
            pixel_width_per_object=pixel_width_per_object
        )

    def generate_report_core(
        self,
        propagation_model: BasePropagation,
        projection_model: BaseProjection,
        modifiers: Modifiers,
        time: Time,
        report_path: str,
    ) -> None:
        self._generate_report_core(
            image_frame=projection_model.project(
                propagation_model.propagate(self.sats, time)
            ).render(modifiers),
            report_path=report_path
        )

    def generate_report(
        self,
        observer: Optional[GeographicPosition] = None,
        FoV: float = 120,
        time: Time = ts.now(),
        propagation_model: BasePropagation = SGP4Propagation(),
        matrix: Matrix = Matrix(128, 128),
        projection_model_class: type[BaseProjection] = TopocentricProjection,
        modifiers: Modifiers = Modifiers(AlwaysPixelModifier(WHITE)),
        filename: str = "./images/out.pdf",
    ) -> None:
        """helper method to generate a pdf report from the provided projection.

        this report contains the generated images, details about all the satellites in the frame, an overview of all satellites in the frame and more.

        this will take a while for frames that include more than a few hundred satellites.

        Args:
            observer: `GeographicPosition` of the observer. Defaults to get_estimated_latlon() (estimate your current location based on your ip address).
            FoV: field of view of the observer [degrees]. Defaults to 120.
            time: propagation time (time for position of satellites). Defaults to ts.now() (the current time).
            propagation_model: `BasePropagation` object that is the internal method for coming up with the satellite positions. Defaults to SGP4Propagation().
            matrix: `Matrix` is the 2d frame used for projections with a defined size. Defaults to Matrix(128, 128).
            projection_model_class: `BaseProjection` is the projection model used to generate the image. This is either `GeocentricProjection` or `TopocentricProjection` Defaults to TopocentricProjection.
            modifiers: `Modifiers` highlight information with different colours in the output image. Defaults to Modifiers(AlwaysPixelModifier(WHITE)) (all satellites are white).
            filename: relative location and filename of the image. Defaults to "images/out.png".
        """
        self.generate_report_core(
            propagation_model=propagation_model,
            projection_model=projection_model_class.from_FoV(
                matrix,
                self._handle_observer_input(observer),
                FoV
            ),
            modifiers=modifiers,
            time=time,
            report_path=filename
        )

    def generate_gif_core(
        self,
        propagation_model: BasePropagation,
        projection_model: BaseProjection,
        modifiers: Modifiers,
        propagation_start_time: Time,
        propagation_time_interval: timedelta,
        gif_fps: int,  # secs
        gif_duration: int,
        gif_path: str,
        *,
        background_colour: RGB = BLACK,
        pixel_width_per_object: int = 1,
    ) -> None:
        # TODO: Add docstring
        temp_dir = f"./images/temp/{''.join(choices(ascii_letters + digits, k=10))}"

        # generate images
        image_paths, image_frames = self.generate_images_core(
            propagation_model=propagation_model,
            projection_model=projection_model,
            modifiers=modifiers,
            image_start_time=propagation_start_time,
            image_time_interval=propagation_time_interval,
            number_of_images=gif_fps * gif_duration,
            path=temp_dir,
            background_colour=background_colour,
            pixel_width_per_object=pixel_width_per_object
        )

        # generate video
        self._generate_gif_core(
            image_paths=image_paths,
            gif_path=gif_path,
            fps=gif_fps
        )

        # remove temp dir
        self._remove_working_directoey(temp_dir)

    def generate_gif(
        self,
        observer: Optional[GeographicPosition] = None,
        FoV: float = 120,
        propagation_start_time: Time = ts.now(),
        propagation_time_interval: timedelta = timedelta(milliseconds=500),
        gif_fps: int = 2,
        gif_duration: int = 5,
        propagation_model: BasePropagation = SGP4Propagation(),
        matrix: Matrix = Matrix(128, 128),
        projection_model_class: type[BaseProjection] = GeocentricProjection,
        modifiers: Modifiers = Modifiers(AlwaysPixelModifier(WHITE)),
        filename: str = "./images/out.gif",
        *,
        background_colour: RGB = BLACK,
        pixel_width_per_object: int = 1
    ) -> None:
        # TODO: Write a docstring
        self.generate_gif_core(
            propagation_model=propagation_model,
            projection_model=projection_model_class.from_FoV(
                matrix=matrix,
                observer=self._handle_observer_input(observer),
                FoV=FoV
            ),
            modifiers=modifiers,
            propagation_start_time=propagation_start_time,
            propagation_time_interval=propagation_time_interval,
            gif_fps=gif_fps,
            gif_duration=gif_duration,
            gif_path=filename,
            background_colour=background_colour,
            pixel_width_per_object=pixel_width_per_object
        )

    def plot_orbital_overview(self, time: Time = ts.now()) -> None:
        """plot an interactive popup showing an overview of all satellites at a given time
        """
        plot_orbital_overview(SGP4Propagation().propagate(self.sats, time))

    #
    # Internal processes below
    #

    def _generate_video_core(
            self,
            image_paths: list[str],
            video_path: str,
            fps: int
    ) -> None:
        """generate a video from images"""
        import cv2

        timer = ProgressBar(len(image_paths))

        # get dimensions from the first frame
        frame0 = cv2.imread(image_paths[0])
        height, width, _ = frame0.shape  # type: ignore

        # setup video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # type:ignore
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        # add frames to the video
        for i, image_path in enumerate(image_paths):
            frame = cv2.imread(image_path)
            out.write(frame)  # type: ignore
            timer.update(i+1)

        # generate video
        out.release()
        print(f"Video saved to {video_path}")

    def _generate_gif_core(
            self,
            image_paths: list[str],
            gif_path: str,
            fps: int
    ) -> None:
        """generate a gif from images"""
        import imageio.v3 as iio

        # read the images from files
        frames = np.stack([iio.imread(path) for path in image_paths])

        # write the gif
        iio.imwrite(gif_path, frames, duration=1000/fps, loop=0)

        print(f"Gif saved to {gif_path}")

    def _generate_report_core(
            self,
            image_frame: ImageFrame,
            report_path: str
    ) -> None:
        # generate output images
        image_frame.to_png("./images/out.png")
        # save orbital overview as png
        plot_orbital_overview(
            image_frame.orbital_positions,
            _plot=False, _filename="./images/orbital_overview.png"
        )

        dict_to_pdf({
            "generated image": "./images/out.png",
            "orbital overview": "./images/orbital_overview.png",
            **image_frame.to_dict()
        }, report_path)

    def _create_working_directory(self, path: str) -> None:
        dir_path = Path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created {dir_path} working directory")

    def _remove_working_directoey(self, path: str) -> None:
        dir_path = Path(path)
        if dir_path.exists() and dir_path.is_dir():
            rmtree(dir_path)
            print(f"Deleted {dir_path} working directory")
