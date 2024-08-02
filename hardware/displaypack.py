"""Client code for Pimoroni Display Pack"""

import machine  # type: ignore
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY as DISPLAY
import sys

graphics = PicoGraphics(DISPLAY)
graphics.set_backlight(1)

# overclock to 200MHz
machine.freq(200000000)

# width and height of cell in pixels
cell_size = 6

width, height = graphics.get_bounds()

while True:
    args = sys.stdin.readline().strip("\r\n").strip().split(",")

    if not args:
        continue

    op = int(args[0])

    if op == 1:
        # set pixel
        _, row, col, r, g, b, *_ = args
        row = int(row)*cell_size
        col = int(col)*cell_size
        graphics.set_pen(graphics.create_pen(int(r), int(g), int(b)))
        for i in range(cell_size):
            for j in range(cell_size):
                graphics.pixel(int(row)+i, int(col)+j)
        graphics.update()
    elif op == 2:
        # clear display
        graphics.set_pen(graphics.create_pen(0, 0, 0))
        graphics.clear()
        graphics.update()
    elif op == 3:
        # request dimensions
        print(width//cell_size, height//cell_size, sep=",")
    elif op == 4:
        # set time
        _, ts, *_ = args
        # TODO: Implement
    elif op == 5:
        # delayed request
        _, ts, op, *args = args
        ts = float(ts)
        op = int(op)
        # TODO: Implement
