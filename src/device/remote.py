"""Handles remote control of the Pico to write files to the filesystem and set time"""
# ! WARNING ! For some rather frustrating reason pyboard is not distributed well anywhere and is instead downloaded as a script from GitHub go figure. https://docs.micropython.org/en/latest/reference/pyboard.py.html# https://github.com/micropython/micropython/blob/master/tools/pyboard.py pyserial is the only dependency of this code
from .pyboard import Pyboard
from .tools import autoport
from ..progress import LapTimer
from ..projectionmodels import BaseProjectionModel
from ..analysis import Modifiers
from ..models import ts
import datetime


class RemoteInterface:
    """remoteInterface is a class for communicating with the underlying fs, micropython and executing repl commands on a micropython device from a connected PC.

    this object is built upon Pyboard (root of mpremote)

    usage is not recommended unless you know what you are doing. it is possible to permanently delete all files on your micropython device with this object
    """
    # ! Unplug and replug to start program

    def __init__(self, port: str = "", baudrate: int = 115200) -> None:
        if not port:
            port = autoport()

        # init
        self._pyb = Pyboard(port, baudrate)

        # must include this to enter raw repl mode and start communication
        self._pyb.enter_raw_repl()

        print(f"Connected to device on port {port}")

    def __del__(self) -> None:
        # start main.py script
        self.start_main()
        # must call to exit raw repl mode on the pico
        self._pyb.exit_raw_repl()

        print("Disconnected from device")

    def _create_dir_if_not_exist(self, dir: str) -> None:
        """create an absolute dir on the remote device if it doesn't already exist

        Args:
            dir: absolute dir path
        """
        if not self._pyb.fs_exists(dir):
            self._pyb.fs_mkdir(dir)

    def put(self, src: str, dst: str) -> None:
        """copy the file src to the location dst on the remote device.

        please note src is relative and dst is an absolute path on the host including the filename

        the directory must already exist or an error will occur

        Args:
            src: path (and filename) to file on PC
            dst: path (and filename) on remote device
        """
        self._pyb.fs_put(src, dst)

    def copy_file_structure(self, src: str, dst: str, *, _progress: bool = True, _print: bool = True) -> None:
        """copy the file structure from the PC to the remote fs

        Args:
            src: filepath of the folder to be copied, not including the root folder name
            dst: root filepath for desination. Defaults to "".
            _progress: whether to print progress stats. Defaults to True.
            _print: whether to print when a file or dir is copied. Defaults to True.
        """
        # create host directory
        from pathlib import Path
        rootdir = Path(src)
        self._create_dir_if_not_exist(dst)

        if _progress:
            _print = False

            # calculate number of items
            count = 0
            for f in rootdir.rglob("*"):
                count += 1

            timer = LapTimer(_n_target=count)

        for f in rootdir.rglob("*"):
            # traverse through file tree
            src_path = f.as_posix()
            dst_path = dst + src_path.removeprefix(src)

            if f.is_dir():
                # create file if not exists
                self._create_dir_if_not_exist(dst_path)

                if _print:
                    print(f"Create remote dir, {dst_path}")

            elif f.is_file():
                # copy file
                self.put(src_path, dst_path)

                if _print:
                    print(
                        f"Copied host file ({src_path}) to remote ({dst_path})")

            if _progress:
                timer.lap()
                print(f"{timer.info() + ' ' + dst_path:<100}", end="\r")

        if _progress:
            print()

    def tree(self, src: str = "/", *, _depth: int = 0) -> None:
        """print a linux like tree output of the remote filesystem

        Args:
            src: source path. Defaults to "/".
            _depth: internal attribute. do not use. Defaults to 0.
        """
        import stat
        if _depth == 0:
            print(src)
        for dir in self._pyb.fs_listdir(src):
            print(f"{'│   '*(_depth)}├── {dir.name}")
            if stat.S_ISDIR(dir.st_mode):
                dir_path = src + dir.name + "/"
                self.tree(dir_path, _depth=_depth+1)

    def delete_dir_and_contents(self, dst: str) -> None:
        """deleted remote directory and all children with recursive calls

        this will deleted everything inside of these folders inreversibly

        please ensure dst ends in "/" of this will throw an error

        Args:
            dst: remote directory to remove along with contents
        """
        if not self._pyb.fs_exists(dst):
            return

        import stat
        for dir in self._pyb.fs_listdir(dst):
            if stat.S_ISDIR(dir.st_mode):
                dir_path = dst + dir.name + "/"
                self.delete_dir_and_contents(dir_path)
            else:
                file_path = dst + dir.name
                self._pyb.fs_rm(file_path)
        self._pyb.fs_rmdir(dst)

    def set_datetime(self) -> None:
        """set the datetime on the device to the current unix datetime

        note this is UTC datetime not locale datetime

        datetime format defined in https://docs.micropython.org/en/latest/library/machine.RTC.html (not standard CPython format)
        """
        now = datetime.datetime.utcnow()
        time_tuple = (now.year, now.month, now.day,
                      now.weekday(), now.hour, now.minute, now.second, now.microsecond/1000000)
        self._pyb.eval(f'machine.RTC().datetime({time_tuple})')

    def get_datetime(self) -> datetime.datetime:
        """get the current UTC (unix) datetime from the remote device

        Returns:
            datetime.datetime object
        """
        t = str(self._pyb.eval("machine.RTC().datetime()"),
                encoding="utf8")[1:-1].split(", ")
        return datetime.datetime(int(t[0]), int(t[1]), int(
            t[2]), int(t[4]), int(t[5]), int(t[6]))

    def get_display_dimensions(self) -> tuple[int, int]:
        width, height = str(self._pyb.eval(
            'open("display_dimensions").read().strip()'), encoding="utf8").split(",")
        return int(width), int(height)

    def start_main(self) -> None:
        """starts running the local main.py file on the remote device

        this will continue running after the program disconnects

        automatically called on __del__
        """
        self._pyb.exec_raw_no_follow(
            '(lambda: exec(open("main.py").read()))()')

    def fresh_copy(self, src: str, dst: str) -> None:
        """delete file on remote and then copy the file structure from the PC to the remote fs

        Args:
            src: filepath of the folder to be copied, not including the root folder name
            dst: root filepath for desination. Defaults to "".
        """
        self.delete_dir_and_contents(dst + "/")
        self.copy_file_structure(src, dst)

    def generate_images_to_device(
            self,
            model: BaseProjectionModel,
            modifiers: list[Modifiers],
            times: list[datetime.datetime],
            *,
            _backup: bool = False,
            _delete_old_data: bool = True,
            _cache_generated_images: bool = False,
            _print: bool = True
    ):
        """generates and send propagation data to a remote device

        please note that all times will be rounded to the nearest second as the client code does not support sub second precision.

        please note datetimes much be created with the utc timezone as below:
        >>> from skyfield.api import utc
        >>> from datetime import datetime
        >>> dt = datetime.now(tz=utc)
        or
        >>> dt = datetime(2024, 09, 28, tzinfo=utc)

        it is not recommended to change the _ (underscore) parameters for this method as they may have undocumented and unexpected side effects.

        Args:
            model: model to use
            modifiers: modifiers to use
            times: times for propagation
            _backup: whether this data should be classificed as backdata. Defaults to False.
            _delete_old_data: whether old data should be deleted. Defaults to True.
            _cache_generated_images: . Defaults to False.
            _print: whether progress information should be printed. Defaults to True.

        Raises:
            ValueError: if provided a times list of 0 items
        """
        import time

        # set output directories
        SRC_DIR = f"images/temp/{int(time.time())}"
        DST_DIR = "backup_images" if _backup else "images"

        # check times have been supplied
        n = len(times)
        if not n:
            raise ValueError(
                "Atleast 1 time must be provided to this function")

        if _print:
            print(
                f"Generating {n*len(modifiers)} images ({len(modifiers)} views for {n} different propagation times)")

        # setup generation timer
        timer = LapTimer(_n_target=n)

        for dt in times:
            # convert datetime to Skyfield Time
            t = ts.from_datetime(dt)

            # propagate satellites
            sat_frame = model.generate_sat_frame(t)

            # generate and save image for each modifier
            for idx, modifier in enumerate(modifiers):
                path = f"{SRC_DIR}/{idx}/{sat_frame.unix_timestamp_seconds}.png"
                sat_frame.render(modifier).to_png(path, _print=False)

            # timing code
            timer.lap()
            if _print:
                print(f"{timer.info():<80}", end="\r")

        if _print:
            print("\nImages generated")

        if _delete_old_data:
            if _print:
                print("Removing old data from device")
            # remove old data from device
            self.delete_dir_and_contents(DST_DIR + "/")

        if _print:
            print("Uploading images to device")

        # copy generated images to device
        self.copy_file_structure(SRC_DIR, DST_DIR)

        if _print:
            print("Upload complete")

        if not _cache_generated_images:
            from shutil import rmtree

            # delete generated images
            rmtree(SRC_DIR)

            if _print:
                print("Removed cached images")
