from datetime import timedelta

from eq3btsmart._structures import _PresetsStruct
from eq3btsmart.models import Presets


def test_presets_from_struct() -> None:
    preset_struct = _PresetsStruct(
        window_open_temp=4.5,
        window_open_time=timedelta(seconds=5),
        comfort_temp=24,
        eco_temp=16,
        offset=0,
    )

    presets = Presets._from_struct(preset_struct)

    assert presets.window_open_temperature == 4.5
    assert presets.window_open_time == timedelta(seconds=5)
    assert presets.comfort_temperature == 24
    assert presets.eco_temperature == 16
    assert presets.offset_temperature == 0


def test_presets_struct_type() -> None:
    assert Presets._struct_type() == _PresetsStruct
