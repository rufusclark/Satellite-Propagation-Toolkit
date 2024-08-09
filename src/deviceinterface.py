"""handles communication with RPi Pico over serial and control of the Pico device"""
# TODO: Include api spec in the top of this file
from typing import List, Any, Sequence

from .matrix import RGB, ImageFrame

import serial


class DeviceInterface:
    _encoding = "utf-8"

    def __init__(self, port: str = "", baudrate: int = 115200) -> None:
        if not port:
            port = self._autoport()

        self.conn = serial.Serial(port, baudrate)

        self._last_frame: ImageFrame = None  # type:ignore

        print(f"Connected to device on port: {port}")

        # set the time on the device to the current time
        self.set_current_time()

    def _autoport(self) -> str:
        """returns the str port device of first connected serial device

        Raises:
            Error if no ports are connected

        Returns:
            port e.g. "COM3"
        """
        import serial.tools.list_ports

        try:
            return serial.tools.list_ports.comports()[0].device
        except Exception as e:
            raise Exception("No ports found", e)

    def _send_csv(self, op: int, *args) -> None:
        """send command over serial to device

        Args:
            op: op code
            args: args
        """
        self.conn.write(
            f"{op},{','.join([str(arg) for arg in args])}\n".encode(self._encoding))

    def _delayed_cmd(self, ts: float, *args) -> None:
        """send an command to be executed at a specified unix timestamp

        consider setting the time on the device to ensure it is correct. micro-proccessors have a tendency to have poor timekeeper or no timekeeping ability.

        Args:
            ts: execution unix timestamp
        """
        self._send_csv(5, ts, *args)

    def set_pixel(self, x: int, y: int, rgb: RGB) -> None:
        """set the devices pixel to colour rgb

        Args:
            x: x position
            y: y position
            rgb: RGB object
        """
        self._send_csv(1, x, y, *rgb.to_tuple())

    def delayed_set_pixel(self, ts: float, x: int, y: int, rgb: RGB) -> None:
        self._delayed_cmd(ts, 1, x, y, *rgb.to_tuple())

    def clear_display(self) -> None:
        """clear the display
        """
        self._send_csv(2)

    def delayed_clear(self, ts: float) -> None:
        self._delayed_cmd(ts, 2)

    def display_dimensions(self) -> tuple[int, int]:
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

    def set_time(self, unix_timestamp: float) -> None:
        """set the time on the device

        Args:
            unix_timestamp: unix timestamp seconds
        """
        self._send_csv(4, unix_timestamp)

    def set_current_time(self) -> None:
        """set the time on the device to the current time
        """
        import time
        self.set_time(time.time())

    def upload_frame(self, frame: ImageFrame) -> None:
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
