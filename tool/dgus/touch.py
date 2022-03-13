import argparse
from mmap import *
from pathlib import Path
from ctypes import *
from .common import *

class TouchArea(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("pic", Pic),
                ("area", Area),
                ("pic_next", Pic),
                ("pic_press", Pic),
                ("type", c_uint8),
                ("subtype", c_uint8)]

    type_map = {}

    def __init_subclass__(cls) -> None:
        cls.type_map.update(dict.fromkeys(cls.type_codes, cls))

    def get_subclass(self) -> object:
        return self.type_map[self.type]

    def __new__(cls, buf, off):
        return cls.from_buffer(buf, off)

    def __init__(self, buf, off) -> None:
        assert sizeof(TouchArea) == 0x10

    def __str__(self) -> str:
        return '{} {}'.format(self.pic, self.area)

class Key:
    special_keycodes = {
        0xf0: 'cancel',
        0xf1: 'return',
        0xf2: 'backspace',
        0xf3: 'delete',
        0xf4: 'capslock',
        0xf7: 'left',
        0xf8: 'right',
    }

    def __init__(self, code) -> None:
        self.code = code

    def __str__(self) -> str:
        if self.code in self.special_keycodes:
            return self.special_keycodes[self.code]
        elif chr(self.code).isprintable():
            return chr(self.code)
        else:
            return ':0x{:02x}'.format(self.code)

class NumpadKey(TouchArea):
    type_codes = (0x00,)

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.key = Key(self.subtype)

    def __str__(self) -> str:
        return '{} numpad:{}'.format(super().__str__(), self.key)

class KeyboardKey(TouchArea):
    type_codes = range(1, 0x80)

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.upper = Key(self.type)
        self.lower = Key(self.subtype)

    def __str__(self) -> str:
        return '{} keyboard:⇩{}⇧{}'.format(super().__str__(), self.lower, self.upper)

class TouchControl(TouchArea):
    _pack_ = 1
    _fields_ = [("_continue0", c_uint8),
                ("vp_word", c_uint16)]

    type_codes = (0xfd, 0xfe)
    subtypes = {}

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.vp = VP(self.vp_word)
        if self.__class__ is not TouchControl:
            assert sizeof(self) in (0x20, 0x30, 0x40)

    def __init_subclass__(cls) -> None:
        cls.subtypes[cls.subtype_code] = cls

    def get_subclass(self) -> object:
        return self.subtypes[self.subtype]

    def __str__(self) -> str:
        return '{} ctl:{:<9} {}'.format(super().__str__(), self.__class__.__name__, self.vp)

class Numpad(TouchControl):
    subtype_code = 0x00
    _pack_ = 1
    _fields_ = [("vp_format", c_uint8),
                ("int_digits", c_uint8),
                ("dec_digits", c_uint8),
                ("cursor_pos", Coord),
                ("font_color", Color),
                ("font", c_uint8),
                ("font_x", c_uint8),
                ("cursor_white", Bool),
                ("unmasked", Bool),
                ("_continue1", c_uint8),
                ("kbd_elsewhere", Bool),
                ("kbd_pic", Pic),
                ("kbd_area", Area),
                ("kbd_pos", Coord),
                ("_continue2", c_uint8),
                ("limits_en", Bool),
                ("limit_min", c_int32),
                ("limit_max", c_int32),
                ("_reserved", c_uint8 * 6)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        if 0 == self.vp_format:
            self.vp.size = 2
        elif 1 == self.vp_format:
            self.vp.size = 4
        elif 2 == self.vp_format:
            self.vp.size = 1
        elif 3 == self.vp_format:
            self.vp.addr += 1
            self.vp.size = 1
        elif 4 == self.vp_format:
            self.vp.size = 8
        else:
            raise ValueError(self.vp_format)

class Increment(TouchControl):
    subtype_code = 0x02
    _pack_ = 1
    _fields_ = [("bit_mode", Bool, 4),
                ("vp_format", c_uint8, 4),
                ("add", Bool),
                ("loop_range", Bool),
                ("step", c_uint16),
                ("min", c_uint16),
                ("max", c_uint16),
                ("disable_repeat", Bool),
                ("_reserved", c_uint8 * 3)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        if self.bit_mode:
            self.vp.set_bit_mode(self.vp_format)
        else:
            if 0 == self.vp_format:
                self.vp.size = 2
            elif 1 == self.vp_format:
                self.vp.size = 1
            elif 2 == self.vp_format:
                self.vp.addr += 1
                self.vp.size = 1
            else:
                raise ValueError(self.vp_format)

class Slider(TouchControl):
    subtype_code = 0x03
    _pack_ = 1
    _fields_ = [("vp_format", c_uint8, 4),
                ("vertical", Bool, 4),
                ("area", Area),
                ("min", c_uint16),
                ("max", c_uint16)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        if 0 == self.vp_format:
            self.vp.size = 2
        elif 1 == self.vp_format:
            self.vp.size = 1
        elif 2 == self.vp_format:
            self.vp.addr += 1
            self.vp.size = 1
        else:
            raise ValueError(self.vp_format)

class Button(TouchControl):
    subtype_code = 0x05
    _pack_ = 1
    _fields_ = [("bit_mode", Bool, 4),
                ("vp_format", c_uint8, 4),
                ("keycode", c_uint16),
                ("_reserved", c_uint8 * 10)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        if self.bit_mode:
            self.vp.set_bit_mode(self.vp_format)
        else:
            if 0 == self.vp_format:
                self.vp.size = 2
            elif 1 == self.vp_format:
                self.vp.size = 1
            elif 2 == self.vp_format:
                self.vp.addr += 1
                self.vp.size = 1
            else:
                raise ValueError(self.vp_format)

class Keyboard(TouchControl):
    subtype_code = 0x06
    _pack_ = 1
    _fields_ = [("vp_len_words", c_uint8),
                ("modify", Bool),
                ("font", c_uint8),
                ("font_x", c_uint8),
                ("font_y", c_uint8),
                ("cursor_white", Bool),
                ("color", Color),
                ("text_pos", Coord),
                ("use_len_prefix", Bool),
                ("_continue1", c_uint8),
                ("text_pos_end", Coord),
                ("kbd_elsewhere", Bool),
                ("kbd_pic", Pic),
                ("kbd_area", Area),
                ("_continue2", c_uint8),
                ("kbd_pos", Coord),
                ("unmasked", Bool),
                ("_reserved", c_uint8 * 10)]

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        #FIXME: is this +1 correct?
        self.vp.size = (self.vp_len_words + 1) * 2
        if self.use_len_prefix:
            self.vp.addr -= 2
            self.vp.size += 2

class Parser:
    @staticmethod
    def make_class(mm, off) -> object:
        touch = TouchArea(mm, off)
        while True:
            t = touch.get_subclass()
            if t == touch.__class__:
                return touch
            touch = t(mm, off)

    def __init__(self, dirname):
        d = Path(dirname) / 'DWIN_SET'
        filename = next(d.glob('13*.bin'))

        with open(filename, 'r+b') as f:
            # cannot be read-only if we want to use the buffer directly
            #mm = mmap(f.fileno(), 0, access=ACCESS_READ)
            self.mm = mmap(f.fileno(), 0)
            # print(filename, 'len', len(mm))

            assert self.mm[-2:] == b'\xff\xff', "file should end in 0xffff"

    def __iter__(self):
        off = 0
        while off + 2 < len(self.mm):
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
