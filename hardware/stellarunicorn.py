"""Client code for Pomoroni Stellar Unicorn"""

import machine  # type: ignore
from random import randint
from stellar import StellarUnicorn
from picographics import PicoGraphics, DISPLAY_STELLAR_UNICORN as DISPLAY
import sys

stellar = StellarUnicorn()
graphics = PicoGraphics(DISPLAY)

# overclock to 200MHz
machine.freq(200000000)

while True:
    args = sys.stdin.readline().strip("\r\n").strip().split(",")

    if not args:
        continue

    op = int(args[0])

    if op == 1:
        # set pixel
        _, row, col, r, g, b = args
        graphics.set_pen(graphics.create_pen(int(r), int(g), int(b)))
        graphics.pixel(int(row), int(col))
        stellar.update(graphics)
    elif op == 2:
        # clear display
        graphics.set_pen(graphics.create_pen(0, 0, 0))
        graphics.clear()
        stellar.update(graphics)
    elif op == 3:
        # request dimensions
        print(stellar.WIDTH, stellar.HEIGHT, sep=",")
