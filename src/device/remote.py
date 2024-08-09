"""Handles remote control of the Pico to write files to the filesystem and set time"""
# ! WARNING ! For some rather frustrating reason pyboard is not distributed well anywhere and is instead downloaded as a script from GitHub go figure. https://docs.micropython.org/en/latest/reference/pyboard.py.html# https://github.com/micropython/micropython/blob/master/tools/pyboard.py pyserial is the only dependency of this code
# TODO: Warning if the device hangs reinsert it
# BUG: Can hang if already been executed and called again

from .pyboard import Pyboard
from .tools import autoport
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

        print(f"Connect to device on port {port}")

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

    def copy_file_structure(self, src: str, dst: str) -> None:
        """copy the file structure from the PC to the remote fs

        Args:
            src: filepath of the folder to be copied, not including the root folder name
            dst: root filepath for desination. Defaults to "".
        """
        from pathlib import Path
        rootdir = Path(src)
        self._create_dir_if_not_exist(dst)
        for f in rootdir.rglob("*"):
            src_path = f.as_posix()
            dst_path = dst + "/" + src_path.removeprefix(src)
            if f.is_dir():
                # create file if not exists
                self._create_dir_if_not_exist(dst_path)
                print(f"Create remote dir, {dst_path}")
            elif f.is_file():
                # copy file
                self.put(src_path, dst_path)
                print(
                    f"Copied host file ({src_path}) to remote ({dst_path})")

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
