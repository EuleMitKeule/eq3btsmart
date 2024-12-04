from datetime import datetime, time, timedelta

from construct_typed import Adapter, Context

from eq3btsmart.const import (
    EQ3_MAX_OFFSET,
    EQ3_MIN_OFFSET,
    EQ3_OFF_TEMP,
    EQ3_ON_TEMP,
)
from eq3btsmart.exceptions import Eq3InvalidDataException

__all__: list[str] = []


class _Eq3AwayTime(Adapter[bytes, bytes, datetime, datetime]):
    """Adapter to encode and decode away time data."""

    @staticmethod
    def from_datetime(value: datetime) -> bytes:
        value += timedelta(minutes=15)
        value -= timedelta(minutes=value.minute % 30)

        if value.year < 2000 or value.year > 2099:
            raise Eq3InvalidDataException("Invalid year, possible [2000, 2099]")

        year = value.year - 2000
        hour = value.hour * 2
        if value.minute != 0:
            hour |= 0x01

        return bytes([value.day, year, hour, value.month])

    @staticmethod
    def to_datetime(value: bytes) -> datetime:
        if value == bytes([0x00, 0x00, 0x00, 0x00]):
            return datetime(year=2000, month=1, day=1, hour=0, minute=0)

        (day, year, hour_min, month) = value

        year += 2000

        minute = 0
        if hour_min & 0x01:
            minute = 30
        hour = int(hour_min / 2)

        return datetime(year=year, month=month, day=day, hour=hour, minute=minute)

    def _encode(self, obj: datetime, _ctx: Context, _path: str) -> bytes:
        return self.from_datetime(obj)

    def _decode(self, obj: bytes, _ctx: Context, _path: str) -> datetime:
        return self.to_datetime(obj)


class _Eq3Duration(Adapter[int, int, timedelta, timedelta]):
    """Adapter to encode and decode duration data."""

    def _encode(self, obj: timedelta, _ctx: Context, _path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, _ctx: Context, _path: str) -> timedelta:
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


class _Eq3ScheduleTime(Adapter[int, int, time, time]):
    """Adapter to encode and decode schedule time data."""

    def _encode(self, obj: time, _ctx: Context, _path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, _ctx: Context, _path: str) -> time:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: time) -> int:
        return int((value.hour * 60 + value.minute) / 10)

    @classmethod
    def decode(cls, value: int) -> time:
        hour, minute = divmod(value * 10, 60)
        return time(hour=hour, minute=minute)


class _Eq3Serial(Adapter[bytes, bytes, str, str]):
    """Adapter to encode and decode serial id."""

    def _encode(self, obj: str, _ctx: Context, _path: str) -> bytes:
        return self.encode(obj)

    def _decode(self, obj: bytes, _ctx: Context, _path: str) -> str:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: str) -> bytes:
        return bytes(char + 0x30 for char in value.encode())

    @classmethod
    def decode(cls, value: bytes) -> str:
        return bytes(char - 0x30 for char in value).decode()


class _Eq3TemperatureOffset(Adapter[int, int, float, float]):
    """Adapter to encode and decode temperature offset data."""

    def _encode(self, obj: float, _ctx: Context, _path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, _ctx: Context, _path: str) -> float:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: float) -> int:
        if value < EQ3_MIN_OFFSET or value > EQ3_MAX_OFFSET:
            raise Eq3InvalidDataException(
                f"Temperature {value} out of range [{EQ3_MIN_OFFSET}, {EQ3_MAX_OFFSET}]"
            )

        return int((value + 3.5) / 0.5)

    @classmethod
    def decode(cls, value: int) -> float:
        return float(value * 0.5 - 3.5)


class _Eq3Temperature(Adapter[int, int, float, float]):
    """Adapter to encode and decode temperature data."""

    def _encode(self, obj: float, _ctx: Context, _path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, _ctx: Context, _path: str) -> float:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: float) -> int:
        if value < EQ3_OFF_TEMP or value > EQ3_ON_TEMP:
            raise Eq3InvalidDataException(
                f"Temperature {value} out of range [{EQ3_OFF_TEMP}, {EQ3_ON_TEMP}]"
            )

        return int(value * 2)

    @classmethod
    def decode(cls, value: int) -> float:
        return float(value / 2)


class _Eq3Time(Adapter[bytes, bytes, datetime, datetime]):
    """Adapter to encode and decode time data."""

    def _encode(self, obj: datetime, _ctx: Context, _path: str) -> bytes:
        return self.encode(obj)

    def _decode(self, obj: bytes, _ctx: Context, _path: str) -> datetime:
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
