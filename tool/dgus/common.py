from ctypes import *
from enum import Enum, unique
from functools import total_ordering
import webcolors

# just for better documentation and BE support. No need to define __bool__(self)
class Bool(c_uint8):
    pass

@unique
class VP_Type(Enum):
    TEXT = -1
    BIT = -2
    NONE = 0
    BYTE = 1
    WORD = 2
    DWORD = 4
    QWORD = 8

class VP:
    def __init__(self, word_addr=None) -> None:
        self.addr = word_addr * 2 if word_addr is not None else None
        self.type = None

    def _set_bit_mode(self, bit):
        assert bit in range(16)
        self.size = 1
        if bit < 8:
            self.addr += 1
        else:
            bit -= 8
        self.bit = bit

    def set_type(self, type: VP_Type, *, bit=None, len=None, low_byte=None):
        assert self.type is None, f'type {self.type} already set'
        self.type = type
        if VP_Type.TEXT == type:
            self.size = len
        elif VP_Type.BIT == type:
            self._set_bit_mode(bit)
        elif VP_Type.BYTE == type:
            if low_byte:
                self.addr += 1
            self.size = 1
        else:
            self.size = type.value

    def set_from_vp_format_standard(self, vp_format: c_uint8):
        if 0 == vp_format:
            self.set_type(VP_Type.WORD)
        elif 1 == vp_format:
            self.set_type(VP_Type.BYTE, low_byte=False)
        elif 2 == vp_format:
            self.set_type(VP_Type.BYTE, low_byte=True)
        else:
            raise ValueError(vp_format)

    def set_from_vp_format_numeric(self, vp_format: c_uint8):
        if vp_format in (0, 5):
            self.set_type(VP_Type.WORD)
        elif vp_format in (1, 6):
            self.set_type(VP_Type.DWORD)
        elif 2 == vp_format:
            self.set_type(VP_Type.BYTE, low_byte=False)
        elif 3 == vp_format:
            self.set_type(VP_Type.BYTE, low_byte=True)
        elif 4 == vp_format:
            self.set_type(VP_Type.QWORD)
        else:
            raise ValueError(vp_format)

    def __str__(self) -> str:
        if self.type == VP_Type.BIT:
            return 'VP {:04x} b{}'.format(self.addr, self.bit)
        elif self.type == VP_Type.TEXT:
            return 'VP {:04x} T{:02x}'.format(self.addr, self.size)
        elif self.type == VP_Type.NONE:
            return ''
        else:
            return 'VP {:04x} +{:02x}'.format(self.addr, self.size)

    @property
    def end(self) -> int:
        return self.addr + self.size

class Pic(c_uint16):
    def __int__(self) -> int:
        return self.value

    def __eq__(self, other):
        return int(self) == int(other)

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

@total_ordering
class Position(c_uint16):
    def __int__(self) -> int:
        return self.value

    def __eq__(self, other):
        return int(self) == int(other)

    def __lt__(self, other):
        return int(self) < int(other)

    def __sub__(self, other):
        return int(self) - int(other)

    def __add__(self, other):
        return int(self) + int(other)

    def __str__(self) -> str:
        return '{:3}'.format(int(self))

@total_ordering
class Coord(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("x", Position),
                ("y", Position)]

    def __sub__(self, other):
        return Coord(self.x - other.x, self.y - other.y)

    def __getitem__(self, index):
        if 0 == index:
            return int(self.x)
        elif 1 == index:
            return int(self.y)
        else:
            raise IndexError()

    def __eq__(self, other):
        return self[0] == other[0] and self[1] == other[1]

    def __le__(self, other):
        return self[0] <= other[0] and self[1] <= other[1]

    def __str__(self) -> str:
        return '({},{})'.format(self.x, self.y)

class Area(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("start", Coord),
                ("end", Coord)]

    def size(self) -> Coord:
        return self.end - self.start

    def __str__(self) -> str:
        return '@{} +{}'.format(self.start, self.size())
