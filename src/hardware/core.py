# Hardware core code
# TODO: Write docs

import machine  # type: ignore
from picographics import PicoGraphics
import uselect  # type: ignore
import os
from pngdec import PNG
import sys
import time


class StopWatch:
    """ms accurate stopwatch"""

    def __init__(self):
        self.reset()

    def _time_ms(self) -> int:
        return time.ticks_ms()  # type: ignore

    def reset(self):
        self.start_ms = self._time_ms()

    @property
    def elapsed_ms(self) -> int:
        return self._time_ms() - self.start_ms

    @property
    def elapsed_s(self) -> float:
        return self.elapsed_ms / 1000

    @property
    def elapsed_m(self) -> float:
        return self.elapsed_s / 60


class UntetheredMode:
    _LIVE = 0
    _OFFSET_LIVE = 1
    _BACKUP = 2

    def __init__(self) -> None:
        self.view = 0
        self.frame_timer = StopWatch()
        self.inactivity_timer = StopWatch()
        self.sleep = False
        self.reset()

    def reset(self) -> None:
        # calculate the correct mode of operation and offset the current time as appropriate
        self.playback_mode = 0
        self.offset = 0

        # set playback mode
        self.tss = self._list_dir()
        unix_ts = time.time()

        # set to backup mode because no image files exist
        if len(self.tss) == 0:
            self.playback_mode = self._BACKUP
            self.tss = self._list_dir()
            if len(self.tss) != 0:
                self.offset = unix_ts - self.tss[0]

        # set to live mode because valid data for current time period
        elif unix_ts > self.tss[0] and unix_ts < self.tss[-1]:
            self.playback_mode = self._LIVE

        # set to offset mode because no valid data for current time period
        else:
            self.playback_mode = self._OFFSET_LIVE
            self.offset = unix_ts - self.tss[0]

    def handle(self, device: "PicoGraphicsDevice", cell_size: int = 1) -> None:
        """main event loop for untethered mode (outputing images from root)

        Args:
            graphics: PicoGraphics object
            cell_size: number of pixels wide per "sat cell". Defaults to 1.
        """

        # change view if button is pressed
        btn_pressed, idx = device.button_pressed()
        if btn_pressed:
            self.view = idx

            # handle sleep mode
            self.inactivity_timer.reset()
            if self.sleep:
                self.sleep = False

        # sleep if been inactive for 5 minutes
        if self.inactivity_timer.elapsed_m > 5:
            if not self.sleep:
                self.sleep = True
                device.clear_display()

        else:
            # only execute every second
            if self.frame_timer.elapsed_s > 1:
                self.frame_timer.reset()
                unix_ts = self.unix_time()

                # if image exists
                if unix_ts in self.tss:

                    png = PNG(device.graphics)
                    # png = PNG(graphics)

                    # open image file for respective dir
                    if self.playback_mode == self._BACKUP:
                        png.open_file(
                            f"backup_images/{self.view}/{unix_ts}.png")
                    else:
                        png.open_file(f"images/{self.view}/{unix_ts}.png")

                    # scale to cell_size and display png
                    png.decode(0, 0, scale=cell_size)

                    device.update()
                    # graphics.update()

                # reset if the time is after the first available time
                elif (len(self.tss) != 0) and (unix_ts > self.tss[-1]):
                    self.reset()

    def unix_time(self) -> int:
        return time.time() - self.offset  # type: ignore

    def _list_dir(self) -> list[int]:
        """return a list of all timestamps for the current view and playback_mode
        """
        dirs = []

        # get timestamps from backup dir if in backup mode
        if self.playback_mode == self._BACKUP:
            if ("backup_images" in os.listdir()) and (f"{self.view}" in os.listdir("backup_images")):
                dirs = os.listdir(f"backup_images/{self.view}")

        # get timestamps from main dir if not in backup mode
        else:
            if ("images" in os.listdir()) and (f"{self.view}" in os.listdir("images")):
                dirs = os.listdir(f"images/{self.view}")

        # convert file names to int unix timestamps and sort
        out = [int(dir[:-4]) for dir in dirs]
        out.sort()

        return out


class PicoGraphicsDevice:
    def __init__(self, display: int, cell_size: int = 1) -> None:

        # overclock to 200MHz
        machine.freq(200000000)

        # create and register stdin listener
        self._poll = uselect.poll()
        self._poll.register(sys.stdin, uselect.POLLIN)

        self._tethered = True

        # setup graphics
        self._cell_size = cell_size
        self.graphics = PicoGraphics(display)
        self.graphics.set_backlight(1)

        # setup untethered device
        self.untethered_handler = UntetheredMode()

    def __del__(self) -> None:
        # unregister listener
        self._poll.unregister(sys.stdin)

    def start(self) -> None:
        """Start the main event loop
        """

        # flash screen for 1 seconds
        self.set_pixel(0, 0, 255, 255, 255)
        time.sleep(1)
        self.set_pixel(0, 0, 0, 0, 0)

        last_comm = StopWatch()

        # time without communication from computer to enter untethered mode [ms]
        TIMEOUT = 5000

        try:
            while True:
                # serial msg sent
                if self._stdin_ready():
                    last_comm.reset()
                    # enter tethered mode

                    # init for tethered mode if switching mode
                    if not self._tethered:
                        self._tethered = True
                        self.clear_display()

                    # handle tethered mode
                    self._tethered_mode_handle()

                elif last_comm.elapsed_ms > TIMEOUT:
                    # enter untethered mode

                    # init for untethered mode if switching mode
                    if self._tethered:
                        self._tethered = False
                        self.clear_display()
                        self.untethered_handler.reset()
                        self.untethered_handler.sleep = False
                        self.untethered_handler.inactivity_timer.reset()

                    # handle untethered mode
                    self.untethered_handler.handle(
                        self, cell_size=self._cell_size)

        except KeyboardInterrupt:
            pass

# !
# ! Overwrite the following methods to customise control
# !

    def set_pixel(self, row: int, col: int, r: int, g: int, b: int) -> None:
        """set a pixel on the display

        overwrite if not the default PicoGraphics code"""
        self.graphics.set_pen(self.graphics.create_pen(r, g, b))
        row, col = row * self._cell_size, col * self._cell_size
        for i in range(self._cell_size):
            for j in range(self._cell_size):
                self.graphics.pixel(row+i, col+j)
        self.graphics.update()

    def clear_display(self) -> None:
        """clear the display

        overwrite if not the default PicoGraphics code"""
        self.graphics.set_pen(0)
        self.graphics.clear()
        self.graphics.update()

    def display_dimensions(self) -> tuple[int, int]:
        """return the width and height of your display

        overwrite if not the default PicoGraphics code"""
        w, h = self.graphics.get_bounds()
        return w//self._cell_size, h//self._cell_size

    def update(self) -> None:
        """update the graphics screen

        overwrite if not the default PicoGraphics code"""
        self.graphics.update()

    def button_pressed(self) -> tuple[bool, int]:
        """overwrite this method to support changing the view using buttons

        should return whether a bottom has been changed and the index of the change
        """
        return False, 0

# !
# ! Internal Methods
# !

    def _stdin_ready(self) -> bool:
        """return bool whether stdin has a bytes ready to be read"""
        timeout_ms = 0
        return bool(self._poll.poll(timeout_ms))

    def _send_serial(self, *args) -> None:
        """send serial to host where args are a sequence of arguments to be encoded in csv format
        """
        print(*args, sep=",", end="\n")

    def _read_serial_csv(self) -> list[str]:
        """read serial port and return str args decoded as csv

        please note this is a block method. Consider checking anthing is ready to be read before with the `stdin_ready()` method
        """
        return sys.stdin.readline().strip("\r\n").strip().split(",")

    def _tethered_mode_handle(self) -> None:
        """handle cmds received over serial"""
        cmd = self._read_serial_csv()

        if not cmd:
            return

        op, *args = cmd
        op = int(op)

        if op == 1:
            # set pixel
            row, col, r, g, b, *_ = args
            row, col, r, g, b = int(row), int(col), int(r), int(g), int(b)
            self.set_pixel(row, col, r, g, b)

        elif op == 2:
            # clear display
            self.clear_display()

        elif op == 3:
            # request dimensions
            self._send_serial(*self.display_dimensions())
