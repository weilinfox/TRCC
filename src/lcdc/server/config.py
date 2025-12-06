import pathlib

from typing import List, Tuple

from .canvas import Canvas
from ..display.usb_display import Display
from ..theme.theme import Theme


class Config:
    def __init__(self, __config_dir: pathlib.Path, __data_dir: pathlib.Path):
        self._config_dir = __config_dir
        self._data_dir = __data_dir

        if not __config_dir.exists():
            __config_dir.mkdir(parents=True)
        if not __data_dir.exists():
            __data_dir.mkdir(parents=True)

        self.canvas: List[Tuple[Display, Canvas]] = []

    def setup_canvas(self, __displays: List[Display]) -> List[Canvas]:
        ret = []
        for d in __displays:
            v, p = d.device()
            cd = self._config_dir / f"{v:04x}:{p:04x}"

            if not cd.exists():
                cd.mkdir()

            c = Canvas(d, Theme(cd))
            ret.append(c)

            self.canvas.append((d, c))

        return ret
