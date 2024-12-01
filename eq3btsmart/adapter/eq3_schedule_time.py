from datetime import time

from construct_typed import Adapter, Context


class Eq3ScheduleTime(Adapter[int, int, time, time]):
    """Adapter to encode and decode schedule time data."""

    def _encode(self, obj: time, ctx: Context, path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, ctx: Context, path: str) -> time:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: time) -> int:
        return int((value.hour * 60 + value.minute) / 10)

    @classmethod
    def decode(cls, value: int) -> time:
        hour, minute = divmod(value * 10, 60)
        return time(hour=hour, minute=minute)
