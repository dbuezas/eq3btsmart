from eq3btsmart.adapter.base_adapter import BaseAdapter


class Eq3Serial(BaseAdapter[str, bytes]):
    """Adapter to encode and decode serial id."""

    @classmethod
    def _encode(cls, value: str) -> bytes:
        return bytes(char + 0x30 for char in value.encode())

    @classmethod
    def _decode(cls, value: bytes) -> str:
        return bytes(char - 0x30 for char in value).decode()
