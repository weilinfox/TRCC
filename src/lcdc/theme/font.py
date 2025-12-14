
import ctypes
import ctypes.util
import dataclasses
import logging
import pathlib

from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class _FontRaw:
    namelang: List[str]
    family: List[str]
    familylang: List[str]
    style: List[str]
    stylelang: List[str]
    fullname: List[str]
    fullnamelang: List[str]
    file: List[str]
    index: List[int]


@dataclasses.dataclass
class FontInfo:
    family: str
    familylang: str
    style: str
    stylelang: str
    fullname: str
    file: str


class FontManager:
    def __init__(self):
        self.fontconfig = ctypes.util.find_library("fontconfig")
        self.font_raw: List[_FontRaw] = []
        # { family: { style: List[FontInfo] } }
        self.fonts: Dict[str, Dict[str, List[FontInfo]]] = {}
        self.families: List[str] = []
        self.styles: Dict[str, List[str]] = {}

    def init(self):
        if self.fontconfig is None:
            raise AssertionError("Font subsystem not init for fontconfig.so not found")

        fc = ctypes.CDLL(self.fontconfig)

        # types
        _FcBool = ctypes.c_int
        _FcFalse: int = 0
        _FcTrue: int = 1

        _FcChar32 = ctypes.c_uint
        _FcChar16 = ctypes.c_ushort
        _FcChar8 = ctypes.c_ubyte

        _FcPatternP = ctypes.c_void_p
        _FcObjectSetP = ctypes.c_void_p
        _FcFontSetP = ctypes.c_void_p

        _FcResult = ctypes.c_int
        _FcResultMatch = 0
        _FcResultNoMatch = 1
        _FcResultTypeMismatch = 2
        _FcResultNoId = 3
        _FcResultOutOfMemory = 4

        class _FcFontSet(ctypes.Structure):
            """
            a list of FcPatterns
            """
            _fields_ = [
                ("nfont", ctypes.c_int),  # 'nfont' holds the number of patterns in the 'fonts' array
                ("sfont", ctypes.c_int),  # 'sfont' is used to indicate the size of that array
                ("fonts", ctypes.POINTER(_FcPatternP)),  # FcPattern **fonts
            ]

        # font properties
        _FcNamelang = b"namelang"  # String  Language name to be used for the default value of familylang, stylelang and fullnamelang
        _FcFamily = b"family"  # String  Font family names
        _FcFamilyLang = b"familylang"  # String  Language corresponding to each family name
        _FcStyle = b"style"  # String  Font style. Overrides weight and slant
        _FcStyleLang = b"stylelang"  # String  Language corresponding to each style name
        _FcFullname = b"fullname"  # String  Font face full name where different from family and family + style
        _FcFullnameLang = b"fullnamelang"  # String  Language corresponding to each fullname
        _FcFile = b"file"  # String  The filename holding the font relative to the config's sysroot
        _FcIndex = b"index"  # Int     The index of the font within the file

        # functions
        fc.FcInit.restype = _FcBool
        fc.FcFontList.restype = _FcFontSetP
        fc.FcFontList.argtypes = [ctypes.c_void_p, _FcPatternP, _FcObjectSetP]
        fc.FcFontSetDestroy.argtypes = [_FcFontSetP]
        fc.FcPatternCreate.restype = _FcPatternP
        fc.FcPatternGetString.restype = _FcResult
        fc.FcPatternGetString.argtypes = [_FcPatternP, ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
        fc.FcObjectSetBuild.restype = _FcObjectSetP

        if fc.FcInit() != _FcTrue:
            raise RuntimeError(f"Font subsystem not init for {self.fontconfig} FcInit failed")

        # build an object set from a null-terminated list of property names
        objset = fc.FcObjectSetBuild(_FcNamelang, _FcFamily, _FcFamilyLang, _FcStyle, _FcStyleLang,
                                     _FcFullname, _FcFullnameLang, _FcFile, _FcIndex, None)
        # build patterns with no properties
        pat = fc.FcPatternCreate()
        # list fonts
        cfontsets = fc.FcFontList(None, pat, objset)
        if not cfontsets:
            raise RuntimeError(f"Font subsystem not init for FcFontList return NULL pointer")

        # list of FcPattern
        fontsets = ctypes.cast(cfontsets, ctypes.POINTER(_FcFontSet)).contents

        def _fc_pattern_list_strings(_pattern: _FcPatternP, _property: bytes) -> List[str]:
            out_list: List[str] = []
            idx: int = 0

            while True:
                _s = ctypes.c_char_p()
                _result = fc.FcPatternGetString(p, _property, idx, ctypes.byref(_s))
                if _result != _FcResultMatch:
                    break
                out_list.append(_s.value.decode("utf-8", errors="replace"))
                idx += 1

            return out_list

        def _fc_pattern_get_int(_pattern: _FcPatternP, _property: bytes) -> List[int]:
            out_list: List[int] = []
            idx: int = 0

            while True:
                _i = ctypes.c_char_p()
                _result = fc.FcPatternGetString(p, _property, idx, ctypes.byref(_i))
                if _result != _FcResultMatch:
                    break
                out_list.append(_i.value)
                idx += 1

            return out_list

        self.font_raw: List[_FontRaw] = []
        for i in range(fontsets.nfont):
            p = fontsets.fonts[i]
            self.font_raw.append(_FontRaw(
                namelang=_fc_pattern_list_strings(p, _FcNamelang),
                family=_fc_pattern_list_strings(p, _FcFamily),
                familylang=_fc_pattern_list_strings(p, _FcFamilyLang),
                style=_fc_pattern_list_strings(p, _FcStyle),
                stylelang=_fc_pattern_list_strings(p, _FcStyleLang),
                fullname=_fc_pattern_list_strings(p, _FcFullname),
                fullnamelang=_fc_pattern_list_strings(p, _FcFullnameLang),
                file=_fc_pattern_list_strings(p, _FcFile),
                index=_fc_pattern_get_int(p, _FcIndex),
            ))

        # destroy a font set
        fc.FcFontSetDestroy(cfontsets)
        # finalize fontconfig library
        fc.FcFini()

        # parse font raw to font dict
        for fr in self.font_raw:
            print(fr)
            for i in range(len(fr.style)):
                fm = fr.family[i]
                fs = fr.style[i]
                if fm not in self.fonts.keys():
                    self.fonts[fm] = {}
                    self.styles[fm] = []
                    self.families.append(fm)
                if fs not in self.fonts[fm].keys():
                    self.fonts[fm][fs] = []
                self.styles[fm].append(fs)
                self.fonts[fm][fs].append(FontInfo(
                    family=fm,
                    style=fs,
                    familylang=fr.familylang[i],
                    stylelang=fr.stylelang[i],
                    fullname=fr.fullname[0],
                    file=fr.file[0],
                ))

        self.families.sort()

if __name__ == "__main__":
    font = FontManager()
    font.init()

    for f in font.families:
        print(f)

    print(font.styles["Noto Sans Arabic"])
    print(font.fonts["Noto Sans Arabic"]["Regular"])
