from eq3btsmart.const import OperationMode, StatusFlags
from eq3btsmart.models import Status
from eq3btsmart.structures import StatusStruct


def test_status_from_device() -> None:
    mock_struct = StatusStruct(
        valve=50,
        target_temp=21,
        mode=StatusFlags.MANUAL,
    )

    status = Status.from_struct(mock_struct)

    assert status.valve == 50
    assert status.target_temperature == 21


def test_operation_mode_property() -> None:
    status = Status(
        valve=5,
        target_temperature=4.5,
        _operation_mode=OperationMode.ON,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.operation_mode == OperationMode.OFF

    status = Status(
        valve=5,
        target_temperature=24,
        _operation_mode=OperationMode.AUTO,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.operation_mode == OperationMode.AUTO

    status = Status(
        valve=5,
        target_temperature=30,
        _operation_mode=OperationMode.AUTO,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.operation_mode == OperationMode.ON

    status = Status(
        valve=5,
        target_temperature=20,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.operation_mode == OperationMode.MANUAL


def test_status_from_bytes() -> None:
    mock_struct = StatusStruct(
        valve=50,
        target_temp=21,
        mode=StatusFlags.MANUAL,
    )
    mock_bytes = mock_struct.to_bytes()

    status = Status.from_bytes(mock_bytes)

    assert status.valve == 50
    assert status.target_temperature == 21


def test_valve_temperature() -> None:
    status = Status(
        valve=0,
        target_temperature=20,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.valve_temperature == 20

    status = Status(
        valve=50,
        target_temperature=20,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.valve_temperature == 19

    status = Status(
        valve=100,
        target_temperature=20,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=None,
    )
    assert status.valve_temperature == 18
