
from PIL import Image


class USB:
    def open(self) -> None:
        raise NotImplementedError

    def write(self, _: bytes) -> int:
        raise NotImplementedError

    def read(self) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class Display:
    def ready(self) -> bool:
        """
        False when device init failed, do not do further operations.
        :return:
        """
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    def print(self, _: Image) -> int:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
