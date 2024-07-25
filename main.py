"""Pico main code"""


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

    def handle_file(self, arg: list[str]) -> None:
        # TODO: Implement receive file
        pass

    def set_pixel_buffer(self, args: list[str]) -> None:
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

    def decode_csv(self) -> tuple[str, list[str]]:
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

    def handle_csv(self, op: str, args: list[str]) -> None:
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


if __name__ == "__main__":
    pico = Pico()
    while True:
        op, args = pico.decode_csv()
        pico.handle_csv(op, args)
