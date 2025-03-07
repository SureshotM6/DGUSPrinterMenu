import argparse
from mmap import *
from pathlib import Path
from ctypes import *
from .common import *

class DisplayVariable(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("valid", c_uint8),
                ("type", c_uint8),
                ("sp_word", c_uint16),
                ("desc_len_words", c_uint16),
                ("vp_word", c_uint16)]

    type_map = {}

    def __init_subclass__(cls) -> None:
        cls.type_map[cls.type_code] = cls

    def get_subclass(self) -> object:
        return self.type_map[self.type]

    def __new__(cls, buf, off):
        return cls.from_buffer(buf, off)

    def __init__(self, buf, off) -> None:
        assert self.valid == 0x5a, f'bad magic: 0x{self.valid:02x} off 0x{off:x}'
        if self.__class__ is not DisplayVariable:
            assert sizeof(self) == 0x20, '{} has bad size 0x{:x}'.format(self.__class__.__name__, sizeof(self))
        assert self.sp_word == 0xffff, f'SP not supported yet: 0x{self.sp_word:04x} off 0x{off:x}'
        self.vp = VP(self.vp_word)
        self.pic = Pic(off // 0x800)

    def __str__(self) -> str:
        return '{} {} {:<7} {}'.format(self.pic, self.area, self.__class__.__name__, self.vp)

class Icon(DisplayVariable):
    type_code = 0x00
    _pack_ = 1
    _fields_ = [("pos", Coord),
                ("val_min", c_uint16),
                ("val_max", c_uint16),
                ("icon_min", c_uint16),
                ("icon_max", c_uint16),
                ("icon_lib", c_uint8),
                ("opaque", Bool),
                ("_reserved", c_uint8 * 10)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        # would need to parse icons to get real area
        self.area = Area(self.pos, self.pos)
        self.vp.set_type(VP_Type.WORD)

class ImageAnimation(DisplayVariable):
    type_code = 0x04
    _pack_ = 1
    _fields_ = [("pic_begin", Pic),
                ("pic_end", Pic),
                ("frame_time_8ms", c_uint8),
                ("_reserved", c_uint8 * 0x13)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.vp.set_type(VP_Type.NONE)

    def __str__(self) -> str:
        return '{} {} {} to {} every {} ms'.format(
            self.pic,
            self.__class__.__name__,
            self.pic_begin,
            self.pic_end,
            self.frame_time_8ms * 8)

class Slider(DisplayVariable):
    type_code = 0x02
    _pack_ = 1
    _fields_ = [("val_min", c_uint16),
                ("val_max", c_uint16),
                ("xy_begin", Position),
                ("xy_end", Position),
                ("icon", c_uint16),
                ("yx", Position),
                ("adj_left_top", c_uint8),
                ("vertical", Bool),
                ("icon_lib", c_uint8),
                ("opaque", Bool),
                ("vp_format", c_uint16),
                ("_reserved", c_uint8 * 6)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        if self.vertical:
            self.pos = Coord(self.yx, self.xy_begin)
            self.end = Coord(self.yx, self.xy_end)
        else:
            self.pos = Coord(self.xy_begin, self.yx)
            self.end = Coord(self.xy_end, self.yx)

        #TODO: take adj_left_top into account?
        assert self.adj_left_top == 0

        self.area = Area(self.pos, self.end)

        self.vp.set_from_vp_format_standard(self.vp_format)

class BitIcon(DisplayVariable):
    type_code = 0x06
    _pack_ = 1
    _fields_ = [("vp_aux_ptr_word", c_uint16), # also called AP, 2 words
                ("bitmask", c_uint16),
                ("mode", c_uint8),
                ("arrangement", c_uint8),
                ("opaque", Bool),
                ("icon_lib", c_uint8),
                ("icon0s", c_uint16),
                ("icon0e", c_uint16),
                ("icon1s", c_uint16),
                ("icon1e", c_uint16),
                ("pos", Coord),
                ("spacing", Position),
                ("_reserved", c_uint8 * 2)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        # multiple spaced icons aren't supported yet
        assert bin(self.bitmask).count('1') == 1
        assert int(self.spacing) == 0, self.spacing

        # would need to parse icons to get real area
        self.area = Area(self.pos, self.pos)

        # compute size based on self.bitmask
        if bin(self.bitmask).count('1') == 1:
            self.vp.set_type(VP_Type.BIT, bit=self.bitmask.bit_length() - 1)
        elif self.bitmask & 0xff == 0:
            self.vp.set_type(VP_Type.BYTE, low_byte=False)
        elif self.bitmask & 0xff00 == 0:
            self.vp.set_type(VP_Type.BYTE, low_byte=True)

        self.ap = VP(self.vp_aux_ptr_word)
        self.ap.size = 4
        #assert self.vp_aux_ptr_word == self.vp_word + 1
        #self.vp_size = 6

class Numeric(DisplayVariable):
    type_code = 0x10
    _pack_ = 1
    _fields_ = [("text_pos", Coord),
                ("color", Color),
                ("font", c_uint8),
                ("x_px", c_uint8),
                ("alignment", c_uint8),
                ("int_digits", c_uint8),
                ("dec_digits", c_uint8),
                ("vp_format", c_uint8),
                ("suffix_len", c_uint8),
                ("_suffix", c_char * 11)]

    def num_chars(self):
        decimalpoint = 1 if self.dec_digits > 0 else 0
        return min(self.int_digits, 1) + self.dec_digits + decimalpoint

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.suffix = self._suffix[:self.suffix_len].decode('ascii')
        self.y_px = self.x_px * 2

        self.area = Area(self.text_pos, self.text_pos)
        self.area.end.y += self.y_px
        self.area.end.x += self.x_px * self.num_chars()

        self.vp.set_from_vp_format_numeric(self.vp_format)

    def __str__(self) -> str:
        return '{} {}.{} digits {}x{}px suffix \'{}\' {}'.format(
            super().__str__(),
            self.int_digits, self.dec_digits,
            self.x_px, self.y_px,
            self.suffix,
            self.color)

class Text(DisplayVariable):
    type_code = 0x11
    _pack_ = 1
    _fields_ = [("text_pos", Coord),
                ("color", Color),
                ("area", Area),
                ("length", c_uint16),
                ("font_ascii", c_uint8),
                ("font_nonascii", c_uint8), # documentation is ambiguous
                ("x_px", c_uint8),
                ("y_px", c_uint8),
                ("monospace", Bool, 1),
                ("encoding", c_uint8, 7),
                ("x_kerning_px", c_uint8),
                ("y_tracking_px", c_uint8),
                ("_reserved", c_uint8)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.vp.set_type(VP_Type.TEXT, len=self.length)

    def __str__(self) -> str:
        return '{} {:2} chars {}x{}px {} {}'.format(
            super().__str__(),
            self.vp.size,
            self.x_px, self.y_px,
            "monospace" if self.monospace else "variable",
            self.color)

class Curve(DisplayVariable):
    type_code = 0x20
    _pack_ = 1
    _fields_ = [("area", Area),
                ("y_center", Position),
                ("value_center", c_uint16),
                ("color", Color),
                ("_y_scale256th", c_uint16),
                ("channel", c_uint8),
                ("x_spacing", c_uint8),
                ("_reserved", c_uint8 * 6)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.vp.set_type(VP_Type.NONE)
        self.y_scale = self._y_scale256th / 256

    def __str__(self) -> str:
        return '{} y_center {}@{} scale {}x{:.03f} channel {} {}'.format(
            super().__str__(),
            self.value_center, self.y_center,
            self.x_spacing, self.y_scale,
            self.channel,
            self.color)

class Parser:
    @staticmethod
    def make_class(mm, off) -> object:
        touch = DisplayVariable(mm, off)
        while True:
            t = touch.get_subclass()
            if t == touch.__class__:
                return touch
            touch = t(mm, off)

    def __init__(self, dirname):
        d = Path(dirname) / 'DWIN_SET'
        filename = next(d.glob('14*.bin'))

        with open(filename, 'r+b') as f:
            # cannot be read-only if we want to use the buffer directly
            #mm = mmap(f.fileno(), 0, access=ACCESS_READ)
            self.mm = mmap(f.fileno(), 0)
            # print(filename, 'len', len(self.mm))

    def __iter__(self):
        off = 0
        while off < len(self.mm):
            if 0x00 == self.mm[off]:
                off += 0x20
                continue
            # print('off: {:04x}'.format(off))
            t = self.make_class(self.mm, off)
            off += sizeof(t)
            yield t


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('basedir', nargs='?', type=Path, default='../dgusm')
    args = parser.parse_args()
    for c in Parser(args.basedir):
        print(c)
