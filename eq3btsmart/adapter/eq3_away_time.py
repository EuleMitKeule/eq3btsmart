from datetime import datetime, timedelta

from construct_typed import Adapter, Context

from eq3btsmart.exceptions import Eq3InvalidDataException


class Eq3AwayTime(Adapter[bytes, bytes, datetime, datetime]):
    """Adapter to encode and decode away time data."""

    def _encode(self, obj: datetime, ctx: Context, path: str) -> bytes:
        return self.encode(obj)

    def _decode(self, obj: bytes, ctx: Context, path: str) -> datetime:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: datetime) -> bytes:
        value += timedelta(minutes=15)
        value -= timedelta(minutes=value.minute % 30)

        if value.year < 2000 or value.year > 2099:
            raise Eq3InvalidDataException("Invalid year, possible [2000, 2099]")

        year = value.year - 2000
        hour = value.hour * 2
        if value.minute != 0:
            hour |= 0x01

        return bytes([value.day, year, hour, value.month])

    @classmethod
    def decode(cls, value: bytes) -> datetime:
        if value == bytes([0x00, 0x00, 0x00, 0x00]):
            return datetime(year=2000, month=1, day=1, hour=0, minute=0)

        (day, year, hour_min, month) = value

        year += 2000

        min = 0
        if hour_min & 0x01:
            min = 30
        hour = int(hour_min / 2)

        return datetime(year=year, month=month, day=day, hour=hour, minute=min)
