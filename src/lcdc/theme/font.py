
import ctypes
import ctypes.util
import dataclasses
import logging
import pathlib

from typing import List, Union

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Font:
    family: str
    style: str
    file: str


fontconfig: Union[str, None] = None
fonts: Union[List[Font], None] = None


def fc_init() -> None:
    global fontconfig
    global fonts

    fontconfig = ctypes.util.find_library("fontconfig")
    if fontconfig is None:
        logger.warning("Font subsystem not init for fontconfig.so not found")
        return

    fc = ctypes.CDLL(fontconfig)

    # types
    fc_patten_t = ctypes.c_void_p
    fc_object_set_t = ctypes.c_void_p
    fc_font_set_t = ctypes.c_void_p
    fc_result_t = ctypes.c_int

    class StructFcFontSet(ctypes.Structure):
        _fields_ = [
            ("nfont", ctypes.c_int),
            ("sfont", ctypes.c_int),
            ("fonts", ctypes.POINTER(fc_patten_t)),
        ]

    # constants
    fc_family = b"family"
    fc_style = b"style"
    fc_fullname = b"fullname"
    fc_file = b"file"
    fc_weight = b"weight"
    fc_slant = b"slant"
    fc_width = b"width"
    fc_index = b"index"

    # functions
    fc.FcInit.restype = ctypes.c_int
    fc.FcFontList.restype = fc_font_set_t
    fc.FcFontList.argtypes = [ctypes.c_void_p, fc_patten_t, fc_object_set_t]
    fc.FcFontSetDestroy.argtypes = [fc_font_set_t]
    fc.FcPatternCreate.restype = fc_patten_t
    fc.FcPatternGetString.restype = fc_result_t
    fc.FcPatternGetString.argtypes = [fc_patten_t, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
    fc.FcObjectSetBuild.restype = fc_object_set_t

    if not fc.FcInit():
        logger.error(f"Font subsystem not init for {fontconfig} FcInit failed")
        return

    pat = fc.FcPatternCreate()
    objset = fc.FcObjectSetBuild(fc_family, fc_style, fc_fullname, fc_file,
                                 fc_weight, fc_slant, fc_width, fc_index, None)

    font_set_p = fc.FcFontList(None, pat, objset)
    if not font_set_p:
        logger.warning(f"Font subsystem not init for FcFontList return NULL pointer")
        return

    fontset = ctypes.cast(font_set_p, ctypes.POINTER(StructFcFontSet)).contents

    def _list_str(p: fc_patten_t, key: bytes) -> List[str]:
        out_list: List[str] = []
        idx: int = 0

        while True:
            op = ctypes.c_char_p()
            r = fc.FcPatternGetString(p, key, idx, ctypes.byref(op))
            if r != 0 or not op.value:
                break
            out_list.append(op.value.decode("utf-8", errors="replace"))
            idx += 1

        return out_list

    font_list: List[Font] = []
    for i in range(fontset.nfont):
        _f = fontset.fonts[i]
        families = _list_str(_f, fc_family)
        styles = _list_str(_f, fc_style)
        files = _list_str(_f, fc_file)
        file = files[0] if files else ""

        if not file:
            continue
        if not families or not styles:
            logger.debug(f"Font dropped family{families} style{styles} path {file}")
            continue

        for family in families:
            for style in styles:
                font_list.append(Font(family=family, style=style, file=file))

    fc.FcFontSetDestroy(font_set_p)

    # uniq
    uniq = {}
    for _f in font_list:
        # one font, multiple styles
        k = (_f.file, _f.family, _f.style)
        uniq[k] = _f

    # sort
    fonts = list(uniq.values())

if __name__ == "__main__":
    fc_init()

    for f in fonts:
        print(f"{f.family}, {f.style}, {f.file}")
