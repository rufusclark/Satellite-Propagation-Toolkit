"""Handles live communication with the device over serial to control the device display

see README for api spec
"""

from src.matrix import RGB, ImageFrame
from .tools import autoport
import serial


class LiveInterface:
    _encoding = "utf-8"

    def __init__(self, port: str = "", baudrate: int = 115200) -> None:
        if not port:
            port = autoport()

        self.conn = serial.Serial(port, baudrate)

        self._last_frame: ImageFrame = None  # type:ignore

        print(f"Connected to device on port: {port}")

    def _send_csv(self, op: int, *args) -> None:
        """send command over serial to device

        Args:
            op: op code
            args: args
        """
        self.conn.write(
            f"{op},{','.join([str(arg) for arg in args])}\n".encode(self._encoding))

    def set_pixel(self, x: int, y: int, rgb: RGB) -> None:
        """set the devices pixel to colour rgb

        Args:
            x: x position
            y: y position
            rgb: RGB object
        """
        self._send_csv(1, x, y, *rgb.to_tuple())

    def clear_display(self) -> None:
        """clear the display
        """
        self._send_csv(2)

    def get_display_dimensions(self) -> tuple[int, int]:
        """get the matrix dimensions from the device

        Returns:
            width [int], height [int]
        """
        self._send_csv(3)

        while True:
            raw = self.conn.readline()
            if raw:
                args = raw.decode(self._encoding).strip(
                    "\r\n").strip().split(",")

                row, col, *_ = args
                return int(row), int(col)

    def _debug_print_serial(self) -> None:
        while True:
            raw = self.conn.readline()
            if raw:
                raw.decode(self._encoding)
                print(raw)

    def update_display(self, frame: ImageFrame) -> None:
        """upload and display the frame on the device

        Args:
            frame: ImageFrame to be displayed
        """
        # create a blank frame for comparison if it doesn't exist
        if not self._last_frame:
            self._last_frame = frame._matrix._empty_frame()
            self.clear_display()

        # update pixels that require update
        def update_px(x, y):
            last_pixel = self._last_frame.get_pixel(x, y)
            pixel = frame.get_pixel(x, y)

            if last_pixel != pixel:
                self.set_pixel(x, y, pixel)
        frame._for_grid(update_px)

        # save frame for next update
        self._last_frame = frame

    def randomise(self) -> None:
        import time
        from random import randint

        width, height = self.get_display_dimensions()

        t0 = time.time() + 10
        while t0 > time.time():
            self.set_pixel(randint(0, width), randint(0, height), RGB.random())
