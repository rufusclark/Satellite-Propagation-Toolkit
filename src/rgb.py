"""represents a single RGB pixel"""
from typing_extensions import Self


class RGB:
    def __init__(self, R: int = 0, G: int = 0, B: int = 0) -> None:
        self.R = max(0, min(255, R))
        self.G = max(0, min(255, G))
        self.B = max(0, min(255, B))

    @classmethod
    def random(cls) -> Self:
        from random import randint
        return cls(randint(0, 255), randint(0, 255), randint(0, 255))

    def is_off(self) -> bool:
        return self.R == self.G == self.B == 0

    def to_tuple(self) -> tuple[int, int, int]:
        return self.R, self.G, self.B

    def __repr__(self) -> str:
        return f"<RGB {self.R, self.G, self.B}>"

    def __eq__(self, other: Self) -> bool:
        return self.R == other.R and self.G == other.G and self.B == other.B

    def __add__(self, other: Self) -> Self:
        self.R = max(0, min(255, self.R + other.R))
        self.G = max(0, min(255, self.G + other.G))
        self.B = max(0, min(255, self.B + other.B))
        return self

    def info(self) -> str:
        out = ""
        if self.R:
            out += f"red (+{self.R})"
        if self.G:
            out += f"green (+{self.G})"
        if self.B:
            out += f"blue (+{self.B})"
        return out
