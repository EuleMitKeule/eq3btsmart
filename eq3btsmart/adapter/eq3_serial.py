from construct_typed import Adapter, Context


class Eq3Serial(Adapter[bytes, bytes, str, str]):
    """Adapter to encode and decode serial id."""

    def _encode(self, obj: str, ctx: Context, path: str) -> bytes:
        return self.encode(obj)

    def _decode(self, obj: bytes, ctx: Context, path: str) -> str:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: str) -> bytes:
        return bytes(char + 0x30 for char in value.encode())

    @classmethod
    def decode(cls, value: bytes) -> str:
        return bytes(char - 0x30 for char in value).decode()
