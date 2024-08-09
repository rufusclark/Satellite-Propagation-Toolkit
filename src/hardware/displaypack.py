# Pinoromi Display Pack Client Code
from core import PicoGraphicsDevice
from picographics import DISPLAY_PICO_DISPLAY
from pimoroni import RGBLED, Button

RGBLED(6, 7, 8).set_rgb(0, 0, 0)

btns = [Button(x) for x in [12, 13, 14, 15]]


class DisplayPack(PicoGraphicsDevice):
    def button_pressed(self) -> tuple[bool, int]:
        for idx, btn in enumerate(btns):
            if btn.is_pressed:
                return True, idx
        return False, 0


DisplayPack(DISPLAY_PICO_DISPLAY, cell_size=6).start()
