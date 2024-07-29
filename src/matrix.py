"""code and utilities to work with LED matrix data, generate images and more"""
from typing import Sequence, Any
from skyfield.timelib import Time

from .models import Sat
from .rgb import RGB
from .analysis import BasePixelModifier, AltitudeModifier


class Matrix:
    def __init__(self, width: int = 16, height: int = 16, path: str = "./images/", pixel_modifiers: Sequence[BasePixelModifier] = []) -> None:
        """creates a matrix object that it used to manage the size of matrix frame objects and file saving locations.

        This is effectively a proxy for a LED matrix panel or picture

        Args:
            width: number of pixels wide. Defaults to 16.
            height: number of pxiels high. Defaults to 16.
            path: base directory for saved images. Defaults to "./images/".
            pixel_modifiers: list of pixel modifiers for support for changing pixel values based on sat metadata
        """
        self.width = width
        self.height = height
        self.path = path
        self._pixel_modifiers = pixel_modifiers

    @property
    def path(self) -> str:
        return self._path

    @path.setter
    def path(self, path) -> None:
        import os

        # create directory if not exists
        if not os.path.exists(path):
            os.makedirs(path)

        self._path = path

    def __repr__(self) -> str:
        return f"<Matrix (w={self.width}, h={self.height})"


class Frame:
    """MatrixFrame about origin (top left) with conventional cartesian coordinates
    """

    def __init__(self, m: Matrix, time: Time) -> None:
        self._m = m
        self.time = time
        self._pixels: list[RGB] = [
            RGB() for _ in range(self._m.width * self._m.height)]

    @property
    def unix_timestamp(self) -> float:
        """unix timestamp of frame in seconds including microseconds

        Returns:
            float seconds since epoch
        """
        return self.time.utc_datetime().timestamp()  # type: ignore

    @property
    def unix_timestamp_seconds(self) -> int:
        """unix timestamp of frame in seconds - no microseconds

        Returns:
            integer seconds since epoch
        """
        return int(self.unix_timestamp)

    def _pixel_idx(self, x: int, y: int) -> int:
        return (y * self._m.width) + x

    def set_pixel(self, x: int, y: int, rgb: RGB) -> None:
        self._pixels[self._pixel_idx(x, y)] = rgb

    def get_pixel(self, x: int, y: int) -> RGB:
        return self._pixels[self._pixel_idx(x, y)]

    def handle_pixel_modifiers(self, x: int, y: int, sat: Sat, args: dict[str, Any]):
        """conditionally change the value of a pixel based on conditional modifier logic from Matrix

        Args:
            x: x position
            y: y position
            sat: Sat object
        """
        for modifier in self._m._pixel_modifiers:
            rgb = self.get_pixel(x, y)
            rgb = modifier.handle(sat, rgb, args)
            self.set_pixel(x, y, rgb)

    def _for_grid(self, fn) -> None:
        for y in range(self._m.height):
            for x in range(self._m.width):
                fn(x, y)

    def _print_grid(self, fn) -> None:
        """calls fn for each row and col and print output in a grid. See usage

        Usage:
            >>> m = Matrix(3, 4)
            >>> mf = MatrixFrame(m, t)
            >>> def pos(x, y):
            >>>     return f"{x, y}"
            >>> mf._format_coord(pos)
            (0, 0), (1, 0), (2, 0),
            (0, 1), (1, 1), (2, 1),
            (0, 2), (1, 2), (2, 2),
            (0, 3), (1, 3), (2, 3),
        Args:
            fn: function to print output
        """
        for y in range(self._m.height):
            for x in range(self._m.width):
                print(fn(x, y), end=", ")
            print()

    def print_pixel_grid(self) -> None:
        self._print_grid(lambda x, y: self.get_pixel(x, y))

    def print_position_grid(self) -> None:
        self._print_grid(lambda x, y: f"{x, y}")

    def __repr__(self) -> str:
        return f"<MatrixFrame t={self.time} {self._m}>"

    def to_png(self, filename) -> None:
        import png

        pixels = []

        for y in range(self._m.height):
            row = []
            for x in range(self._m.width):
                row.extend(self.get_pixel(x, y).to_tuple())
            pixels.append(row)

        filepath = self._m.path + filename
        png.from_array(pixels, "RGB").save(filepath)
        print(f"Saved png: {filepath}")


if __name__ == "__main__":
    from skyfield.api import load
    ts = load.timescale()

    m = Matrix(4, 4)
    f = Frame(m, ts.now())

    print(f)
