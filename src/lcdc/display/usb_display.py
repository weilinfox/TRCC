import usb

from typing import List, Union

from .raw_display import Display87ad70db
from .hid_display import Display04165302

_USB_ID_SUPPORTED = {
    (0x0416, 0x5302): lambda: Display04165302(),
    (0x87ad, 0x70db): lambda: Display87ad70db(),
}

Display = Union[Display87ad70db, Display04165302]


def usb_detect() -> List[Display]:

    dev_list = []
    busses = usb.busses()
    for bus in busses:
        for dev in bus.devices:
            if (dev.idVendor, dev.idProduct) in _USB_ID_SUPPORTED:
                new = _USB_ID_SUPPORTED[(dev.idVendor, dev.idProduct)]()
                if new.ready():
                    dev_list.append(new)

    return dev_list
