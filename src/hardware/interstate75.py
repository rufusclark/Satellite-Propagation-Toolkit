# Pinoromi Interstate75 Client Code
from core import PicoGraphicsDevice
from interstate75 import Interstate75
from picographics import DISPLAY_INTERSTATE75_128X64

driver = Interstate75(DISPLAY_INTERSTATE75_128X64)


class StellarUnicornDevice(PicoGraphicsDevice):
    def set_pixel(self, row: int, col: int, r: int, g: int, b: int) -> None:
        self.graphics.set_pen(self.graphics.create_pen(int(r), int(g), int(b)))
        self.graphics.pixel(int(row), int(col))
        driver.update()

    def clear_display(self) -> None:
        self.graphics.set_pen(self.graphics.create_pen(0, 0, 0))
        self.graphics.clear()
        driver.update()

    def update(self) -> None:
        driver.update()


StellarUnicornDevice(DISPLAY_INTERSTATE75_128X64).start()

"""
There is a fair chance this won't work as the API is different to the usual PicoGraphics API.

Will work once I've had an opportunity to test it.

The display will need to be changed if the resolution is different.

See examples at: https://github.com/pimoroni/pimoroni-pico/tree/main/micropython/examples/interstate75
"""
