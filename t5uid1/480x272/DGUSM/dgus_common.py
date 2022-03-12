from ctypes import *
import webcolors

# just for better documentation and BE support. No need to define __bool__(self)
class Bool(c_uint8):
    pass

class VP:
    def __init__(self, word_addr=None, size=None) -> None:
        self.addr = word_addr * 2 if word_addr is not None else None
        self.size = size
        self.bit = None

    def set_bit_mode(self, bit):
        assert self.bit is None and bit in range(16)
        self.bit = bit
        self.size = 1
        if bit < 8:
            self.addr_bytes += 1
        else:
            bit -= 8

    def __str__(self) -> str:
        if self.bit is None:
            return 'VP {:04x} +{:02x}'.format(self.addr, self.size)
        else:
            return 'VP {:04x} b{}'.format(self.addr, self.bit)

class Pic(c_uint16):
    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return 'P{:<3}'.format(int(self.value))

class Color(c_uint16):
    def r(self) -> int:
        msb = ((self.value & 0xf800) >> 11) << 3
        return msb | msb >> 5

    def g(self) -> int:
        msb = ((self.value & 0x07e0) >> 5) << 2
        return msb | msb >> 6

    def b(self) -> int:
        msb = (self.value & 0x001f) << 3
        return msb | msb >> 5

    def rgb(self):
        return (self.r(), self.g(), self.b())

    def hex24(self) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*self.rgb())

    def closest_name(self) -> str:
        r, g, b = self.rgb()
        min_rank = float('inf')
        chosen = '?'
        for key, name in webcolors.CSS3_HEX_TO_NAMES.items():
            cr, cg, cb = webcolors.hex_to_rgb(key)
            rank = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if (rank < min_rank):
                min_rank = rank
                chosen = name
        return chosen

    def __str__(self) -> str:
        return '{}~{}'.format(self.hex24(), self.closest_name())

class Position(c_uint16):
    def __int__(self) -> int:
        return self.value

    def __sub__(self, other):
        return int(self) - int(other)

    def __add__(self, other):
        return int(self) + int(other)

    def __str__(self) -> str:
        return '{:3}'.format(int(self))

class Coord(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("x", Position),
                ("y", Position)]

    def __sub__(self, other):
        return Coord(self.x - other.x, self.y - other.y)

    def __str__(self) -> str:
        return '({},{})'.format(self.x, self.y)

class Area(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("start", Coord),
                ("end", Coord)]

    def __str__(self) -> str:
        return '@{} +{}'.format(self.start, self.end - self.start)
