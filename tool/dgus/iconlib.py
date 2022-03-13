import argparse
from mmap import *
from pathlib import Path
from ctypes import *
import re
from .common import *

class Icon(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("x_0", c_uint8),
                ("y_0", c_uint8),
                ("x_8", c_uint32, 2),
                ("y_8", c_uint32, 2),
                ("data_offset", c_uint32, 28),
                ("transparency", Color)]

    def is_valid(self):
        return self.data_offset != 0

    def __new__(cls, buf, off):
        return cls.from_buffer(buf, off)

    def __init__(self, buf, off) -> None:
        assert sizeof(self) == 0x8
        self.id = off // 0x8
        x = self.x_0 | self.x_8 << 8
        y = self.y_0 | self.y_8 << 8
        self.size = Coord(x, y)

    def __str__(self) -> str:
        return '{:3}: {} transparency {}'.format(self.id, self.size, self.transparency)

class IconLib:
    def __init__(self, filename : Path) -> None:
        m = re.fullmatch(r'(\d+)_(.+)', filename.stem)
        self.id = int(m.group(1))
        self.name = m.group(2)
        self.icons = []

    def __str__(self) -> str:
        return 'iconlib {} \'{}\' {} icons'.format(self.id, self.name, len(self.icons))

class Parser:
    def __init__(self, dirname):
        d = Path(dirname) / 'DWIN_SET'
        self.files = d.glob('*.ico')

    def __iter__(self):
        for filename in self.files:
            with open(filename, 'r+b') as f:
                mm = mmap(f.fileno(), 0)
                lib = IconLib(filename)

                off = 0
                while off < min(len(mm), 256*1024):
                    t = Icon(mm, off)
                    if not t.is_valid():
                        break
                    off += sizeof(t)
                    lib.icons.append(t)

                yield lib


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('basedir', nargs='?', type=Path, default='../dgusm')
    args = parser.parse_args()
    for lib in Parser(args.basedir):
        print(lib)
        for icon in lib.icons:
            print('  ', icon)
