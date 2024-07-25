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
