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

    def __mul__(self, other: int | float) -> "RGB":
        if not isinstance(other, (int, float)):
            return NotImplemented
        return RGB(
            R=int(self.R*other),
            G=int(self.G*other),
            B=int(self.B*other)
        )

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


WHITE = RGB(255, 255, 255)
BLACK = RGB(0, 0, 0)
RED = RGB(255, 0, 0)
GREEN = RGB(0, 255, 0)
BLUE = RGB(0, 0, 255)
BRIGHT_CYAN = RGB(0, 255, 255)   # High contrast, very bright
VIVID_ORANGE = RGB(255, 165, 0)   # Warm, clear distinction
BRIGHT_LIME = RGB(166, 226, 46)  # Neon-greenish, highly visible
MAGENTA = RGB(255, 0, 255)   # Pops well on dark
YELLOW = RGB(255, 255, 0)   # Classic highlight, very visible
SKY_BLUE = RGB(0, 191, 255)   # Softer than cyan, still clear
HOT_PINK = RGB(255, 105, 180)  # Feminine pop color
LIGHT_GRAY = RGB(211, 211, 211)  # Good neutral contrast
CHARTREUSE = RGB(127, 255, 0)   # Green-yellow, very distinct
CORAL_RED = RGB(255, 64, 64)   # Good warm hue
