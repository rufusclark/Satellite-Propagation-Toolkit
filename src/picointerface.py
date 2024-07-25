"""handles communication with RPi Pico over serial and control of the Pico device"""
from typing import List, Tuple

from .matrix import RGB

# TODO: Implement sending blobs or files


class PC:
    def __init__(self, port: str = "", baudrate: int = 115200, encoding: str = "utf-8") -> None:
        self.encoding = encoding
        import serial

        if not port:
            port = self.auto_port()

        self.conn = serial.Serial(port, baudrate)

        print(f"Connected to Pico on port {port}")

    def auto_port(self) -> str:
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

    def send_csv(self, args: List[str]):
        """send csv to the Pico"""
        self.conn.write(f"{','.join(args)}\n".encode(self.encoding))

    def send_file(self):
        # TODO: Implement send file
        pass

    def set_pixel_buffer(self, x: int, y: int, rgb: RGB):
        """set a pixel in the led matrix buffer

        Args:
            x: x position
            y: y position
            rgb: RGB colour value
        """
        self.send_csv(["set pixel buffer", str(x), str(y),
                      str(rgb.R), str(rgb.G), str(rgb.B)])

    def clear_buffer(self):
        """clear the led matrix buffer - does not change the led matrix itself
        """
        self.send_csv(["clear buffer"])

    def clear_matrix(self):
        """clear the led matrix
        """
        self.send_csv(["clear matrix"])

    def update_matrix(self):
        """update the led matrix with the current led matrix buffer
        """
        self.send_csv(["update matrix"])

    def randomise(self):
        """update the led matrix with random colours indefinately
        """
        from random import randint
        from time import sleep

        while True:
            self.set_pixel_buffer(randint(0, 15), randint(0, 15), RGB.random())
            self.update_matrix()
            sleep(0.01)


class Pico:
    def __init__(self, brightness: float = 1.0) -> None:
        import machine  # type: ignore

        from stellar import StellarUnicorn
        from picographics import PicoGraphics, DISPLAY_STELLAR_UNICORN as DISPLAY

        # overclock to 200MHz
        machine.freq(200000000)

        # init hardware
        self.stellar = StellarUnicorn()
        self.graphics = PicoGraphics(DISPLAY)

        # set LED brightness
        self.stellar.set_brightness(brightness)

    def handle_file(self, arg: List[str]) -> None:
        # TODO: Implement receive file
        pass

    def set_pixel_buffer(self, args: List[str]) -> None:
        row, col, r, g, b = args
        self.graphics.set_pen(self.graphics.create_pen(int(r), int(g), int(b)))
        self.graphics.pixel(int(row), int(col))

    def clear_buffer(self) -> None:
        self.graphics.set_pen(self.graphics.create_pen(0, 0, 0))
        self.graphics.clear()

    def clear_matrix(self) -> None:
        self.clear_buffer()
        self.update_matrix()

    def update_matrix(self) -> None:
        self.stellar.update(self.graphics)

    def decode_csv(self) -> Tuple[str, List[str]]:
        import sys

        # read msg string from serial port
        msg = sys.stdin.readline().strip()

        args = msg.split(",")

        # ignore empty instructions
        if not len(args):
            return "", []

        op = args[0]
        args = args[1:]
        return op, args

    def handle_csv(self, op: str, args: List[str]) -> None:
        # handle empty operation
        if not op:
            return

        if op == "set pixel buffer":
            self.set_pixel_buffer(args)
        elif op == "clear buffer":
            self.clear_buffer()
        elif op == "clear matrix":
            self.clear_matrix()
        elif op == "update matrix":
            self.update_matrix()
