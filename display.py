
import logging
import time

import usb.core


logger = logging.getLogger(__name__)

if __name__ == "__main__":
    dev = usb.core.find(idVendor=0x87ad, idProduct=0x70db)
    if dev is None:
        exit(1)
    if dev.bNumConfigurations == 0:
        logger.fatal("No configuration?")
        exit(1)
    elif dev.bNumConfigurations > 1:
        logger.warning("Multiple configurations?")

    logger.warning(str(dev))

    dev.set_configuration()
    cfg = dev.get_active_configuration()[(0, 0)]
    logger.warning("==========")

    ep_out = None  # write（host -> device）
    ep_in = None  # read（device -> host）

    for ep in cfg:
        if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
            if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                ep_out = ep
            elif usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                ep_in = ep

    logger.warning("OUT =" + hex(ep_out.bEndpointAddress) + " IN =" + hex(ep_in.bEndpointAddress))
    if ep_out is None or ep_in is None:
        exit(1)

    # URB_BULK out
    # 12 34 56 78 00 00 00 00 00 00 00 00 00 00 00 00
    # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    # 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
    ep_out.write(bytes.fromhex("""
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
    resp = bytes(ep_in.read(128, 100))
    logger.warning("==========")
    logger.warning("Command response:")
    logger.warning(resp.hex(" "))
    #
    # URB_BUIK out
    # 12 34 56 78 02 00 00 00 e0 01 00 00 e0 01 00 00
    # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    # 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    # 00 00 00 00 00 00 00 00 02 00 00 00 1a ad 01 00
    #                         type 0x02   little int32 length
    # ff d8 ff e0 00 10 4a 46 49 46 00 01 01 01 00 60
    # JPEG
    # 00 60 00 00 ff db 00 43 00 02 01 01 01 01 01 02

    fb = None
    with open("/home/hachi/Documents/Untitled.jpg", "rb") as f:
    #with open("/home/hachi/Desktop/test.jpg", "rb") as f:
        fb = f.read()

    if fb is None:
        exit(1)

    logger.warning(str(len(fb)))
    logger.warning(str(len(fb).to_bytes(4, byteorder="little")))
    logger.warning(str(fb[:64]))

    # baseline DCT only
    # no optimized Huffman
    data = (bytes.fromhex("""
    12 34 56 78 02 00 00 00 e0 01 00 00 e0 01 00 00
    00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    00 00 00 00 00 00 00 00 02 00 00 00""")
            + len(fb).to_bytes(4, byteorder="little") + fb
            )
    logger.warning(str(data[:64].hex(" ")))
    logger.warning(str(data[64:128].hex(" ")))

    for i in range(5000):
        time.sleep(0.01)
        ep_out.write(data)