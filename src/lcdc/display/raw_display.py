
import io
import logging
import usb

from PIL import Image
from typing import List, Tuple

from .display import Display, USB


logger = logging.getLogger(__name__)


class UsbRaw(USB):
    def __init__(self, _vendor: int, _product: int) -> None:
        self._id_vendor = _vendor
        self._id_product = _product

        self._dev = usb.core.find(idVendor=_vendor, idProduct=_product)
        if self._dev is None:
            raise AssertionError(f"USB device {_vendor:04x}:{_product:04x} not found")
        if self._dev.bNumConfigurations == 0:
            raise AssertionError(f"USB device {_vendor:04x}:{_product:04x} has no configurations")
        elif self._dev.bNumConfigurations > 1:
            logger.warning(f"USB device {_vendor:04x}:{_product:04x} has multiple configurations")

        # write(host -> device)
        self._ep_out = None
        # read(device -> host)
        self._ep_in = None

    def open(self) -> None:

        self._dev.set_configuration()

        for ep in self._dev.get_active_configuration()[(0, 0)]:
            if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    self._ep_out = ep
                elif usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    self._ep_in = ep

        if self._ep_out is None or self._ep_in is None:
            raise AssertionError(f"USB device endpoint IN {self._ep_in} OUT {self._ep_out}")

    def write(self, _buf: bytes) -> int:
        return self._ep_out.write(_buf)

    def read(self) -> bytes:
        # length, timeout
        return bytes(self._ep_in.read(512, 10))

    def device(self) -> Tuple[int, int]:
        return self._id_vendor, self._id_product

    def close(self) -> None:
        pass


class RawDisplay(Display):
    def __init__(self, _vendor: int, _product: int) -> None:
        self._ready = True
        try:
            self._device = UsbRaw(_vendor, _product)
            self._device.open()
        except Exception as e:
            logger.error(e)
            logger.error(f"USB device {_vendor:04x}:{_product:04x} failed to open")
            self._ready = False

    def ready(self) -> bool:
        return self._ready

    def close(self) -> None:
        self._device.close()

    def device(self) -> Tuple[int, int]:
        return self._device.device()


class Display87ad70db(RawDisplay):
    def __init__(self) -> None:
        RawDisplay.__init__(self, 0x87ad, 0x70db)
        if self.ready():
            self.clear()
            logger.info(f"USB device 87ad:70db ready")
        else:
            logger.error(f"USB device 87ad:70db not ready")

    def clear(self) -> None:
        # URB_BULK out
        # 12 34 56 78 00 00 00 00 00 00 00 00 00 00 00 00
        # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
        # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
        # 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
        self._device.write(bytes.fromhex("""
        12 34 56 78 00 00 00 00 00 00 00 00 00 00 00 00
        00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
        00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
        00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00"""))

        # URB_BULK in
        # 12 34 56 78 53 53 43 52 4d 2d 56 31 00 00 00 00
        # 00 00 00 00 4c 1f aa 8f 04 00 00 00 2e 00 00 00
        # 01 00 00 00 01 00 00 00 00 00 00 00 01 00 00 00
        # 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
        #                         little int32 type 0x01
        logger.debug("HID device 87ad:70db clear command response")
        resp = self._device.read()
        logger.debug(str(resp.hex(" ")))

    def print(self, _img: Image) -> int:
        # baseline DCT only
        # no optimized Huffman
        _buf = io.BytesIO()
        _img.save(_buf, format="JPEG", progressive=False, optimize=False, )

        # URB_BUIK out
        # 12 34 56 78 02 00 00 00 e0 01 00 00 e0 01 00 00
        # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
        # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
        # 00 00 00 00 00 00 00 00 02 00 00 00 1a ad 01 00
        #                         type 0x02   little int32 length
        # ff d8 ff e0 00 10 4a 46 49 46 00 01 01 01 00 60
        # JPEG
        # 00 60 00 00 ff db 00 43 00 02 01 01 01 01 01 02
        data = (bytes.fromhex("12 34 56 78 02 00 00 00") +
                _img.width.to_bytes(4, byteorder="little") + _img.height.to_bytes(4, byteorder="little") +
                bytes.fromhex("""00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
                00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
                00 00 00 00 00 00 00 00 02 00 00 00""")
                + len(_buf.getvalue()).to_bytes(4, byteorder="little") + _buf.getvalue()
                )

        return self._device.write(data)

    def resolutions(self) -> List[Tuple[int, int]]:
        return [(480, 480), (320, 320)]
