from construct_typed import Adapter, Context

from eq3btsmart.const import EQ3BT_MAX_OFFSET, EQ3BT_MIN_OFFSET
from eq3btsmart.exceptions import Eq3InvalidDataException


class Eq3TemperatureOffset(Adapter[int, int, float, float]):
    """Adapter to encode and decode temperature offset data."""

    def _encode(self, obj: float, ctx: Context, path: str) -> int:
        return self.encode(obj)

    def _decode(self, obj: int, ctx: Context, path: str) -> float:
        return self.decode(obj)

    @classmethod
    def encode(cls, value: float) -> int:
        if value < EQ3BT_MIN_OFFSET or value > EQ3BT_MAX_OFFSET:
            raise Eq3InvalidDataException(
                f"Temperature {value} out of range [{EQ3BT_MIN_OFFSET}, {EQ3BT_MAX_OFFSET}]"
            )

        return int((value + 3.5) / 0.5)

    @classmethod
    def decode(cls, value: int) -> float:
        return float(value * 0.5 - 3.5)
