from typing import List, Tuple

import hid
import io
import logging

from PIL import Image

from .display import Display, USB


logger = logging.getLogger(__name__)


class UsbHid(USB):
    def __init__(self, _vendor: int, _product: int) -> None:
        self._id_vendor = _vendor
        self._id_product = _product

        self._dev = hid.device()

    def open(self) -> None:
        self._dev.open(self._id_vendor, self._id_product)
        self._dev.set_nonblocking(False)

    def _reports_write(self, _buf: bytes) -> int:
        # ReportID
        return self._dev.write(b'\x00' + _buf)

    def _reports_read(self, _timeout: int) -> bytes:
        _r = []
        while True:
            _tt = self._dev.read(512, _timeout)
            if _tt is None or len(_tt) == 0:
                break
            _r.extend(_tt)
        return bytes(_r)

    def write(self, _buf: bytes) -> int:
        _t = 0
        for _c in range(len(_buf) // 512 + 1):
            td = _buf[512 * _c: 512 * _c + 512]
            td = td.ljust(512, b'\x00')
            _tt = self._reports_write(td)
            if _tt == -1:
                break
            _t += _tt

        return _t

    def read(self) -> bytes:
        return self._reports_read(10)

    def close(self) -> None:
        self._dev.close()


class HidDisplay(Display):
    def __init__(self, _vendor: int, _product: int) -> None:
        self._ready = True
        try:
            self._device = UsbHid(_vendor, _product)
            self._device.open()
        except Exception as e:
            logger.error(e)
            logger.error(f"HID device {_vendor:04x}:{_product:04x} failed to open")
            self._ready = False

    def ready(self) -> bool:
        return self._ready

    def close(self) -> None:
        self._device.close()


class Display04165302(HidDisplay):
    def __init__(self) -> None:
        HidDisplay.__init__(self, 0x0416, 0x5302)
        if self.ready():
            self.clear()
            logger.info(f"HID device 0416:5302 ready")
        else:
            logger.error(f"HID device 0416:5302 not ready")

    def clear(self) -> None:
        # URB_INTERRUPT out
        # da db dc dd 00 00 00 00 00 00 00 00 01 00 00 00
        #             ↑ little int32 type 0x00
        self._device.write(bytes.fromhex("da db dc dd 00 00 00 00 00 00 00 00 01 00 00 00"))

        # URB_INTERRUPT in
        # da db dc dd 01 80 00 00 00 00 00 00 01 00 00 00
        #             ↑ little int32 type 0x01
        # 10 00 00 00 42 50 32 31 39 34 30 0d 01 6f 57 42
        # 47 02 20 78
        logger.debug("HID device 0416:5302 clear command response")
        resp = self._device.read()
        logger.debug(str(resp.hex(" ")))

    def print(self, _img: Image) -> int:
        _buf = io.BytesIO()
        _img.save(_buf, format="JPEG", progressive=False, optimize=False, )

        # URB_BUIK out
        # da db dc dd 02 00 00 00 00 05 e0 01 02 00 00 00
        #             ↑ type 0x02    ↑ magic
        # 10 b7 02 00 ff d8 ff e0 00 10 4a 46 49 46 00 01
        # uint32 size JPEG
        data = (bytes.fromhex("da db dc dd 02 00 00 00 00 00 00 00 02 00 00 00")
                + len(_buf.getvalue()).to_bytes(4, byteorder="little") + _buf.getvalue()
                )

        return self._device.write(data)

    def resolutions(self) -> List[Tuple[int, int]]:
        return [(1280, 480), ]
