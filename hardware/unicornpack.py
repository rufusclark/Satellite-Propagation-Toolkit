"""Client code for PIM546 Pimoroni Unicorn Pack"""

import machine  # type: ignore
from random import randint
from picounicorn import PicoUnicorn
import sys

picounicorn = PicoUnicorn()

# overclock to 200MHz
machine.freq(200000000)

while True:
    args = sys.stdin.readline().strip("\r\n").strip().split(",")

    if not args:
        continue

    op = int(args[0])

    if op == 1:
        # set pixel
        _, x, y, r, g, b = args
        picounicorn.set_pixel(int(x), int(y), int(r), int(g), int(b))
    elif op == 2:
        # clear display
        picounicorn.clear()
    elif op == 3:
        # request dimensions
        print(picounicorn.get_width, picounicorn.get_height, sep=",")
