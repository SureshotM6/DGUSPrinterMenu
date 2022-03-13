import argparse
from pathlib import Path
from PIL import Image
from .common import *

class Page:
    def __init__(self, filename : Path) -> None:
        self.pic = Pic(int(filename.stem[:3]))
        self.name = filename.stem[4:]
        img = Image.open(filename)
        assert img.format == 'BMP'
        assert img.mode == 'RGB'
        assert img.info['compression'] == 0
        self.size = Coord(*img.size)

    def __str__(self) -> str:
        return '{} \'{}\' {}'.format(self.pic, self.name, self.size)

class Parser:
    def __init__(self, dirname):
        d = Path(dirname) / 'DWIN_SET'
        self.files = d.glob('???_*.bmp')

    def __iter__(self) -> Page:
        for filename in self.files:
            yield Page(filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('basedir', nargs='?', type=Path, default='../dgusm')
    args = parser.parse_args()
    for page in Parser(args.basedir):
        print(page)
