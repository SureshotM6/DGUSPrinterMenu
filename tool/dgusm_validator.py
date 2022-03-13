#!/usr/bin/env python3

import argparse
from collections import defaultdict
from pathlib import Path
import sys
import bisect

from numpy import isin
from dgus import touch, display, iconlib, pages as dpages
from dgus.common import VP, VP_Type

TOTAL_RAM = 4096
MAX_PAGE = 374 - 1
RESOLUTION = (480, 272)
MAX_ICON_DIMS = (255, 255)

dcontrols = []
tcontrols = []
pages = {}
iconlibs = {}
ramlist = []

def info(*str):
    print('INFO:', *str)

def warn(*str):
    print('WARNING:', *str, file=sys.stderr)

def err(*str):
    print('ERROR:', *str, file=sys.stderr)

def check(cond, *str) -> bool:
    if cond:
        return True
    err(*str)
    return False

def check_eq(a, b, *str) -> bool:
    return check(a == b, *str, f'DURING ASSERT({a} == {b})')

def check_neq(a, b, *str) -> bool:
    return check(a != b, *str, f'DURING ASSERT({a} != {b})')

def check_leq(a, b, *str) -> bool:
    return check(a <= b, *str, f'DURING ASSERT({a} <= {b})')

class FakeApControl:
    def __init__(self, control) -> None:
        self.control = control
        self.vp = control.ap

    def __str__(self) -> str:
        return f'AUX_PTR of [{self.control}]'

def populate_ram():
    aux_ptrs = []
    for c in dcontrols:
        if not hasattr(c, 'ap'):
            continue
        aux_ptrs.append(FakeApControl(c))

    for c in [*dcontrols, *tcontrols, *aux_ptrs]:
        if not hasattr(c, 'vp') or c.vp.size == 0:
            continue
        ramlist.append(c)

    ramlist.sort(key=lambda c: c.vp.addr)

def check_vp_ram_size():
    last = ramlist[-1]
    check_leq(last.vp.end, TOTAL_RAM, f'last VP past end of RAM: {last}')

def one_isinstance(cls, *x) -> bool:
    for c in x:
        if isinstance(c, cls):
            return True
    return False

def allow_paired_controls(a, b, cls1, cls2) -> bool:
    return (isinstance(a, cls1) and isinstance(b, cls2)) or \
        (isinstance(a, cls2) and isinstance(b, cls1))

def check_vp_overlap():
    last = ramlist[0]
    for c in ramlist[1:]:
        if c.vp.addr < last.vp.end:
            if check_eq(c.vp.type, last.vp.type, f'VP usage mismatch [{c}] <=> [{last}]'):
                # address overlap of same types
                check_eq(c.vp.addr, last.vp.addr, f'VP addr mismatch [{c}] <=> [{last}]')
                check_eq(c.vp.size, last.vp.size, f'VP size mismatch [{c}] <=> [{last}]')
                if c.__class__ != last.__class__:
                    # this should be allowed for some items (control vs display for example)
                    if allow_paired_controls(c, last, touch.Increment, display.Numeric):
                        pass
                    elif allow_paired_controls(c, last, touch.Slider, touch.Button): # min/max buttons
                        pass
                    elif allow_paired_controls(c, last, display.Slider, display.Icon): # 'track' slider
                        pass
                    else:
                        err(f'VP control type mismatch [{c}] <=> [{last}]')
                elif isinstance(c, FakeApControl):
                    err(f'AUX_PTRs cannot overlap: [{c}] <=> [{last}]')

                #info(f'VP overlap "{last}" <=> "{c}"')
        last = c

def check_unique_keycodes():
    keycodes = defaultdict(dict)
    for c in tcontrols:
        if not hasattr(c, 'keycode'):
            continue
        addrdict = keycodes[c.vp.addr]
        if c.keycode in addrdict:
            # allow if on different pages
            other = addrdict[c.keycode]
            if c.pic == other.pic:
                err(f'duplicate keycode {c.keycode:04x} at addr {c.vp.addr:04x} [{c}] <=> [{addrdict[c.keycode]}]')
        else:
            addrdict[c.keycode] = c

def check_textbox_sizes():
    for c in dcontrols:
        if not isinstance(c, display.Text):
            continue
        check_eq(c.x_px * 2, c.y_px, f'TextBox char x/y sizes wrong [{c}]')
        line_height = c.y_px + c.y_tracking_px
        if int(c.area.size().y) < c.y_px:
            lines = 0
        else:
            lines = 1 + (c.area.size().y - c.y_px) // line_height
        check_eq((c.area.size().y - c.y_px) % line_height, 0, f'box is wrong height {c}')
        needed_width = c.length * (c.x_px + c.x_kerning_px)
        width = int(c.area.size().x) * lines
        if c.monospace:
            check_eq(width, needed_width, f'monospaced textbox incorrect size ({width}px != {needed_width}px) [{c}]')
        elif width < needed_width:
            warn(f'non-monospaced textbox possibly too small ({width}px < {needed_width}px): [{c}]')

def check_unsupported_numerics():
    for c in ramlist:
        check_neq(c.vp.type, VP_Type.QWORD, f'QWORDs are not supported: [{c}]')


def populate_pages(dir):
    for p in dpages.Parser(dir):
        pages[int(p.pic)] = p

def populate_icons(dir):
    for i in iconlib.Parser(dir):
        iconlibs[i.id] = i

def check_pages():
    maxpage = max(pages.keys())
    check_leq(maxpage, MAX_PAGE, f'page id {maxpage} too large')
    for p in pages.values():
        check_eq(p.size, RESOLUTION, f'resolution mismatch {p}')

def check_icons():
    for lib in iconlibs.values():
        for i in lib.icons:
            check_leq(i.size, MAX_ICON_DIMS, f'icon {i} in {lib} too large')

def check_control_page_usage():
    for c in [*dcontrols, *tcontrols]:
        check(int(c.pic) in pages, f'bad pic for [{c}]')

def check_icon_property(lib, c, prop):
    # unused icons should be set to 0 which should always exist in lib
    if hasattr(c, prop):
        check_leq(getattr(c, prop), len(lib.icons) - 1, f'bad icon index in [{c}]')

def check_control_icon_usage():
    for c in dcontrols:
        if not hasattr(c, 'icon_lib'):
            continue

        if not check(c.icon_lib in iconlibs, f'bad iconlib for [{c}]'):
            continue

        lib = iconlibs[c.icon_lib]

        check_icon_property(lib, c, 'icon')
        check_icon_property(lib, c, 'icon_min')
        check_icon_property(lib, c, 'icon_max')
        check_icon_property(lib, c, 'icon0s')
        check_icon_property(lib, c, 'icon0e')
        check_icon_property(lib, c, 'icon1s')
        check_icon_property(lib, c, 'icon1e')

def check_font_encoding():
    for c in dcontrols:
        if not hasattr(c, 'encoding'):
            continue
        if c.encoding == 0:
            continue
        warn(f'font encoding {c.encoding} should probably be 0 (8-bit): [{c}]')

def check_fontlib_property(c, prop):
    # unused icons should be set to 0 which should always exist in lib
    if hasattr(c, prop):
        check_eq(getattr(c, prop), 0, f'bad fontlib in [{c}]')

def check_fontlibs():
    for c in [*dcontrols, *tcontrols]:
        check_fontlib_property(c, 'font')
        check_fontlib_property(c, 'font_ascii')
        check_fontlib_property(c, 'font_nonascii')

### main ###
parser = argparse.ArgumentParser()
parser.add_argument('basedir', nargs='?', type=Path, default='../dgusm')
args = parser.parse_args()

# read everything in
tcontrols = list(touch.Parser(args.basedir))
dcontrols = list(display.Parser(args.basedir))
populate_pages(args.basedir)
populate_icons(args.basedir)
populate_ram()

# do actual validation
check_pages()
check_icons()
check_vp_ram_size()
check_vp_overlap()
check_unique_keycodes()
check_textbox_sizes()
check_unsupported_numerics()
check_control_page_usage()
check_control_icon_usage()
check_font_encoding()
check_fontlibs()

#TODO:
# add fontlib check?
