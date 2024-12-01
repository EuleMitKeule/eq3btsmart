from datetime import datetime

from construct_typed import Adapter, Context

from eq3btsmart.exceptions import Eq3InvalidDataException


class Eq3Time(Adapter[bytes, bytes, datetime, datetime]):
    """Adapter to encode and decode time data."""

    def _encode(self, obj: datetime, ctx: Context, path: str) -> bytes:
        return self.encode(obj)

    def _decode(self, obj: bytes, ctx: Context, path: str) -> datetime:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: datetime) -> bytes:
        return bytes(
            [
                value.year % 100,
                value.month,
                value.day,
                value.hour,
                value.minute,
                value.second,
            ]
        )

    @classmethod
    def decode(cls, value: bytes) -> datetime:
        try:
            (year, month, day, hour, minute, second) = value
        except ValueError:
            raise Eq3InvalidDataException("Invalid time data")

        year += 2000

        return datetime(
            year=year, month=month, day=day, hour=hour, minute=minute, second=second
        )
