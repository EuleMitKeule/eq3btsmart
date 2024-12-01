from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
from typing import Any, Awaitable, Callable, Type

from bleak.backends.device import BLEDevice

from eq3btsmart.const import (
    Eq3Characteristic,
    StatusFlags,
    WeekDay,
)
from eq3btsmart.structures import (
    AwaySetCommand,
    BoostSetCommand,
    ComfortEcoConfigureCommand,
    ComfortSetCommand,
    DeviceDataStruct,
    EcoSetCommand,
    Eq3Struct,
    IdGetCommand,
    InfoGetCommand,
    LockSetCommand,
    ModeSetCommand,
    OffsetConfigureCommand,
    PresetsStruct,
    ScheduleDayStruct,
    ScheduleGetCommand,
    ScheduleHourStruct,
    ScheduleSetCommand,
    StatusStruct,
    TemperatureSetCommand,
    WindowOpenConfigureCommand,
)

mock_id = DeviceDataStruct(
    version=1, unknown_1=0, unknown_2=0, serial="serial1234", unknown_3=0
)


mock_presets = PresetsStruct(
    comfort_temp=21,
    eco_temp=17,
    window_open_temp=12,
    window_open_time=timedelta(minutes=5),
    offset=0,
)
mock_status = StatusStruct(
    mode=StatusFlags.MANUAL,
    valve=0x10,
    target_temp=21,
)
mock_status.presets = mock_presets
mock_status.away = datetime.now() - timedelta(days=1)


mock_schedule_days: list[ScheduleDayStruct] = [
    ScheduleDayStruct(
        day=week_day,
        hours=[
            ScheduleHourStruct(
                target_temp=21,
                next_change_at=time(hour=0, minute=0),
            )
        ],
    )
    for week_day in WeekDay
]


class MockClient:
    def __init__(
        self,
        device: BLEDevice,
        disconnected_callback: Callable[[MockClient], None] | None = None,
        timeout: int = 10,
    ):
        self.device = device
        self._is_connected: bool = False
        self._notify_callbacks: list[Callable[[str, bytes], Awaitable[None]]] = []
        self._disconnected_callback: Callable[[MockClient], None] | None = (
            disconnected_callback
        )
        self._timeout: int = timeout
        self._last_command: Eq3Struct | None = None
        self._fail_on_connect: bool = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self, **kwargs: dict[str, Any]) -> None:
        self._is_connected = True

    async def disconnect(self) -> None:
        self._is_connected = False
        if self._disconnected_callback:
            self._disconnected_callback(self)

    async def start_notify(
        self, char: str, callback: Callable[[str, bytes], Awaitable[None]]
    ) -> None:
        self._notify_callbacks.append(callback)

    async def write_gatt_char(self, char: str, data: bytes) -> None:
        command_types: list[Type[Eq3Struct]] = [
            IdGetCommand,
            InfoGetCommand,
            ComfortEcoConfigureCommand,
            OffsetConfigureCommand,
            WindowOpenConfigureCommand,
            ScheduleGetCommand,
            AwaySetCommand,
            ModeSetCommand,
            TemperatureSetCommand,
            ScheduleSetCommand,
            ComfortSetCommand,
            EcoSetCommand,
            BoostSetCommand,
            LockSetCommand,
        ]

        for command_type in command_types:
            try:
                command = command_type.from_bytes(data)
                break
            except Exception:
                continue

        if isinstance(command, WindowOpenConfigureCommand):
            window_open_configure_command: WindowOpenConfigureCommand = command

            mock_presets.window_open_temp = (
                window_open_configure_command.window_open_temperature
            )
            mock_presets.window_open_time = (
                window_open_configure_command.window_open_time
            )

        if isinstance(command, ComfortEcoConfigureCommand):
            comfort_eco_configure_command: ComfortEcoConfigureCommand = command

            mock_presets.comfort_temp = (
                comfort_eco_configure_command.comfort_temperature
            )
            mock_presets.eco_temp = comfort_eco_configure_command.eco_temperature

        if isinstance(command, OffsetConfigureCommand):
            offset_configure_command: OffsetConfigureCommand = command

            mock_presets.offset = offset_configure_command.offset

        if isinstance(command, ModeSetCommand):
            mode_set_command: ModeSetCommand = command
            mode_int = mode_set_command.mode
            temp: int | None = None

            if 0x3C <= mode_int <= 0x80:
                mode_int -= 0x40
                mode = StatusFlags.MANUAL
                temp = mode_int
            elif mode_int >= 0x80:
                mode_int -= 0x80
                mode = StatusFlags.AWAY
                temp = mode_int
            else:
                mode = StatusFlags(mode_int)

            mock_status.mode = mode

            if temp is not None:
                mock_status.target_temp = temp / 2

        if isinstance(command, TemperatureSetCommand):
            mock_status.target_temp = command.temperature

        if isinstance(command, ComfortSetCommand):
            mock_status.target_temp = mock_presets.comfort_temp

        if isinstance(command, EcoSetCommand):
            mock_status.target_temp = mock_presets.eco_temp

        if isinstance(command, BoostSetCommand):
            if command.enable:
                mock_status.mode |= StatusFlags.BOOST
            else:
                mock_status.mode &= ~StatusFlags.BOOST

        if isinstance(command, LockSetCommand):
            if command.enable:
                mock_status.mode |= StatusFlags.LOCKED
            else:
                mock_status.mode &= ~StatusFlags.LOCKED

        if isinstance(command, ScheduleSetCommand):
            schedule_day = next(
                (
                    schedule_day
                    for schedule_day in mock_schedule_days
                    if schedule_day.day == command.day
                ),
                ScheduleDayStruct(day=command.day, hours=[]),
            )
            schedule_day.hours = command.hours

        self._last_command = command

        await self.respond()

    async def respond(self) -> None:
        if isinstance(self._last_command, (ScheduleGetCommand, ScheduleSetCommand)):
            mock_schedule_day = next(
                (
                    schedule_day
                    for schedule_day in mock_schedule_days
                    if schedule_day.day == self._last_command.day
                ),
                ScheduleDayStruct(
                    day=self._last_command.day,
                    hours=[
                        ScheduleHourStruct(
                            target_temp=21,
                            next_change_at=time(hour=0, minute=0),
                        )
                    ],
                ),
            )
            data = mock_schedule_day.to_bytes()

        if isinstance(self._last_command, IdGetCommand):
            data = mock_id.to_bytes()

        elif isinstance(
            self._last_command,
            (
                InfoGetCommand,
                ComfortEcoConfigureCommand,
                OffsetConfigureCommand,
                WindowOpenConfigureCommand,
                ModeSetCommand,
                AwaySetCommand,
                TemperatureSetCommand,
                ComfortSetCommand,
                EcoSetCommand,
                BoostSetCommand,
                LockSetCommand,
            ),
        ):
            data = mock_status.to_bytes()

        asyncio.create_task(self.notify(data))
        self._last_command = None

    async def notify(self, data: bytes) -> None:
        for callback in self._notify_callbacks:
            await callback(
                Eq3Characteristic.NOTIFY,
                data,
            )
