# Pinoromi Stellar Unicorn Client Code
from core import PicoGraphicsDevice
from picographics import DISPLAY_STELLAR_UNICORN
from stellar import StellarUnicorn

stellarunicorn = StellarUnicorn()


class StellarUnicornDevice(PicoGraphicsDevice):
    def set_pixel(self, row: int, col: int, r: int, g: int, b: int) -> None:
        self.graphics.set_pen(self.graphics.create_pen(int(r), int(g), int(b)))
        self.graphics.pixel(int(row), int(col))
        stellarunicorn.update(self.graphics)

    def clear_display(self) -> None:
        self.graphics.set_pen(self.graphics.create_pen(0, 0, 0))
        self.graphics.clear()
        stellarunicorn.update(self.graphics)

    def display_dimensions(self) -> tuple[int, int]:
        return stellarunicorn.WIDTH, stellarunicorn.HEIGHT

    def update(self) -> None:
        stellarunicorn.update(self.graphics)

    def button_pressed(self) -> tuple[bool, int]:
        for idx, btn in enumerate([stellarunicorn.SWITCH_A, stellarunicorn.SWITCH_B, stellarunicorn.SWITCH_C, stellarunicorn.SWITCH_D]):
            if stellarunicorn.is_pressed(btn):
                return True, idx
        return False, 0


StellarUnicornDevice(DISPLAY_STELLAR_UNICORN).start()
