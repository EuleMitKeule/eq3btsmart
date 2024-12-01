import asyncio
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from construct_typed import DataclassStruct

from eq3btsmart.const import (
    EQ3BT_ON_TEMP,
    Command,
    Eq3Characteristic,
    Eq3Event,
    Eq3Preset,
    OperationMode,
    WeekDay,
)
from eq3btsmart.exceptions import (
    Eq3AlreadyAwaitingResponseException,
    Eq3CommandException,
    Eq3ConnectionException,
    Eq3InternalException,
    Eq3StateException,
    Eq3TimeoutException,
)
from eq3btsmart.models.device_data import DeviceData
from eq3btsmart.models.presets import Presets
from eq3btsmart.models.schedule import Schedule
from eq3btsmart.models.schedule_day import ScheduleDay
from eq3btsmart.models.schedule_hour import ScheduleHour
from eq3btsmart.models.status import Status
from eq3btsmart.structures import Eq3Message, Eq3Struct, IdGetCommand
from eq3btsmart.thermostat import Thermostat
from tests.mock_client import MockClient, mock_id, mock_status


@pytest.mark.asyncio
async def test_connect_disconnect(mock_thermostat: Thermostat) -> None:
    assert isinstance(mock_thermostat._conn, MockClient)
    assert not mock_thermostat._conn.is_connected

    await mock_thermostat.async_connect()

    assert mock_thermostat._conn.is_connected

    await mock_thermostat.async_disconnect()

    assert not mock_thermostat._conn.is_connected


@pytest.mark.asyncio
async def test_get_id(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    initial_device_data = mock_thermostat._last_device_data

    mock_id.version = 100

    await mock_thermostat.async_get_device_data()

    assert mock_thermostat._last_device_data is not None
    assert isinstance(mock_thermostat._last_device_data.device_serial, str)
    assert mock_thermostat._last_device_data.device_serial == mock_id.serial
    assert initial_device_data != mock_thermostat._last_device_data


@pytest.mark.asyncio
async def test_get_status(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    initial_status = mock_thermostat._last_status

    mock_status.valve = 0x0F

    status = await mock_thermostat.async_get_status()

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.valve == 0x0F
    assert initial_status != mock_thermostat._last_status
    assert status is not None
    assert status.valve == 0x0F
    assert initial_status != status


@pytest.mark.asyncio
async def test_get_schedule(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    assert mock_thermostat._last_schedule is not None
    assert len(mock_thermostat._last_schedule.schedule_days) == 7

    schedule = await mock_thermostat.async_get_schedule()

    assert mock_thermostat._last_schedule is not None
    assert len(mock_thermostat._last_schedule.schedule_days) == 7
    assert schedule is not None
    assert len(schedule.schedule_days) == 7


@pytest.mark.asyncio
async def test_configure_window_open(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_configure_window_open(6.5, timedelta(minutes=25))

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.presets is not None
    assert mock_thermostat._last_status.presets.window_open_temperature == 6.5
    assert mock_thermostat._last_status.presets.window_open_time == timedelta(
        minutes=25
    )


@pytest.mark.asyncio
async def test_configure_presets(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    await mock_thermostat.async_configure_presets(
        26.5,
        16,
    )

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.presets is not None
    assert mock_thermostat._last_status.presets.comfort_temperature == 26.5

    assert mock_thermostat._last_status.presets.eco_temperature == 16.0


@pytest.mark.asyncio
async def test_configure_comfort_without_status(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = None

    with pytest.raises(Exception):
        await mock_thermostat.async_configure_comfort_temperature(26.5)


@pytest.mark.asyncio
async def test_configure_eco_without_status(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = None

    with pytest.raises(Exception):
        await mock_thermostat.async_configure_eco_temperature(16)


@pytest.mark.asyncio
async def test_configure_temperature_offset(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_configure_temperature_offset(2.5)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.presets is not None
    assert mock_thermostat._last_status.presets.offset_temperature == 2.5


@pytest.mark.asyncio
async def test_set_mode(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    await mock_thermostat.async_set_mode(OperationMode.AUTO)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.operation_mode == OperationMode.AUTO


@pytest.mark.asyncio
async def test_set_mode_without_status(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = None

    with pytest.raises(Eq3StateException):
        await mock_thermostat.async_set_mode(OperationMode.MANUAL)


@pytest.mark.asyncio
async def test_set_mode_manual(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    await mock_thermostat.async_set_mode(OperationMode.MANUAL)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.operation_mode == OperationMode.MANUAL
    assert mock_thermostat._last_status.target_temperature == 21.0


@pytest.mark.asyncio
async def test_set_mode_off(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    await mock_thermostat.async_set_mode(OperationMode.OFF)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.operation_mode == OperationMode.OFF
    assert mock_thermostat._last_status.target_temperature == 4.5


@pytest.mark.asyncio
async def test_set_mode_on(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    await mock_thermostat.async_set_mode(OperationMode.ON)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.operation_mode == OperationMode.ON
    assert mock_thermostat._last_status.target_temperature == 30


@pytest.mark.asyncio
async def test_set_away(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    datetime_now = datetime.now()
    await mock_thermostat.async_set_away(datetime_now + timedelta(days=30), 21.5)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.is_away
    assert mock_thermostat._last_status.away_until is not None

    minute_difference = (
        mock_thermostat._last_status.away_until - (datetime_now + timedelta(days=30))
    ).total_seconds() / 60

    assert minute_difference <= 30


@pytest.mark.asyncio
async def test_set_away_not_disabled(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    await mock_thermostat.async_set_mode(OperationMode.MANUAL)
    await mock_thermostat.async_set_away(datetime.now() + timedelta(days=30), 21.5)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.is_away
    assert mock_thermostat._last_status.operation_mode == OperationMode.AUTO


@pytest.mark.asyncio
async def test_set_temperature(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature != 23.5

    await mock_thermostat.async_set_temperature(23.5)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 23.5


@pytest.mark.asyncio
async def test_set_temperature_off(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature != 4.5
    assert mock_thermostat._last_status.operation_mode != OperationMode.OFF

    await mock_thermostat.async_set_temperature(4.5)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 4.5
    assert mock_thermostat._last_status.operation_mode.value == OperationMode.OFF.value


@pytest.mark.asyncio
async def test_set_temperature_on(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature != 30
    assert mock_thermostat._last_status.operation_mode != OperationMode.ON

    await mock_thermostat.async_set_temperature(EQ3BT_ON_TEMP)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 30
    assert mock_thermostat._last_status.operation_mode.value == OperationMode.ON.value


@pytest.mark.asyncio
async def test_set_preset_comfort(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()
    await mock_thermostat.async_set_temperature(26)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 26.0

    await mock_thermostat.async_configure_presets(
        comfort_temperature=21, eco_temperature=17
    )
    await mock_thermostat.async_set_preset(Eq3Preset.COMFORT)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 21.0


@pytest.mark.asyncio
async def test_set_preset_eco(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()
    await mock_thermostat.async_set_temperature(26)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 26.0

    await mock_thermostat.async_configure_presets(
        comfort_temperature=21, eco_temperature=17
    )
    await mock_thermostat.async_set_preset(Eq3Preset.ECO)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.target_temperature == 17.0


@pytest.mark.asyncio
async def test_set_boost(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_status is not None
    assert not mock_thermostat._last_status.is_boost
    assert mock_thermostat._last_status.operation_mode == OperationMode.MANUAL

    await mock_thermostat.async_set_boost(True)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.is_boost
    assert mock_thermostat._last_status.operation_mode == OperationMode.MANUAL

    await mock_thermostat.async_set_boost(False)

    assert mock_thermostat._last_status is not None
    assert not mock_thermostat._last_status.is_boost
    assert mock_thermostat._last_status.operation_mode == OperationMode.MANUAL


@pytest.mark.asyncio
async def test_set_locked(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_status is not None
    assert not mock_thermostat._last_status.is_locked

    await mock_thermostat.async_set_locked(True)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.is_locked

    await mock_thermostat.async_set_locked(False)

    assert mock_thermostat._last_status is not None
    assert not mock_thermostat._last_status.is_locked


@pytest.mark.asyncio
async def test_set_schedule(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_schedule is not None

    assert len(mock_thermostat._last_schedule.schedule_days) == 7

    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        21,
                        time(1, 0, 0),
                    )
                ],
            )
        ]
    )

    await mock_thermostat.async_set_schedule(schedule)

    assert mock_thermostat._last_schedule is not None
    assert schedule.schedule_days[0] in mock_thermostat._last_schedule.schedule_days


@pytest.mark.asyncio
async def test_delete_schedule(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    await mock_thermostat.async_get_status()

    assert mock_thermostat._last_schedule is not None
    assert len(mock_thermostat._last_schedule.schedule_days) == 7
    assert len(mock_thermostat._last_schedule.schedule_days[0].schedule_hours) == 1

    await mock_thermostat.async_delete_schedule(WeekDay.MONDAY)

    assert len(mock_thermostat._last_schedule.schedule_days) == 7
    assert len(mock_thermostat._last_schedule.schedule_days[2].schedule_hours) == 0

    await mock_thermostat.async_delete_schedule()

    assert len(mock_thermostat._last_schedule.schedule_days) == 7
    for schedule_day in mock_thermostat._last_schedule.schedule_days:
        assert len(schedule_day.schedule_hours) == 0


@pytest.mark.asyncio
async def test_write_not_connected(mock_thermostat: Thermostat) -> None:
    with pytest.raises(Exception):
        await mock_thermostat.async_set_boost(True)


@pytest.mark.asyncio
async def test_fail_on_invalid_notification(mock_thermostat: Thermostat) -> None:
    mock_characteristic = MagicMock(spec=BleakGATTCharacteristic)

    with pytest.raises(Exception):
        await mock_thermostat._on_message_received(
            mock_characteristic,
            bytearray(Eq3Message(cmd=Command.ID_RETURN, data=b"\x01").to_bytes()),
        )


@pytest.mark.asyncio
async def test_device_data(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    # Test when device data is set

    mock_id.version = 100
    await mock_thermostat.async_get_device_data()

    assert mock_thermostat.device_data is not None
    assert isinstance(mock_thermostat.device_data.device_serial, str)
    assert mock_thermostat.device_data.device_serial == mock_id.serial

    # Test when device data is not set
    mock_thermostat._last_device_data = None

    with pytest.raises(Eq3StateException, match="Device data not set"):
        _ = mock_thermostat.device_data


@pytest.mark.asyncio
async def test_presets(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    # Test when presets are set
    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=Presets(
            comfort_temperature=21.0,
            eco_temperature=17.0,
            window_open_temperature=12.0,
            window_open_time=timedelta(minutes=15),
            offset_temperature=0.5,
        ),
    )

    presets = mock_thermostat.presets

    assert presets is not None
    assert presets.comfort_temperature == 21.0
    assert presets.eco_temperature == 17.0
    assert presets.window_open_temperature == 12.0
    assert presets.window_open_time == timedelta(minutes=15)
    assert presets.offset_temperature == 0.5

    # Test when presets are not set
    mock_thermostat._last_status.presets = None

    with pytest.raises(Eq3StateException, match="Presets not set"):
        _ = mock_thermostat.presets


@pytest.mark.asyncio
async def test_schedule(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    # Test when schedule is set
    mock_thermostat._last_schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        target_temperature=21.0,
                        next_change_at=time(6, 0, 0),
                    )
                ],
            )
        ]
    )

    schedule = mock_thermostat.schedule

    assert schedule is not None
    assert len(schedule.schedule_days) == 1
    assert schedule.schedule_days[0].week_day == WeekDay.MONDAY
    assert len(schedule.schedule_days[0].schedule_hours) == 1
    assert schedule.schedule_days[0].schedule_hours[0].target_temperature == 21.0
    assert schedule.schedule_days[0].schedule_hours[0].next_change_at == time(6, 0, 0)

    # Test when schedule is not set
    mock_thermostat._last_schedule = None

    with pytest.raises(Eq3StateException, match="Schedule not set"):
        _ = mock_thermostat.schedule


@pytest.mark.asyncio
async def test_async_connect_success(mock_thermostat: Thermostat) -> None:
    with (
        patch.object(
            mock_thermostat._conn, "connect", return_value=None
        ) as mock_connect,
        patch.object(
            mock_thermostat._conn, "start_notify", return_value=None
        ) as mock_start_notify,
        patch.object(
            mock_thermostat, "async_get_device_data", return_value=MagicMock()
        ) as mock_get_device_data,
        patch.object(
            mock_thermostat, "async_get_status", return_value=MagicMock()
        ) as mock_get_status,
        patch.object(
            mock_thermostat, "async_get_schedule", return_value=MagicMock()
        ) as mock_get_schedule,
        patch.object(
            mock_thermostat, "trigger_event", return_value=None
        ) as mock_trigger_event,
    ):
        await mock_thermostat.async_connect()

        mock_connect.assert_called_once()
        mock_start_notify.assert_called_once_with(
            Eq3Characteristic.NOTIFY, mock_thermostat._on_message_received
        )
        mock_get_device_data.assert_called_once()
        mock_get_status.assert_called_once()
        mock_get_schedule.assert_called_once()
        mock_trigger_event.assert_called_once_with(
            Eq3Event.CONNECTED,
            device_data=mock_thermostat.device_data,
            status=mock_thermostat.status,
            schedule=mock_thermostat.schedule,
        )


@pytest.mark.asyncio
async def test_async_connect_bleak_error(mock_thermostat: Thermostat) -> None:
    with (
        patch.object(mock_thermostat._conn, "connect", side_effect=BleakError),
        patch.object(mock_thermostat._conn, "start_notify", return_value=None),
        patch.object(
            mock_thermostat, "async_get_device_data", return_value=MagicMock()
        ),
        patch.object(mock_thermostat, "async_get_status", return_value=MagicMock()),
        patch.object(mock_thermostat, "async_get_schedule", return_value=MagicMock()),
        patch.object(mock_thermostat, "trigger_event", return_value=None),
    ):
        with pytest.raises(
            Eq3ConnectionException, match="Could not connect to the device"
        ):
            await mock_thermostat.async_connect()


@pytest.mark.asyncio
async def test_async_connect_timeout_error(mock_thermostat: Thermostat) -> None:
    with (
        patch.object(mock_thermostat._conn, "connect", side_effect=TimeoutError),
        patch.object(mock_thermostat._conn, "start_notify", return_value=None),
        patch.object(
            mock_thermostat, "async_get_device_data", return_value=MagicMock()
        ),
        patch.object(mock_thermostat, "async_get_status", return_value=MagicMock()),
        patch.object(mock_thermostat, "async_get_schedule", return_value=MagicMock()),
        patch.object(mock_thermostat, "trigger_event", return_value=None),
    ):
        with pytest.raises(Eq3TimeoutException, match="Timeout during connection"):
            await mock_thermostat.async_connect()


@pytest.mark.asyncio
async def test_async_disconnect_success(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    with patch.object(
        mock_thermostat._conn, "disconnect", return_value=None
    ) as mock_disconnect:
        await mock_thermostat.async_disconnect()

        mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_async_disconnect_bleak_error(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    with patch.object(mock_thermostat._conn, "disconnect", side_effect=BleakError):
        with pytest.raises(
            Eq3ConnectionException, match="Could not disconnect from the device"
        ):
            await mock_thermostat.async_disconnect()


@pytest.mark.asyncio
async def test_async_disconnect_timeout_error(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    with patch.object(mock_thermostat._conn, "disconnect", side_effect=TimeoutError):
        with pytest.raises(Eq3TimeoutException, match="Timeout during disconnection"):
            await mock_thermostat.async_disconnect()


@pytest.mark.asyncio
async def test_async_disconnect_with_pending_futures(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._device_data_future = asyncio.Future()
    mock_thermostat._status_future = asyncio.Future()
    mock_thermostat._schedule_future = asyncio.Future()

    with patch.object(mock_thermostat._conn, "disconnect", return_value=None):
        await mock_thermostat.async_disconnect()

        assert mock_thermostat._device_data_future.exception() is not None
        assert isinstance(
            mock_thermostat._device_data_future.exception(), Eq3ConnectionException
        )
        assert mock_thermostat._status_future.exception() is not None
        assert isinstance(
            mock_thermostat._status_future.exception(), Eq3ConnectionException
        )
        assert mock_thermostat._schedule_future.exception() is not None
        assert isinstance(
            mock_thermostat._schedule_future.exception(), Eq3ConnectionException
        )


@pytest.mark.asyncio
async def test_is_connected(mock_thermostat: Thermostat) -> None:
    # Initially, the thermostat should not be connected
    assert not mock_thermostat.is_connected

    # Connect the thermostat
    await mock_thermostat.async_connect()

    # Now, the thermostat should be connected
    assert mock_thermostat.is_connected

    # Disconnect the thermostat
    await mock_thermostat.async_disconnect()

    # Finally, the thermostat should not be connected again
    assert not mock_thermostat.is_connected


@pytest.mark.asyncio
async def test_configure_window_open_temperature(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=Presets(
            comfort_temperature=21.0,
            eco_temperature=17.0,
            window_open_temperature=12.0,
            window_open_time=timedelta(minutes=15),
            offset_temperature=0.5,
        ),
    )

    await mock_thermostat.async_configure_window_open_temperature(6.5)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.presets is not None
    assert mock_thermostat._last_status.presets.window_open_temperature == 6.5
    assert mock_thermostat._last_status.presets.window_open_time == timedelta(
        minutes=15
    )


@pytest.mark.asyncio
async def test_configure_window_open_temperature_without_presets(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    with pytest.raises(Eq3StateException, match="Presets not set"):
        await mock_thermostat.async_configure_window_open_temperature(6.5)


@pytest.mark.asyncio
async def test_configure_window_open_duration(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=Presets(
            comfort_temperature=21.0,
            eco_temperature=17.0,
            window_open_temperature=12.0,
            window_open_time=timedelta(minutes=15),
            offset_temperature=0.5,
        ),
    )

    await mock_thermostat.async_configure_window_open_duration(timedelta(minutes=30))

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.presets is not None
    assert mock_thermostat._last_status.presets.window_open_time == timedelta(
        minutes=30
    )


@pytest.mark.asyncio
async def test_configure_window_open_duration_float(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
        _operation_mode=OperationMode.MANUAL,
        is_away=False,
        is_boost=False,
        is_dst=False,
        is_window_open=False,
        is_locked=False,
        is_low_battery=False,
        away_until=None,
        presets=Presets(
            comfort_temperature=21.0,
            eco_temperature=17.0,
            window_open_temperature=12.0,
            window_open_time=timedelta(minutes=15),
            offset_temperature=0.5,
        ),
    )

    await mock_thermostat.async_configure_window_open_duration(45.0)

    assert mock_thermostat._last_status is not None
    assert mock_thermostat._last_status.presets is not None
    assert mock_thermostat._last_status.presets.window_open_time == timedelta(
        minutes=45
    )


@pytest.mark.asyncio
async def test_configure_window_open_duration_without_presets(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    mock_thermostat._last_status = Status(
        valve=10,
        target_temperature=21.0,
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

    with pytest.raises(Eq3StateException, match="Presets not set"):
        await mock_thermostat.async_configure_window_open_duration(
            timedelta(minutes=30)
        )


@pytest.mark.asyncio
async def test_aenter(mock_thermostat: Thermostat) -> None:
    async with mock_thermostat:
        assert mock_thermostat.is_connected


@pytest.mark.asyncio
async def test_aexit(mock_thermostat: Thermostat) -> None:
    async with mock_thermostat:
        pass
    assert not mock_thermostat.is_connected


@pytest.mark.asyncio
async def test_async_write_command_with_device_data_response_success(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    command = IdGetCommand()

    result = await mock_thermostat._async_write_command_with_device_data_response(
        command
    )
    assert result == DeviceData.from_struct(mock_id)


@pytest.mark.asyncio
async def test_async_write_command_with_device_data_response_already_awaiting(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)
    mock_thermostat._device_data_future = asyncio.Future()

    with pytest.raises(
        Eq3AlreadyAwaitingResponseException,
        match="Already awaiting a device data command response",
    ):
        await mock_thermostat._async_write_command_with_device_data_response(command)


@pytest.mark.asyncio
async def test_async_write_command_with_device_data_response_timeout(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    command = IdGetCommand()

    with (
        patch.object(mock_thermostat, "_async_write_command", return_value=None),
        patch("asyncio.wait_for", side_effect=TimeoutError),
    ):
        with pytest.raises(
            Eq3TimeoutException, match="Timeout during device data command"
        ):
            await mock_thermostat._async_write_command_with_device_data_response(
                command
            )


@pytest.mark.asyncio
async def test_async_write_command_with_status_response_success(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)
    mock_status = MagicMock(spec=Status)

    with (
        patch.object(mock_thermostat, "_async_write_command", return_value=None),
        patch("asyncio.wait_for", return_value=mock_status),
    ):
        result = await mock_thermostat._async_write_command_with_status_response(
            command
        )
        assert result == mock_status


@pytest.mark.asyncio
async def test_async_write_command_with_status_response_already_awaiting(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)
    mock_thermostat._status_future = asyncio.Future()

    with pytest.raises(
        Eq3AlreadyAwaitingResponseException,
        match="Already awaiting a status command response",
    ):
        await mock_thermostat._async_write_command_with_status_response(command)


@pytest.mark.asyncio
async def test_async_write_command_with_status_response_timeout(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)

    with (
        patch.object(mock_thermostat, "_async_write_command", return_value=None),
        patch("asyncio.wait_for", side_effect=TimeoutError),
    ):
        with pytest.raises(Eq3TimeoutException, match="Timeout during status command"):
            await mock_thermostat._async_write_command_with_status_response(command)


@pytest.mark.asyncio
async def test_async_write_commands_with_schedule_response_success(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    commands = [MagicMock(spec=Eq3Struct) for _ in range(3)]
    mock_schedule = MagicMock(spec=Schedule)

    with (
        patch.object(mock_thermostat, "_async_write_command", return_value=None),
        patch("asyncio.wait_for", return_value=mock_schedule),
    ):
        result = await mock_thermostat._async_write_commands_with_schedule_response(
            commands  # type: ignore
        )
        assert result == mock_schedule


@pytest.mark.asyncio
async def test_async_write_commands_with_schedule_response_already_awaiting(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    commands = [MagicMock(spec=Eq3Struct) for _ in range(3)]
    mock_thermostat._schedule_future = asyncio.Future()

    with pytest.raises(
        Eq3AlreadyAwaitingResponseException,
        match="Already awaiting a schedule command response",
    ):
        await mock_thermostat._async_write_commands_with_schedule_response(commands)  # type: ignore


@pytest.mark.asyncio
async def test_async_write_commands_with_schedule_response_timeout(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    commands = [MagicMock(spec=Eq3Struct) for _ in range(3)]

    with (
        patch.object(mock_thermostat, "_async_write_command", return_value=None),
        patch("asyncio.wait_for", side_effect=TimeoutError),
    ):
        with pytest.raises(
            Eq3TimeoutException, match="Timeout during schedule command"
        ):
            await mock_thermostat._async_write_commands_with_schedule_response(commands)  # type: ignore


@pytest.mark.asyncio
async def test_async_write_command_success(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)
    command.to_bytes.return_value = b"\x01\x02\x03"

    with patch.object(
        mock_thermostat._conn, "write_gatt_char", return_value=None
    ) as mock_write_gatt_char:
        await mock_thermostat._async_write_command(command)

        mock_write_gatt_char.assert_called_once_with(
            Eq3Characteristic.WRITE, b"\x01\x02\x03"
        )


@pytest.mark.asyncio
async def test_async_write_command_not_connected(mock_thermostat: Thermostat) -> None:
    command = MagicMock(spec=Eq3Struct)

    with pytest.raises(Eq3ConnectionException, match="Not connected"):
        await mock_thermostat._async_write_command(command)


@pytest.mark.asyncio
async def test_async_write_command_bleak_error(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)
    command.to_bytes.return_value = b"\x01\x02\x03"

    with patch.object(mock_thermostat._conn, "write_gatt_char", side_effect=BleakError):
        with pytest.raises(Eq3CommandException, match="Error during write"):
            await mock_thermostat._async_write_command(command)


@pytest.mark.asyncio
async def test_async_write_command_timeout_error(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    command = MagicMock(spec=Eq3Struct)
    command.to_bytes.return_value = b"\x01\x02\x03"

    with patch.object(
        mock_thermostat._conn, "write_gatt_char", side_effect=TimeoutError
    ):
        with pytest.raises(Eq3TimeoutException, match="Timeout during write"):
            await mock_thermostat._async_write_command(command)


@pytest.mark.asyncio
async def test_on_message_received_id_return(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_characteristic = MagicMock(spec=BleakGATTCharacteristic)
    data = Eq3Message(
        cmd=Command.ID_RETURN, is_status_command=True, data=b"\x02\x03"
    ).to_bytes()

    with (
        patch.object(
            mock_thermostat, "_on_device_data_received", return_value=None
        ) as mock_on_device_data_received,
        patch.object(
            DeviceData, "from_bytes", return_value=DeviceData.from_struct(mock_id)
        ),
        patch.object(
            DeviceData, "from_struct", return_value=DeviceData.from_struct(mock_id)
        ),
    ):
        await mock_thermostat._on_message_received(mock_characteristic, bytearray(data))

        mock_on_device_data_received.assert_called_once()
        assert isinstance(mock_on_device_data_received.call_args[0][0], DeviceData)


@pytest.mark.asyncio
async def test_on_message_received_info_return(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_characteristic = MagicMock(spec=BleakGATTCharacteristic)
    data = Eq3Message(
        cmd=Command.INFO_RETURN, is_status_command=True, data=b"\x02\x03"
    ).to_bytes()

    with (
        patch.object(
            mock_thermostat, "_on_status_received", return_value=None
        ) as mock_on_status_received,
        patch.object(
            Status, "from_bytes", return_value=Status.from_struct(mock_status)
        ),
        patch.object(
            Status, "from_struct", return_value=Status.from_struct(mock_status)
        ),
    ):
        await mock_thermostat._on_message_received(mock_characteristic, bytearray(data))

        mock_on_status_received.assert_called_once()
        assert isinstance(mock_on_status_received.call_args[0][0], Status)


@pytest.mark.asyncio
async def test_on_message_received_schedule_return(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_characteristic = MagicMock(spec=BleakGATTCharacteristic)
    data = Eq3Message(
        cmd=Command.SCHEDULE_RETURN, is_status_command=True, data=b"\x02\x03"
    ).to_bytes()

    with (
        patch.object(
            mock_thermostat, "_on_schedule_received", return_value=None
        ) as mock_on_schedule_received,
        patch.object(
            Schedule,
            "from_bytes",
            return_value=Schedule(),
        ),
    ):
        await mock_thermostat._on_message_received(mock_characteristic, bytearray(data))

        mock_on_schedule_received.assert_called_once()
        assert isinstance(mock_on_schedule_received.call_args[0][0], Schedule)


@pytest.mark.asyncio
async def test_on_message_received_unknown_command(mock_thermostat: Thermostat) -> None:
    await mock_thermostat.async_connect()

    mock_characteristic = MagicMock(spec=BleakGATTCharacteristic)
    data = MagicMock(spec=bytearray)
    command = MagicMock(spec=Eq3Message)
    command.cmd = 0xCC
    command.is_status_command = True
    command.data = data

    with (
        patch.object(DataclassStruct, "parse", return_value=command),
    ):
        with pytest.raises(Eq3InternalException, match="Unknown command"):
            await mock_thermostat._on_message_received(mock_characteristic, data)


@pytest.mark.asyncio
async def test_on_message_received_info_return_not_status_command(
    mock_thermostat: Thermostat,
) -> None:
    await mock_thermostat.async_connect()

    mock_characteristic = MagicMock(spec=BleakGATTCharacteristic)
    data = Eq3Message(
        cmd=Command.INFO_RETURN, is_status_command=False, data=b"\x02\x03"
    ).to_bytes()

    with (
        patch.object(
            mock_thermostat, "_on_status_received", return_value=None
        ) as mock_on_status_received,
        patch.object(
            Status, "from_bytes", return_value=Status.from_struct(mock_status)
        ),
        patch.object(
            Status, "from_struct", return_value=Status.from_struct(mock_status)
        ),
    ):
        await mock_thermostat._on_message_received(mock_characteristic, bytearray(data))

        mock_on_status_received.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_event_disconnected(mock_thermostat: Thermostat) -> None:
    callback = MagicMock()
    mock_thermostat.register_callback(Eq3Event.DISCONNECTED, callback)

    await mock_thermostat.trigger_event(Eq3Event.DISCONNECTED)

    callback.assert_called_once_with()


@pytest.mark.asyncio
async def test_trigger_event_connected(mock_thermostat: Thermostat) -> None:
    callback = MagicMock()
    mock_thermostat.register_callback(Eq3Event.CONNECTED, callback)

    device_data = DeviceData.from_struct(mock_id)
    status = Status(
        valve=10,
        target_temperature=21.0,
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
    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        target_temperature=21.0,
                        next_change_at=time(6, 0, 0),
                    )
                ],
            )
        ]
    )

    await mock_thermostat.trigger_event(
        Eq3Event.CONNECTED, device_data=device_data, status=status, schedule=schedule
    )

    callback.assert_called_once_with(device_data, status, schedule)


@pytest.mark.asyncio
async def test_trigger_event_device_data_received(mock_thermostat: Thermostat) -> None:
    callback = MagicMock()
    mock_thermostat.register_callback(Eq3Event.DEVICE_DATA_RECEIVED, callback)

    device_data = DeviceData.from_struct(mock_id)

    await mock_thermostat.trigger_event(
        Eq3Event.DEVICE_DATA_RECEIVED, device_data=device_data
    )

    callback.assert_called_once_with(device_data)


@pytest.mark.asyncio
async def test_trigger_event_status_received(mock_thermostat: Thermostat) -> None:
    callback = MagicMock()
    mock_thermostat.register_callback(Eq3Event.STATUS_RECEIVED, callback)

    status = Status(
        valve=10,
        target_temperature=21.0,
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

    await mock_thermostat.trigger_event(Eq3Event.STATUS_RECEIVED, status=status)

    callback.assert_called_once_with(status)


@pytest.mark.asyncio
async def test_trigger_event_schedule_received(mock_thermostat: Thermostat) -> None:
    callback = MagicMock()
    mock_thermostat.register_callback(Eq3Event.SCHEDULE_RECEIVED, callback)

    schedule = Schedule(
        schedule_days=[
            ScheduleDay(
                WeekDay.MONDAY,
                schedule_hours=[
                    ScheduleHour(
                        target_temperature=21.0,
                        next_change_at=time(6, 0, 0),
                    )
                ],
            )
        ]
    )

    await mock_thermostat.trigger_event(Eq3Event.SCHEDULE_RECEIVED, schedule=schedule)

    callback.assert_called_once_with(schedule)


@pytest.mark.asyncio
async def test_on_device_data_received_no_future(mock_thermostat: Thermostat) -> None:
    mock_device_data = MagicMock(spec=DeviceData)
    mock_thermostat._device_data_future = None

    with patch.object(
        mock_thermostat, "trigger_event", return_value=None
    ) as mock_trigger_event:
        await mock_thermostat._on_device_data_received(mock_device_data)

        mock_trigger_event.assert_called_once_with(
            Eq3Event.DEVICE_DATA_RECEIVED, device_data=mock_device_data
        )


@pytest.mark.asyncio
async def test_on_status_received_no_future(mock_thermostat: Thermostat) -> None:
    mock_status = MagicMock(spec=Status)
    mock_thermostat._status_future = None

    with patch.object(
        mock_thermostat, "trigger_event", return_value=None
    ) as mock_trigger_event:
        await mock_thermostat._on_status_received(mock_status)

        mock_trigger_event.assert_called_once_with(
            Eq3Event.STATUS_RECEIVED, status=mock_status
        )


@pytest.mark.asyncio
async def test_on_schedule_received_no_future(mock_thermostat: Thermostat) -> None:
    mock_schedule = MagicMock(spec=Schedule)
    mock_thermostat._schedule_future = None
    mock_thermostat._last_schedule = None

    with patch.object(
        mock_thermostat, "trigger_event", return_value=None
    ) as mock_trigger_event:
        await mock_thermostat._on_schedule_received(mock_schedule)

        mock_trigger_event.assert_called_once_with(
            Eq3Event.SCHEDULE_RECEIVED, schedule=mock_schedule
        )


@pytest.mark.asyncio
async def test_register_callback(mock_thermostat: Thermostat) -> None:
    async def async_callback() -> None: ...

    def sync_callback() -> None: ...

    # Register async callback
    mock_thermostat.register_callback(Eq3Event.DISCONNECTED, async_callback)
    assert async_callback in mock_thermostat._callbacks[Eq3Event.DISCONNECTED]

    # Register sync callback
    mock_thermostat.register_callback(Eq3Event.DISCONNECTED, sync_callback)
    assert sync_callback in mock_thermostat._callbacks[Eq3Event.DISCONNECTED]

    # Register the same callback again, should not duplicate
    mock_thermostat.register_callback(Eq3Event.DISCONNECTED, sync_callback)
    assert mock_thermostat._callbacks[Eq3Event.DISCONNECTED].count(sync_callback) == 1


@pytest.mark.asyncio
async def test_unregister_callback(mock_thermostat: Thermostat) -> None:
    async def async_callback() -> None: ...

    def sync_callback() -> None: ...

    # Register callbacks
    mock_thermostat.register_callback(Eq3Event.DISCONNECTED, async_callback)
    mock_thermostat.register_callback(Eq3Event.DISCONNECTED, sync_callback)

    # Unregister async callback
    mock_thermostat.unregister_callback(Eq3Event.DISCONNECTED, async_callback)
    assert async_callback not in mock_thermostat._callbacks[Eq3Event.DISCONNECTED]

    # Unregister sync callback
    mock_thermostat.unregister_callback(Eq3Event.DISCONNECTED, sync_callback)
    assert sync_callback not in mock_thermostat._callbacks[Eq3Event.DISCONNECTED]

    # Unregister a callback that is not registered, should not raise an error
    mock_thermostat.unregister_callback(Eq3Event.DISCONNECTED, sync_callback)


@pytest.mark.asyncio
async def test_trigger_event_connected_invalid_arguments(
    mock_thermostat: Thermostat,
) -> None:
    with pytest.raises(
        Eq3InternalException,
        match="device_data, status, and schedule must not be None for CONNECTED event",
    ):
        await mock_thermostat.trigger_event(Eq3Event.CONNECTED)  # type: ignore


@pytest.mark.asyncio
async def test_trigger_event_device_data_received_invalid_arguments(
    mock_thermostat: Thermostat,
) -> None:
    with pytest.raises(
        Eq3InternalException,
        match="device_data must not be None for DEVICE_DATA_RECEIVED event",
    ):
        await mock_thermostat.trigger_event(Eq3Event.DEVICE_DATA_RECEIVED)  # type: ignore


@pytest.mark.asyncio
async def test_trigger_event_status_received_invalid_arguments(
    mock_thermostat: Thermostat,
) -> None:
    with pytest.raises(
        Eq3InternalException, match="status must not be None for STATUS_RECEIVED event"
    ):
        await mock_thermostat.trigger_event(Eq3Event.STATUS_RECEIVED)  # type: ignore


@pytest.mark.asyncio
async def test_trigger_event_schedule_received_invalid_arguments(
    mock_thermostat: Thermostat,
) -> None:
    with pytest.raises(
        Eq3InternalException,
        match="schedule must not be None for SCHEDULE_RECEIVED event",
    ):
        await mock_thermostat.trigger_event(Eq3Event.SCHEDULE_RECEIVED)  # type: ignore
