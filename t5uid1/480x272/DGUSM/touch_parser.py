# from struct import *

# class TouchControl:
#     decoder = Struct('>H HHHH HHH')

#     def __init__(buf):
#         (self.pic, self.Xstart, self.Ystart, self.Xend, self.Yend, self.pic_next, self.pic_touched, self.type, self.subtype) = decoder.unpack(buf)

from logging.config import valid_ident
from mmap import *
from pathlib import Path
from ctypes import *
from turtle import textinput

class Coord(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("x", c_uint16),
                ("y", c_uint16)]

    def __str__(self) -> str:
        return '({}, {})'.format(self.x, self.y)

class Area(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("start", Coord),
                ("end", Coord)]
    def __str__(self) -> str:
        return 'start:{} size:{}'.format(self.start, self.end - self.start)

class TouchArea(BigEndianStructure):
    _pack_ = 1
    _fields_ = [("pic", c_uint16),
                ("area", Area),
                ("pic_next", c_uint16),
                ("pic_press", c_uint16),
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
        pass

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
            return':0x{:02x}'.format(self.code)

class KeypadKey(TouchArea):
    type_codes = (0x00,)

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.key = Key(self.subtype)

    def __str__(self) -> str:
        return 'keypad:{}'.format(self.key)

class KeyboardKey(TouchArea):
    type_codes = range(1, 0x7f)

    def __init__(self, buf, off) -> None:
        super().__init__(buf, off)
        self.upper = Key(self.type)
        self.lower = Key(self.subtype)

    def __str__(self) -> str:
        return 'keyboard:⇩{}⇧{}'.format(self.lower, self.upper)

class TouchControl(TouchArea):
    _pack_ = 1
    _fields_ = [("_continue0", c_uint8),
                ("vp", c_uint16)]

    type_codes = (0xfd, 0xfe)
    subtypes = {}

    def __init_subclass__(cls) -> None:
        cls.subtypes[cls.subtype_code] = cls

    @classmethod
    def debug_print_sizes(cls):
        assert sizeof(TouchArea) == 0x10
        for v in cls.subtypes.values():
            print(v.__name__, sizeof(v))
            assert sizeof(v) in (0x20, 0x30, 0x40)

    def get_subclass(self) -> object:
        return self.subtypes[self.subtype]

    def __str__(self) -> str:
        return 'control:{}'.format(self.__class__.__name__)

class NumericInput(TouchControl):
    subtype_code = 0x00
    _pack_ = 1
    _fields_ = [("vp_format", c_uint8),
                ("int_digits", c_uint8),
                ("dec_digits", c_uint8),
                ("cursor_pos", Coord),
                ("font_color", c_uint16),
                ("font", c_uint8),
                ("font_x", c_uint8),
                ("cursor_color", c_uint8),
                ("unmasked", c_uint8),
                ("_continue1", c_uint8),
                ("kbd_elsewhere", c_uint8),
                ("kbd_pic", c_uint16),
                ("kbd_area", Area),
                ("kbd_pos", Coord),
                ("_continue2", c_uint8),
                ("limits_en", c_uint8),
                ("limit_min", c_int32),
                ("limit_max", c_int32),
                ("_reserved", c_uint8 * 6)]

class SliderInput(TouchControl):
    subtype_code = 0x03
    _pack_ = 1
    _fields_ = [("vp_format", c_uint8, 4),
                ("direction", c_uint8, 4),
                ("area", Area),
                ("min", c_uint16),
                ("max", c_uint16)]

class ButtonInput(TouchControl):
    subtype_code = 0x05
    _pack_ = 1
    _fields_ = [("bit_mode", c_uint8, 4),
                ("vp_format", c_uint8, 4),
                ("keycode", c_uint16),
                ("_reserved", c_uint8 * 10)]

class TextInput(TouchControl):
    subtype_code = 0x06
    _pack_ = 1
    _fields_ = [("vp_len_words", c_uint8),
                ("modify", c_uint8),
                ("font", c_uint8),
                ("font_x", c_uint8),
                ("font_y", c_uint8),
                ("cursor_color", c_uint8),
                ("color", c_uint16),
                ("text_pos", Coord),
                ("prefix_len", c_uint8),
                ("_continue1", c_uint8),
                ("text_pos_end", Coord),
                ("kbd_elsewhere", c_uint8),
                ("kbd_pic", c_uint16),
                ("kbd_area", Area),
                ("_continue2", c_uint8),
                ("kbd_pos", Coord),
                ("unmasked", c_uint8),
                ("_reserved", c_uint8 * 10)]

class Parser:
    def make_class(self, mm, off) -> object:
        touch = TouchArea(mm, off)
        while True:
            t = touch.get_subclass()
            if t == touch.__class__:
                return touch
            touch = t(mm, off)

    def __init__(self, dirname):
        d = Path(dirname) / 'DWIN_SET'
        filename = next(d.glob('13*.bin'))

        #TouchControl.debug_print_sizes()

        self.controls = []

        with open(filename, 'r+b') as f:
            #mm = mmap(f.fileno(), 0, access=ACCESS_READ)
            mm = mmap(f.fileno(), 0)
            # print(filename, 'len', len(mm))

            assert mm[-2:] == b'\xff\xff', "file should end in 0xffff"

            off = 0
            while off + 2 < len(mm):
                # print('off: {:04x}'.format(off))
                t = self.make_class(mm, off)
                off += sizeof(t)
                print(t)
                self.controls.append(t)


if __name__ == "__main__":
    p = Parser('.')
