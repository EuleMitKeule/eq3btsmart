import asyncio
from datetime import datetime, time, timedelta
from unittest.mock import (
    AsyncMock,
    MagicMock,
    PropertyMock,
    create_autospec,
    patch,
)

import pytest
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from eq3btsmart._adapters import _Eq3Temperature
from eq3btsmart._structures import (
    _AwaySetCommand,
    _BoostSetCommand,
    _ComfortEcoConfigureCommand,
    _ComfortSetCommand,
    _DeviceDataStruct,
    _EcoSetCommand,
    _Eq3Message,
    _Eq3Struct,
    _IdGetCommand,
    _InfoGetCommand,
    _LockSetCommand,
    _ModeSetCommand,
    _OffsetConfigureCommand,
    _ScheduleDayStruct,
    _ScheduleHourStruct,
    _ScheduleSetCommand,
    _StatusStruct,
    _TemperatureSetCommand,
    _WindowOpenConfigureCommand,
)
from eq3btsmart.const import (
    EQ3_OFF_TEMP,
    EQ3_ON_TEMP,
    Eq3Event,
    Eq3OperationMode,
    Eq3Preset,
    Eq3WeekDay,
    _Eq3Characteristic,
    _Eq3Command,
    _Eq3StatusFlags,
)
from eq3btsmart.exceptions import (
    Eq3CommandException,
    Eq3ConnectionException,
    Eq3InternalException,
    Eq3InvalidDataException,
    Eq3StateException,
    Eq3TimeoutException,
)
from eq3btsmart.models import DeviceData, Schedule, ScheduleDay, ScheduleHour, Status
from eq3btsmart.thermostat import Thermostat


@pytest.mark.asyncio
async def test_connect(thermostat: Thermostat) -> None:
    with (
        patch(
            "eq3btsmart.thermostat.establish_connection", new_callable=AsyncMock
        ) as mock_establish_connection,
        patch.object(
            thermostat._conn, "start_notify", new_callable=AsyncMock
        ) as mock_start_notify,
        patch.object(
            thermostat, "_async_write_command", new_callable=AsyncMock
        ) as mock_write_command,
        patch.object(
            thermostat, "_trigger_event", new_callable=AsyncMock
        ) as mock_trigger_event,
    ):
        mock_establish_connection.return_value = thermostat._conn
        # Setup mock data that would be returned from successful commands
        thermostat._last_device_data = MagicMock()
        thermostat._last_status = MagicMock()
        thermostat._last_schedule = MagicMock()

        await thermostat.async_connect()

        mock_establish_connection.assert_called_once()
        mock_start_notify.assert_called_once()
        # Should call write command 3 times: ID_GET, INFO_GET, SCHEDULE_GET
        assert mock_write_command.call_count == 9
        mock_trigger_event.assert_called_once_with(
            Eq3Event.CONNECTED,
            device_data=thermostat.device_data,
            status=thermostat.status,
            schedule=thermostat.schedule,
        )


@pytest.mark.asyncio
async def test_connect_already_connected(thermostat: Thermostat) -> None:
    with patch.object(
        Thermostat, "is_connected", new_callable=PropertyMock
    ) as mock_is_connected:
        mock_is_connected.return_value = True

        with pytest.raises(Eq3StateException, match="Already connected"):
            await thermostat.async_connect()


@pytest.mark.asyncio
async def test_connect_bleak_error(thermostat: Thermostat) -> None:
    with patch("eq3btsmart.thermostat.establish_connection", side_effect=BleakError):
        with pytest.raises(
            Eq3ConnectionException, match="Could not connect to the device"
        ):
            await thermostat.async_connect()


@pytest.mark.asyncio
async def test_connect_timeout_error(thermostat: Thermostat) -> None:
    with patch("eq3btsmart.thermostat.establish_connection", side_effect=TimeoutError):
        with pytest.raises(Eq3TimeoutException, match="Timeout during connection"):
            await thermostat.async_connect()


@pytest.mark.asyncio
async def test_disconnect(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat._conn, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        await thermostat.async_disconnect()

        mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_disconnect_not_connected(thermostat: Thermostat) -> None:
    with patch.object(
        Thermostat, "is_connected", new_callable=PropertyMock
    ) as mock_is_connected:
        mock_is_connected.return_value = False

        with pytest.raises(Eq3StateException, match="Not connected"):
            await thermostat.async_disconnect()


@pytest.mark.asyncio
async def test_disconnect_bleak_error(thermostat: Thermostat) -> None:
    with (
        patch.object(thermostat._conn, "disconnect", side_effect=BleakError),
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        with pytest.raises(
            Eq3ConnectionException, match="Could not disconnect from the device"
        ):
            await thermostat.async_disconnect()


@pytest.mark.asyncio
async def test_disconnect_timeout_error(thermostat: Thermostat) -> None:
    with (
        patch.object(thermostat._conn, "disconnect", side_effect=TimeoutError),
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        with pytest.raises(Eq3TimeoutException, match="Timeout during disconnection"):
            await thermostat.async_disconnect()


@pytest.mark.asyncio
async def test_get_device_data(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat,
        "_async_write_command",
        new_callable=AsyncMock,
    ) as mock_write_command:
        await thermostat.async_get_device_data()

        mock_write_command.assert_called_once_with(_IdGetCommand())


@pytest.mark.asyncio
async def test_get_status(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch("eq3btsmart.thermostat.datetime", autospec=True) as mock_datetime,
    ):
        now = datetime.now()
        mock_datetime.now.return_value = now

        await thermostat.async_get_status()

        mock_write_command.assert_called_once_with(_InfoGetCommand(time=now))


@pytest.mark.asyncio
async def test_get_schedule(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat,
        "_async_write_commands",
        new_callable=AsyncMock,
    ) as mock_write_command:
        await thermostat.async_get_schedule()

        assert mock_write_command.called
        assert len(mock_write_command.call_args.args[0]) == 7


@pytest.mark.asyncio
async def test_device_data(thermostat: Thermostat) -> None:
    device_data = MagicMock()
    thermostat._last_device_data = device_data

    assert thermostat.device_data == device_data


@pytest.mark.asyncio
async def test_device_data_not_set(thermostat: Thermostat) -> None:
    thermostat._last_device_data = None

    with pytest.raises(Eq3StateException, match="Device data not set"):
        _ = thermostat.device_data


@pytest.mark.asyncio
async def test_status(thermostat: Thermostat) -> None:
    status = MagicMock()
    thermostat._last_status = status

    assert thermostat.status == status


@pytest.mark.asyncio
async def test_status_not_set(thermostat: Thermostat) -> None:
    thermostat._last_status = None

    with pytest.raises(Eq3StateException, match="Status not set"):
        _ = thermostat.status


@pytest.mark.asyncio
async def test_presets(thermostat: Thermostat) -> None:
    thermostat._last_status = MagicMock()
    presets = MagicMock()
    thermostat._last_status.presets = presets

    assert thermostat.presets == presets


@pytest.mark.asyncio
async def test_presets_not_set(thermostat: Thermostat) -> None:
    thermostat._last_status = MagicMock()
    thermostat._last_status.presets = None

    with pytest.raises(Eq3StateException, match="Presets not set"):
        _ = thermostat.presets


@pytest.mark.asyncio
async def test_schedule(thermostat: Thermostat) -> None:
    schedule = MagicMock()
    thermostat._last_schedule = schedule

    assert thermostat.schedule == schedule


@pytest.mark.asyncio
async def test_schedule_not_set(thermostat: Thermostat) -> None:
    thermostat._last_schedule = None

    with pytest.raises(Eq3StateException, match="Schedule not set"):
        _ = thermostat.schedule


@pytest.mark.asyncio
async def test_set_temperature(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_set_temperature(21.0)

        mock_write_command.assert_called_once_with(
            _TemperatureSetCommand(temperature=21.0)
        )


@pytest.mark.asyncio
async def test_set_temperature_off(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            thermostat, "async_set_mode", new_callable=AsyncMock
        ) as mock_set_mode,
    ):
        await thermostat.async_set_temperature(EQ3_OFF_TEMP)

        mock_write_command.assert_not_called()
        mock_set_mode.assert_called_once_with(Eq3OperationMode.OFF)


@pytest.mark.asyncio
async def test_set_temperature_on(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            thermostat, "async_set_mode", new_callable=AsyncMock
        ) as mock_set_mode,
    ):
        await thermostat.async_set_temperature(EQ3_ON_TEMP)

        mock_write_command.assert_not_called()
        mock_set_mode.assert_called_once_with(Eq3OperationMode.ON)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode, command",
    [
        (
            Eq3OperationMode.MANUAL,
            _ModeSetCommand(mode=Eq3OperationMode.MANUAL | _Eq3Temperature.encode(20)),
        ),
        (
            Eq3OperationMode.AUTO,
            _ModeSetCommand(mode=Eq3OperationMode.AUTO),
        ),
        (
            Eq3OperationMode.ON,
            _ModeSetCommand(
                mode=Eq3OperationMode.MANUAL | _Eq3Temperature.encode(EQ3_ON_TEMP)
            ),
        ),
        (
            Eq3OperationMode.OFF,
            _ModeSetCommand(
                mode=Eq3OperationMode.MANUAL | _Eq3Temperature.encode(EQ3_OFF_TEMP)
            ),
        ),
    ],
)
async def test_set_mode(
    thermostat: Thermostat, mode: Eq3OperationMode, command: _ModeSetCommand
) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            Thermostat, "status", new_callable=PropertyMock
        ) as mock_status_property,
    ):
        mock_status = MagicMock()
        mock_status.target_temperature = 20.0
        # Set initial mode to AUTO so MANUAL mode triggers the workaround
        mock_status.operation_mode = Eq3OperationMode.AUTO
        mock_status_property.return_value = mock_status
        await thermostat.async_set_mode(mode)

        if mode == Eq3OperationMode.MANUAL:
            # MANUAL mode sends a temperature command first as a workaround, then the mode command
            assert mock_write_command.call_count == 2
            mock_write_command.assert_any_call(
                _TemperatureSetCommand(temperature=19.5)
            )  # 20.0 - 0.5
            mock_write_command.assert_any_call(command)
        else:
            mock_write_command.assert_called_once_with(command)


@pytest.mark.asyncio
async def test_set_invalid_mode(thermostat: Thermostat) -> None:
    with patch.object(thermostat, "_async_write_command"):
        with pytest.raises(Eq3InvalidDataException, match="Unsupported operation mode"):
            await thermostat.async_set_mode(Eq3OperationMode.AWAY)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "preset, command",
    [
        (
            Eq3Preset.COMFORT,
            _ComfortSetCommand(),
        ),
        (
            Eq3Preset.ECO,
            _EcoSetCommand(),
        ),
    ],
)
async def test_set_preset(
    thermostat: Thermostat, preset: Eq3Preset, command: _Eq3Command
) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_set_preset(preset)

        mock_write_command.assert_called_once_with(command)


@pytest.mark.asyncio
@pytest.mark.parametrize("enable", [True, False])
async def test_set_boost(thermostat: Thermostat, enable: bool) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_set_boost(enable)

        mock_write_command.assert_called_once_with(_BoostSetCommand(enable=enable))


@pytest.mark.asyncio
@pytest.mark.parametrize("enable", [True, False])
async def test_set_locked(thermostat: Thermostat, enable: bool) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_set_locked(enable)

        mock_write_command.assert_called_once_with(_LockSetCommand(enable=enable))


@pytest.mark.asyncio
async def test_set_away(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        now = datetime.now()
        await thermostat.async_set_away(now, 21.0)

        mock_write_command.assert_called_once_with(
            _AwaySetCommand(
                mode=Eq3OperationMode.AWAY | _Eq3Temperature.encode(21.0),
                away_until=now,
            )
        )


@pytest.mark.asyncio
async def test_set_schedule(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat,
        "_async_write_commands",
        new_callable=AsyncMock,
    ) as mock_write_command:
        schedule = Schedule(
            schedule_days=[
                ScheduleDay(
                    Eq3WeekDay.TUESDAY,
                    schedule_hours=[
                        ScheduleHour(15.5, time(hour=1, minute=0)),
                        ScheduleHour(28.5, time(hour=23, minute=30)),
                    ],
                ),
                ScheduleDay(
                    Eq3WeekDay.WEDNESDAY,
                    schedule_hours=[
                        ScheduleHour(12.5, time(hour=12, minute=30)),
                        ScheduleHour(23.0, time(hour=15, minute=00)),
                    ],
                ),
            ]
        )
        await thermostat.async_set_schedule(schedule)

        mock_write_command.assert_called_once_with(
            [
                _ScheduleSetCommand(
                    day=schedule.schedule_days[0].week_day,
                    hours=[
                        _ScheduleHourStruct(
                            target_temp=schedule.schedule_days[0]
                            .schedule_hours[0]
                            .target_temperature,
                            next_change_at=schedule.schedule_days[0]
                            .schedule_hours[0]
                            .next_change_at,
                        ),
                        _ScheduleHourStruct(
                            target_temp=schedule.schedule_days[0]
                            .schedule_hours[1]
                            .target_temperature,
                            next_change_at=schedule.schedule_days[0]
                            .schedule_hours[1]
                            .next_change_at,
                        ),
                    ],
                ),
                _ScheduleSetCommand(
                    day=schedule.schedule_days[1].week_day,
                    hours=[
                        _ScheduleHourStruct(
                            target_temp=schedule.schedule_days[1]
                            .schedule_hours[0]
                            .target_temperature,
                            next_change_at=schedule.schedule_days[1]
                            .schedule_hours[0]
                            .next_change_at,
                        ),
                        _ScheduleHourStruct(
                            target_temp=schedule.schedule_days[1]
                            .schedule_hours[1]
                            .target_temperature,
                            next_change_at=schedule.schedule_days[1]
                            .schedule_hours[1]
                            .next_change_at,
                        ),
                    ],
                ),
            ]
        )


@pytest.mark.asyncio
async def test_delete_schedule(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat,
        "_async_write_commands",
        new_callable=AsyncMock,
    ) as mock_write_command:
        await thermostat.async_delete_schedule()

        mock_write_command.assert_called_once_with(
            [_ScheduleSetCommand(day=day, hours=[]) for day in Eq3WeekDay]
        )


@pytest.mark.asyncio
async def test_delete_schedule_single_day(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat,
        "_async_write_commands",
        new_callable=AsyncMock,
    ) as mock_write_command:
        await thermostat.async_delete_schedule(Eq3WeekDay.MONDAY)

        mock_write_command.assert_called_once_with(
            [_ScheduleSetCommand(day=Eq3WeekDay.MONDAY, hours=[])]
        )


@pytest.mark.asyncio
async def test_delete_schedule_multiple_days(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat,
        "_async_write_commands",
        new_callable=AsyncMock,
    ) as mock_write_command:
        await thermostat.async_delete_schedule([Eq3WeekDay.MONDAY, Eq3WeekDay.TUESDAY])

        mock_write_command.assert_called_once_with(
            [
                _ScheduleSetCommand(day=Eq3WeekDay.MONDAY, hours=[]),
                _ScheduleSetCommand(day=Eq3WeekDay.TUESDAY, hours=[]),
            ]
        )


@pytest.mark.asyncio
async def test_configure_presets(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_configure_presets(26.5, 16.0)

        mock_write_command.assert_called_once_with(
            _ComfortEcoConfigureCommand(
                comfort_temperature=26.5,
                eco_temperature=16.0,
            )
        )


@pytest.mark.asyncio
async def test_configure_comfort_temperature(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            Thermostat, "presets", new_callable=PropertyMock
        ) as mock_presets_property,
    ):
        mock_presets = MagicMock()
        mock_presets.eco_temperature = 19.5
        mock_presets_property.return_value = mock_presets

        await thermostat.async_configure_comfort_temperature(25.5)

        mock_write_command.assert_called_once_with(
            _ComfortEcoConfigureCommand(comfort_temperature=25.5, eco_temperature=19.5)
        )


@pytest.mark.asyncio
async def test_configure_eco_temperature(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            Thermostat, "presets", new_callable=PropertyMock
        ) as mock_presets_property,
    ):
        mock_presets = MagicMock()
        mock_presets.comfort_temperature = 19.5
        mock_presets_property.return_value = mock_presets

        await thermostat.async_configure_eco_temperature(15.5)

        mock_write_command.assert_called_once_with(
            _ComfortEcoConfigureCommand(comfort_temperature=19.5, eco_temperature=15.5)
        )


@pytest.mark.asyncio
async def test_configure_temperature_offset(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_configure_temperature_offset(2.5)

        mock_write_command.assert_called_once_with(_OffsetConfigureCommand(offset=2.5))


@pytest.mark.asyncio
async def test_configure_window_open(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_configure_window_open(6.5, timedelta(minutes=25))

        mock_write_command.assert_called_once_with(
            _WindowOpenConfigureCommand(
                window_open_temperature=6.5,
                window_open_time=timedelta(minutes=25),
            )
        )


@pytest.mark.asyncio
async def test_configure_window_open_float(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_async_write_command", new_callable=AsyncMock
    ) as mock_write_command:
        await thermostat.async_configure_window_open(6.5, 25)

        mock_write_command.assert_called_once_with(
            _WindowOpenConfigureCommand(
                window_open_temperature=6.5,
                window_open_time=timedelta(minutes=25),
            )
        )


@pytest.mark.asyncio
async def test_configure_window_open_temperature(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            Thermostat, "presets", new_callable=PropertyMock
        ) as mock_presets_property,
    ):
        mock_presets = MagicMock()
        mock_presets.window_open_time = timedelta(minutes=15)
        mock_presets_property.return_value = mock_presets

        await thermostat.async_configure_window_open_temperature(7.5)

        mock_write_command.assert_called_once_with(
            _WindowOpenConfigureCommand(
                window_open_temperature=7.5,
                window_open_time=timedelta(minutes=15),
            )
        )


@pytest.mark.asyncio
async def test_configure_window_open_duration(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            Thermostat, "presets", new_callable=PropertyMock
        ) as mock_presets_property,
    ):
        mock_presets = MagicMock()
        mock_presets.window_open_temperature = 7.5
        mock_presets_property.return_value = mock_presets

        await thermostat.async_configure_window_open_duration(timedelta(minutes=25))

        mock_write_command.assert_called_once_with(
            _WindowOpenConfigureCommand(
                window_open_temperature=7.5,
                window_open_time=timedelta(minutes=25),
            )
        )


@pytest.mark.asyncio
async def test_configure_window_open_duration_float(thermostat: Thermostat) -> None:
    with (
        patch.object(
            thermostat,
            "_async_write_command",
            new_callable=AsyncMock,
        ) as mock_write_command,
        patch.object(
            Thermostat, "presets", new_callable=PropertyMock
        ) as mock_presets_property,
    ):
        mock_presets = MagicMock()
        mock_presets.window_open_temperature = 7.5
        mock_presets_property.return_value = mock_presets

        await thermostat.async_configure_window_open_duration(25.0)

        mock_write_command.assert_called_once_with(
            _WindowOpenConfigureCommand(
                window_open_temperature=7.5,
                window_open_time=timedelta(minutes=25),
            )
        )


@pytest.mark.asyncio
async def test_aenter_aexit() -> None:
    with (
        patch.object(
            Thermostat, "async_connect", new_callable=AsyncMock
        ) as mock_connect,
        patch.object(
            Thermostat, "async_disconnect", new_callable=AsyncMock
        ) as mock_disconnect,
    ):
        async with Thermostat(
            BLEDevice("00:11:22:33:44:55", name="Test Device", details={})
        ):
            mock_connect.assert_called_once()

        mock_disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_write_command_with_device_data_response(thermostat: Thermostat) -> None:
    mock_command = MagicMock()
    mock_device_data = MagicMock()

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        async def simulate_response() -> None:
            await asyncio.sleep(0.01)
            await thermostat._on_device_data_received(mock_device_data)

        asyncio.create_task(simulate_response())

        result = await thermostat._async_write_command(mock_command)

        mock_write_gatt_char.assert_called_once_with(
            _Eq3Characteristic.WRITE, mock_command.to_bytes()
        )
        assert result == mock_device_data


@pytest.mark.asyncio
async def test_write_command_with_device_data_response_timeout(
    thermostat: Thermostat,
) -> None:
    mock_command = MagicMock()

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True
        thermostat._command_timeout = 1

        with pytest.raises(Eq3TimeoutException, match="Timeout during command"):
            await thermostat._async_write_command(mock_command)

        mock_write_gatt_char.assert_called_once_with(
            _Eq3Characteristic.WRITE, mock_command.to_bytes()
        )


@pytest.mark.asyncio
async def test_write_command_with_status_response(thermostat: Thermostat) -> None:
    mock_command = MagicMock()
    mock_status = MagicMock()

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        async def simulate_response() -> None:
            await asyncio.sleep(0.01)
            await thermostat._on_status_received(mock_status)

        asyncio.create_task(simulate_response())

        result = await thermostat._async_write_command(mock_command)

        mock_write_gatt_char.assert_called_once_with(
            _Eq3Characteristic.WRITE, mock_command.to_bytes()
        )
        assert result == mock_status


@pytest.mark.asyncio
async def test_write_command_with_status_response_timeout(
    thermostat: Thermostat,
) -> None:
    mock_command = MagicMock()

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True
        thermostat._command_timeout = 1

        with pytest.raises(Eq3TimeoutException, match="Timeout during command"):
            await thermostat._async_write_command(mock_command)

        mock_write_gatt_char.assert_called_once_with(
            _Eq3Characteristic.WRITE, mock_command.to_bytes()
        )


@pytest.mark.asyncio
async def test_write_commands_with_schedule_response(thermostat: Thermostat) -> None:
    mock_commands = [create_autospec(_Eq3Struct) for _ in range(7)]
    mock_schedule = MagicMock()

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        async def simulate_responses() -> None:
            await asyncio.sleep(0.01)
            for _ in range(7):
                await thermostat._on_schedule_received(mock_schedule)

        # Start the response simulation
        asyncio.create_task(simulate_responses())

        result = await thermostat._async_write_commands(mock_commands)

        assert mock_write_gatt_char.call_count == 7
        assert result == mock_schedule


@pytest.mark.asyncio
async def test_write_commands_with_schedule_response_timeout(
    thermostat: Thermostat,
) -> None:
    mock_commands = [create_autospec(_Eq3Struct) for _ in range(7)]

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True
        thermostat._command_timeout = 0

        with pytest.raises(Eq3TimeoutException, match="Timeout during command"):
            await thermostat._async_write_commands(mock_commands)

        assert mock_write_gatt_char.call_count == 1


@pytest.mark.asyncio
async def test_write_command(thermostat: Thermostat) -> None:
    mock_command = MagicMock()
    mock_device_data = MagicMock()

    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        # Simulate a response after the command is written
        async def simulate_response() -> None:
            # Give the command time to set up the future
            await asyncio.sleep(0.01)
            # Simulate receiving device data response
            await thermostat._on_device_data_received(mock_device_data)

        # Start the response simulation as a background task
        asyncio.create_task(simulate_response())

        result = await thermostat._async_write_command(mock_command)

        mock_write_gatt_char.assert_called_once_with(
            _Eq3Characteristic.WRITE, mock_command.to_bytes()
        )
        assert result == mock_device_data


@pytest.mark.asyncio
async def test_write_command_not_connected(thermostat: Thermostat) -> None:
    mock_command = MagicMock()

    # Mock is_connected to return False and disable connection check to force the error
    with (
        patch.object(
            thermostat._conn, "write_gatt_char", new_callable=AsyncMock
        ) as mock_write_gatt_char,
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = False
        thermostat._conn = None  # Ensure no connection

        with pytest.raises(Eq3StateException, match="Not connected"):
            await thermostat._async_write_command(mock_command, check_connection=False)

        mock_write_gatt_char.assert_not_called()


@pytest.mark.asyncio
async def test_write_command_bleak_error(thermostat: Thermostat) -> None:
    mock_command = MagicMock()

    with (
        patch.object(thermostat._conn, "write_gatt_char", side_effect=BleakError),
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        mock_is_connected.return_value = True

        with pytest.raises(Eq3CommandException, match="Error during command"):
            await thermostat._async_write_command(mock_command)


@pytest.mark.asyncio
async def test_write_command_timeout_error(thermostat: Thermostat) -> None:
    mock_command = MagicMock()

    with (
        patch.object(thermostat._conn, "write_gatt_char", side_effect=TimeoutError),
        patch.object(
            Thermostat, "is_connected", new_callable=PropertyMock
        ) as mock_is_connected,
    ):
        thermostat._command_timeout = 0
        mock_is_connected.return_value = True

        with pytest.raises(Eq3TimeoutException, match="Timeout during command"):
            await thermostat._async_write_command(mock_command)


@pytest.mark.asyncio
async def test_on_disconnected(thermostat: Thermostat) -> None:
    with patch.object(
        thermostat, "_trigger_event", new_callable=AsyncMock
    ) as mock_trigger_event:
        thermostat._on_disconnected(MagicMock())

        mock_trigger_event.assert_called_once_with(Eq3Event.DISCONNECTED)


@pytest.mark.asyncio
async def test_on_message_received_device_data(thermostat: Thermostat) -> None:
    command = _DeviceDataStruct(
        version=0, unknown_1=0, unknown_2=0, serial="0000000000", unknown_3=0
    )
    data = command.to_bytes()
    characteristic = MagicMock()

    with patch.object(
        thermostat, "_on_device_data_received", new_callable=AsyncMock
    ) as mock_on_device_data_received:
        await thermostat._on_message_received(characteristic, bytearray(data))

        mock_on_device_data_received.assert_called_once_with(
            DeviceData._from_bytes(data)
        )


@pytest.mark.asyncio
async def test_on_message_received_status(thermostat: Thermostat) -> None:
    command = _StatusStruct(mode=_Eq3StatusFlags.MANUAL, valve=0, target_temp=4.5)
    data = command.to_bytes()
    characteristic = MagicMock()

    with patch.object(
        thermostat, "_on_status_received", new_callable=AsyncMock
    ) as mock_on_status_received:
        await thermostat._on_message_received(characteristic, bytearray(data))

        mock_on_status_received.assert_called_once_with(Status._from_bytes(data))


@pytest.mark.asyncio
async def test_on_message_received_status_invalid_data(thermostat: Thermostat) -> None:
    command = _StatusStruct(
        mode=_Eq3StatusFlags.MANUAL,
        valve=0,
        target_temp=4.5,
    )
    data = bytearray(command.to_bytes())
    data[1] = 0
    characteristic = MagicMock()

    with patch.object(
        thermostat, "_on_status_received", new_callable=AsyncMock
    ) as mock_on_status_received:
        await thermostat._on_message_received(characteristic, data)

        mock_on_status_received.assert_not_called()


@pytest.mark.asyncio
async def test_on_message_received_schedule(thermostat: Thermostat) -> None:
    command = _ScheduleDayStruct(
        day=Eq3WeekDay.MONDAY,
        hours=[
            _ScheduleHourStruct(
                target_temp=20.5, next_change_at=time(hour=1, minute=0)
            ),
            _ScheduleHourStruct(
                target_temp=22.5, next_change_at=time(hour=23, minute=30)
            ),
        ],
    )
    data = command.to_bytes()
    characteristic = MagicMock()

    with patch.object(
        thermostat, "_on_schedule_received", new_callable=AsyncMock
    ) as mock_on_schedule_received:
        await thermostat._on_message_received(characteristic, bytearray(data))

        mock_on_schedule_received.assert_called_once_with(Schedule._from_bytes(data))


@pytest.mark.asyncio
async def test_on_message_received_unknown(thermostat: Thermostat) -> None:
    command = _Eq3Message(cmd=0xFF, is_status_command=False, data=b"")
    data = command.to_bytes()
    characteristic = MagicMock()

    with pytest.raises(Eq3InternalException, match="Unknown command"):
        await thermostat._on_message_received(characteristic, bytearray(data))


@pytest.mark.asyncio
async def test_on_device_data_received(thermostat: Thermostat) -> None:
    device_data = MagicMock()

    with patch.object(
        thermostat, "_trigger_event", new_callable=AsyncMock
    ) as mock_trigger_event:
        await thermostat._on_device_data_received(device_data)

        mock_trigger_event.assert_called_once_with(
            Eq3Event.DEVICE_DATA_RECEIVED, device_data=device_data
        )


@pytest.mark.asyncio
async def test_on_status_received(thermostat: Thermostat) -> None:
    status = MagicMock()

    with patch.object(
        thermostat, "_trigger_event", new_callable=AsyncMock
    ) as mock_trigger_event:
        await thermostat._on_status_received(status)

        mock_trigger_event.assert_called_once_with(
            Eq3Event.STATUS_RECEIVED, status=status
        )


@pytest.mark.asyncio
async def test_on_schedule_received(thermostat: Thermostat) -> None:
    schedule = MagicMock()

    with patch.object(
        thermostat, "_trigger_event", new_callable=AsyncMock
    ) as mock_trigger_event:
        await thermostat._on_schedule_received(schedule)

        mock_trigger_event.assert_called_once_with(
            Eq3Event.SCHEDULE_RECEIVED, schedule=schedule
        )


@pytest.mark.asyncio
async def test_register_callback(thermostat: Thermostat) -> None:
    callback = lambda: None

    thermostat.register_callback(Eq3Event.DISCONNECTED, callback)

    assert thermostat._callbacks[Eq3Event.DISCONNECTED] == [callback]

    thermostat.register_callback(Eq3Event.DISCONNECTED, callback)

    assert thermostat._callbacks[Eq3Event.DISCONNECTED] == [callback]


@pytest.mark.asyncio
async def test_unregister_event(thermostat: Thermostat) -> None:
    callback = lambda: None

    assert thermostat._callbacks[Eq3Event.DISCONNECTED] == []

    thermostat.unregister_callback(Eq3Event.DISCONNECTED, callback)

    assert thermostat._callbacks[Eq3Event.DISCONNECTED] == []

    thermostat.register_callback(Eq3Event.DISCONNECTED, callback)

    assert thermostat._callbacks[Eq3Event.DISCONNECTED] == [callback]

    thermostat.unregister_callback(Eq3Event.DISCONNECTED, callback)

    assert thermostat._callbacks[Eq3Event.DISCONNECTED] == []


@pytest.mark.asyncio
async def test_trigger_event_connected(thermostat: Thermostat) -> None:
    device_data = DeviceData(321, "0000011111")
    status = Status(
        0, 20.5, Eq3OperationMode.AUTO, False, False, True, False, True, False
    )
    schedule = Schedule()
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.CONNECTED] = [callback]

    await thermostat._trigger_event(
        Eq3Event.CONNECTED, device_data=device_data, status=status, schedule=schedule
    )

    callback.assert_called_once_with(device_data, status, schedule)


@pytest.mark.asyncio
async def test_trigger_event_connected_invalid_data(thermostat: Thermostat) -> None:
    device_data = DeviceData(321, "0000011111")
    status = Status(
        0, 20.5, Eq3OperationMode.AUTO, False, False, True, False, True, False
    )
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.CONNECTED] = [callback]

    with pytest.raises(Eq3InternalException, match="must not be None for"):
        await thermostat._trigger_event(
            Eq3Event.CONNECTED,
            device_data=device_data,
            status=status,
            schedule=None,  # type: ignore
        )

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_event_disconnected(thermostat: Thermostat) -> None:
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.DISCONNECTED] = [callback]

    await thermostat._trigger_event(Eq3Event.DISCONNECTED)

    callback.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_event_device_data_received(thermostat: Thermostat) -> None:
    device_data = DeviceData(321, "0000011111")
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.DEVICE_DATA_RECEIVED] = [callback]

    await thermostat._trigger_event(
        Eq3Event.DEVICE_DATA_RECEIVED, device_data=device_data
    )

    callback.assert_called_once_with(device_data)


@pytest.mark.asyncio
async def test_trigger_event_device_data_received_invalid_data(
    thermostat: Thermostat,
) -> None:
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.DEVICE_DATA_RECEIVED] = [callback]

    with pytest.raises(Eq3InternalException, match="must not be None for"):
        await thermostat._trigger_event(Eq3Event.DEVICE_DATA_RECEIVED, device_data=None)  # type: ignore

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_event_status_received(thermostat: Thermostat) -> None:
    status = Status(
        0, 20.5, Eq3OperationMode.AUTO, False, False, True, False, True, False
    )
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.STATUS_RECEIVED] = [callback]

    await thermostat._trigger_event(Eq3Event.STATUS_RECEIVED, status=status)

    callback.assert_called_once_with(status)


@pytest.mark.asyncio
async def test_trigger_event_status_received_invalid_data(
    thermostat: Thermostat,
) -> None:
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.STATUS_RECEIVED] = [callback]

    with pytest.raises(Eq3InternalException, match="must not be None for"):
        await thermostat._trigger_event(Eq3Event.STATUS_RECEIVED, status=None)  # type: ignore

    callback.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_event_schedule_received(thermostat: Thermostat) -> None:
    schedule = Schedule()
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.SCHEDULE_RECEIVED] = [callback]

    await thermostat._trigger_event(Eq3Event.SCHEDULE_RECEIVED, schedule=schedule)

    callback.assert_called_once_with(schedule)


@pytest.mark.asyncio
async def test_trigger_event_schedule_received_invalid_data(
    thermostat: Thermostat,
) -> None:
    callback = MagicMock()
    thermostat._callbacks[Eq3Event.SCHEDULE_RECEIVED] = [callback]

    with pytest.raises(Eq3InternalException, match="must not be None for"):
        await thermostat._trigger_event(Eq3Event.SCHEDULE_RECEIVED, schedule=None)  # type: ignore

    callback.assert_not_called()


@pytest.mark.asyncio
async def tests_trigger_event_connected_async(thermostat: Thermostat) -> None:
    device_data = DeviceData(321, "0000011111")
    status = Status(
        0, 20.5, Eq3OperationMode.AUTO, False, False, True, False, True, False
    )
    schedule = Schedule()
    callback = AsyncMock()
    thermostat._callbacks[Eq3Event.CONNECTED] = [callback]

    await thermostat._trigger_event(
        Eq3Event.CONNECTED, device_data=device_data, status=status, schedule=schedule
    )

    callback.assert_called_once_with(device_data, status, schedule)
