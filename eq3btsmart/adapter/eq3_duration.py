from datetime import timedelta

from construct_typed import Adapter, Context

from eq3btsmart.exceptions import Eq3InvalidDataException


class Eq3Duration(Adapter[int, int, timedelta, timedelta]):
    """Adapter to encode and decode duration data."""

    def _encode(self, obj: timedelta, ctx: Context, path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, ctx: Context, path: str) -> timedelta:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: timedelta) -> int:
        if value.seconds < 0 or value.seconds > 3600.0:
            raise Eq3InvalidDataException(
                "Window open time must be between 0 and 60 minutes in intervals of 5 minutes."
            )

        return int(value.seconds / 300.0)

    @classmethod
    def decode(cls, value: int) -> timedelta:
        return timedelta(minutes=float(value * 5.0))
