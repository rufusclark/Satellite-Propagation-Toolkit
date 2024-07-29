"""handles communication with RPi Pico over serial and control of the Pico device"""
from typing import List, Any, Sequence

from .matrix import RGB

import serial


class DeviceInterface:
    _encoding = "utf-8"

    def __init__(self, port: str = "", baudrate: int = 115200) -> None:
        if not port:
            port = self._autoport()

        self.conn = serial.Serial(port, baudrate)

        print(f"Connected to device on port: {port}")

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

    def _send_csv(self, op: int, *args):
        """send command over serial to device

        Args:
            op: op code
            args: args
        """
        self.conn.write(
            f"{op},{','.join([str(arg) for arg in args])}\n".encode(self._encoding))

    def set_pixel(self, x: int, y: int, rgb: RGB):
        """set the devices pixel to colour rgb

        Args:
            x: x position
            y: y position
            rgb: RGB object
        """
        self._send_csv(1, x, y, *rgb.to_tuple())

    def clear(self):
        self._send_csv(2)

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
                return int(args[0]), int(args[1])
