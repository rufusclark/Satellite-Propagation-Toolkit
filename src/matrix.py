"""code and utilities to work with LED matrix data, generate images and more"""
from typing import TYPE_CHECKING, Optional

from skyfield.timelib import Time

from .rgb import RGB, BLACK
from .models import ts
from .analysis import Modifiers
if TYPE_CHECKING:
    from .projection import SatFrame, BaseProjection, FramePosition
    from .propagation import OrbitalPosition

# TODO: Support adding ImageFrames together (and all child objects)


class ImageFrame:
    """MatrixFrame about origin (top left) with conventional cartesian coordinates

    do not create direction. Create by calling .render on a SatFrame
    """

    def __init__(self, sat_frame: "SatFrame", modifiers: Modifiers, *, render: bool = True) -> None:
        """create a new ImageFrame from a SatFrame and modifiers

        Args:
            sat_frame: SatFrame
            modifiers: Modifiers
        """
        # link objects
        self._sat_frame = sat_frame
        self._modifiers = modifiers

        # setup pixels
        self._pixels: list[RGB] = [RGB() for _ in range(len(self.matrix))]

        # render
        if render:
            for position in self.sat_frame.frame_positions:
                rgb = self.get_pixel(position.x_idx, position.y_idx)
                for modifier in modifiers.modifiers:
                    rgb = modifier.handle(position, rgb)
                self.set_pixel(position.x_idx, position.y_idx, rgb)

    @property
    def frame_positions(self) -> list["FramePosition"]:
        return self._sat_frame.frame_positions

    @property
    def orbital_positions(self) -> list["OrbitalPosition"]:
        return [frame_position.orbital_position for frame_position in self.frame_positions]

    @property
    def matrix(self) -> "Matrix":
        return self._sat_frame._model._matrix

    @property
    def modifiers(self) -> Modifiers:
        return self._modifiers

    @property
    def projection_model(self) -> "BaseProjection":
        return self._sat_frame._model

    @property
    def sat_frame(self) -> "SatFrame":
        return self._sat_frame

    def key_to_dict(self) -> dict:
        return {
            "image frame modifiers": self.modifiers.key_with_analysis_to_dict(self.sat_frame)
        }

    def to_dict(self) -> dict:
        return {
            "image frame modifiers": self.modifiers.key_with_analysis_to_dict(self.sat_frame),
            **self.sat_frame.to_dict()
        }

    def key_info(self) -> str:
        from pprint import pformat
        return pformat(self.key_to_dict())

    def info(self) -> str:
        from pprint import pformat
        return pformat(self.to_dict())

    # !
    # ! Old code beloww
    # !

    # def key(self) -> str:
    #     # TODO: Reimplement
    #     """return image key for ImageFrame

    #     this requires that this object was rendered from a SatFrame object"""
    #     if self._modifiers:
    #         return self._modifiers.key()
    #     raise UserWarning(
    #         "this method is only valid for ImageFrame objects rendered from SatFrames")

    # def key_with_analysis(self) -> str:
    #     # TODO: Reimplement
    #     """return image key for ImageFrame with the number of sats per category

    #     this requires that this object was rendered from a SatFrame object"""
    #     if self._modifiers and self._sat_frame:
    #         return self._modifiers.key_with_analysis(self._sat_frame)
    #     raise UserWarning(
    #         "this method is only valid for ImageFrame objects rendered from SatFrames")

    # def info(self) -> str:
    #     # TODO: Reimplement
    #     """return info about the ImageFrame including model, matrix and sats

    #     this requires that this object was rendered from a SatFrame object"""
    #     return self.key_with_analysis() + "\n" + self._sat_frame.info()  # type: ignore

    def _idx(self, x: int, y: int) -> int:
        return (y * self.matrix.width) + x

    def set_pixel(self, x: int, y: int, rgb: RGB) -> None:
        self._pixels[self._idx(x, y)] = rgb

    def get_pixel(self, x: int, y: int) -> RGB:
        return self._pixels[self._idx(x, y)]

    def idx_is_valid(self, x: int, y: int) -> bool:
        return (x >= 0 and x < self.matrix.width) and (y >= 0 and y < self.matrix.height)

    def _for_grid(self, fn) -> None:
        for y in range(self.matrix.height):
            for x in range(self.matrix.width):
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
        for y in range(self.matrix.height):
            for x in range(self.matrix.width):
                print(fn(x, y), end=", ")
            print()

    def print_pixel_grid(self) -> None:
        self._print_grid(lambda x, y: self.get_pixel(x, y))

    def print_position_grid(self) -> None:
        self._print_grid(lambda x, y: f"{x, y}")

    def __repr__(self) -> str:
        return f"<ImageFrame t={self.sat_frame.time} {self.matrix}>"

    def to_png(self, filename: str = "image.png", *, _print: bool = True, _create_path: bool = True, _background_colour: Optional[RGB] = None, _pixel_width_per_object: Optional[int] = None) -> None:
        """saves the ImageFrame object as a png file

        by default this will create any neccesary folders aswell and will print out a confirmation message once saved

        Args:
            filename: image filename including path. Defaults to "image.png".
            _print: whether to print a confirmation message. Defaults to True.
            _create_path: whether to create the path if it doesn't exist. Defaults to True.
            _background_colour: specify a different pixel background colour. Defaults to Black.
            _pixel_width_per_object: the number of pixels width per object. Defaults to 1. 3 would mean a 3x3 box for each pixel
        """
        if _create_path:
            from pathlib import Path
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

        import png

        pixels = []

        # support more than one pixel per object (Optional)
        if _pixel_width_per_object:
            # generate new empty ImageFrame
            new_frame = ImageFrame(
                self.sat_frame, self._modifiers, render=False)

            # populate the ImageFrame
            n = _pixel_width_per_object//2

            def generate_pixels_per_object(x, y) -> None:
                if self.get_pixel(x, y) != BLACK:
                    for dx in range(-n, n+1):
                        for dy in range(-n, n+1):
                            nx, ny = x + dx, y + dy
                            if self.idx_is_valid(nx, ny):
                                new_frame.set_pixel(
                                    nx, ny,
                                    new_frame.get_pixel(nx, ny)
                                    + self.get_pixel(x, y)
                                )

            self._for_grid(generate_pixels_per_object)
            self = new_frame

        # change background colour from black (Optional)
        if _background_colour:
            def background_colour(x, y) -> None:
                if self.get_pixel(x, y) == BLACK:
                    self.set_pixel(x, y, _background_colour)
            self._for_grid(background_colour)

        # convert internal matrix to png
        for y in range(self.matrix.height):
            row = []
            for x in range(self.matrix.width):
                row.extend(self.get_pixel(x, y).to_tuple())
            pixels.append(row)

        png.from_array(pixels, "RGB").save(filename)
        if _print:
            print(
                f"Saved image: {Path(filename).absolute().as_posix()}")


class Matrix:
    def __init__(self, width: int = 16, height: int = 16) -> None:
        """creates a matrix object that it used to manage the size of matrix frame objects

        This is effectively a proxy for a LED matrix panel or picture

        Args:
            width: number of pixels wide. Defaults to 16.
            height: number of pxiels high. Defaults to 16.
        """
        self.width = width
        self.height = height

    def info(self) -> str:
        return f"matrix size: ({self.width} x {self.height})"

    def __len__(self) -> int:
        return self.width * self.height

    def __repr__(self) -> str:
        return f"<Matrix (w={self.width}, h={self.height})"
