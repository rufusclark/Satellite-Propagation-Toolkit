# Pinoromi Unicorn Pack Client Code
from core import PicoGraphicsDevice
from picographics import DISPLAY_UNICORN_PACK
from picounicorn import PicoUnicorn

picounicorn = PicoUnicorn()


class UnicornPack(PicoGraphicsDevice):
    def set_pixel(self, row: int, col: int, r: int, g: int, b: int) -> None:
        picounicorn.set_pixel(row, col, r, g, b)

    def clear_display(self) -> None:
        picounicorn.clear()

    def display_dimensions(self) -> tuple[int, int]:
        return picounicorn.get_width(), picounicorn.get_height()

    def update(self) -> None:
        picounicorn.update(self.graphics)

    def button_pressed(self) -> tuple[bool, int]:
        for idx, btn in enumerate([picounicorn.BUTTON_A, picounicorn.BUTTON_B, picounicorn.BUTTON_X, picounicorn.BUTTON_Y]):
            if picounicorn.is_pressed(btn):
                return True, idx
        return False, 0


UnicornPack(DISPLAY_UNICORN_PACK).start()
