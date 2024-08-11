"""Contains tools for measuring process progress"""
from time import monotonic


class LapTimer:
    """LapTimer supports timing and counting loops
    """

    def __init__(self, *, _n_target: int = 0) -> None:
        """creates a new LapTimer object

        if _n_target is provided, this will represent the total number of laps to complete this task and the `LapTimer.info()` method will provided information about progress and the estimated time until completion
        """
        self.n = 0
        """lap count"""
        self.t00 = 0
        """start time"""
        self.t0 = 0
        """lap start time"""
        self.d0 = 0
        """lap time"""
        self.n_target = _n_target
        """total laps - expected to be completed"""
        self.reset()

    def reset(self) -> None:
        """reset and start the timer

        this call is redundent if `__init__` has just been called
        """
        self.n = 0
        t = monotonic()
        self.t00 = t
        self.t0 = t

    def lap(self) -> None:
        """lap the timer

        this increments the timer and saves the time of the last lap
        """
        self.n += 1
        t = monotonic()
        self.d0 = t - self.t0
        self.t0 = t

    @property
    def last(self) -> float:
        """last lap time"""
        return self.d0

    @property
    def avg(self) -> float:
        """average lap time since start"""
        return (self.t0 - self.t00)/self.n

    @property
    def rate(self) -> float:
        """average rate since start"""
        return 1/self.avg

    @property
    def n_remaining(self) -> int:
        """remaining laps"""
        return self.n_target - self.n

    @property
    def percentage_complete(self) -> float:
        """percentage of target laps complete"""
        if self.n_target:
            return min((self.n / self.n_target) * 100, 100)
        else:
            return 100

    @property
    def remaining_seconds(self) -> float:
        """remaining time to complete total laps in seconds"""
        return max(self.n_remaining * self.avg, 0)

    def fmt_remaining_time(self) -> str:
        """string formatted remaining time reading to be displayed"""
        t = self.remaining_seconds
        if t > 60:
            if t > 3600:
                return f"{int(t//3600)}h {int((t-3600)//60)}m {int(t%60)}s"
            else:
                return f"{int(t//60)}m {int(t%60)}s"
        else:
            return f"{int(t)}s"

    def info(self) -> str:
        """return a str output containing the last, avg and rate for printing

        Returns:
            formatted string ready to print
        """
        if self.n_target:
            return f"Progress: {self.percentage_complete:.0f}%, Remaining Time: {self.fmt_remaining_time()} (Last: {self.last:.3f}s, Avg: {self.avg:.3f}s, Rate: {self.rate:.3f}/s)"
        else:
            return f"Last: {self.last:.3f}s, Avg: {self.avg:.3f}s, Rate: {self.rate:.3f}/s"
