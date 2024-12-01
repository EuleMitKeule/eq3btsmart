"""Support for eq3 Bluetooth Smart thermostats."""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from types import TracebackType
from typing import Awaitable, Callable, Literal, Self, Union, overload

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from construct_typed import DataclassStruct

from eq3btsmart.adapter.eq3_temperature import Eq3Temperature
from eq3btsmart.const import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_CONNECTION_TIMEOUT,
    EQ3BT_OFF_TEMP,
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
from eq3btsmart.models import DeviceData, Schedule, Status
from eq3btsmart.models.presets import Presets
from eq3btsmart.structures import (
    AwaySetCommand,
    BoostSetCommand,
    ComfortEcoConfigureCommand,
    ComfortSetCommand,
    EcoSetCommand,
    Eq3Message,
    Eq3Struct,
    IdGetCommand,
    InfoGetCommand,
    LockSetCommand,
    ModeSetCommand,
    OffsetConfigureCommand,
    ScheduleGetCommand,
    ScheduleHourStruct,
    ScheduleSetCommand,
    TemperatureSetCommand,
    WindowOpenConfigureCommand,
)


class Thermostat:
    """Representation of a EQ3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        mac_address: str,
        connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
    ):
        """Initialize the thermostat."""

        self.mac_address = mac_address

        self._last_status: Status | None = None
        self._last_device_data: DeviceData | None = None
        self._last_schedule: Schedule | None = None

        self._callbacks: defaultdict[
            Eq3Event, list[Union[Callable[..., None], Callable[..., Awaitable[None]]]]
        ] = defaultdict(list)
        self._conn: BleakClient = BleakClient(
            mac_address,
            disconnected_callback=self._on_disconnected,
            timeout=DEFAULT_CONNECTION_TIMEOUT,
        )
        self._device_data_future: asyncio.Future[DeviceData] | None = None
        self._status_future: asyncio.Future[Status] | None = None
        self._schedule_future: asyncio.Future[Schedule] | None = None
        self._schedule_future_counter: int = 0
        self._lock = asyncio.Lock()
        self._connection_timeout = connection_timeout
        self._command_timeout = command_timeout

    @property
    def is_connected(self) -> bool:
        """Check if the thermostat is connected."""
        return self._conn.is_connected

    @property
    def device_data(self) -> DeviceData:
        """Get the last known device data, ensuring it's not None."""
        if self._last_device_data is None:
            raise Eq3StateException("Device data not set")
        return self._last_device_data

    @property
    def status(self) -> Status:
        """Get the last known status, ensuring it's not None."""
        if self._last_status is None:
            raise Eq3StateException("Status not set")
        return self._last_status

    @property
    def presets(self) -> Presets:
        """Get the presets from the last known status."""

        if self.status.presets is None:
            raise Eq3StateException("Presets not set")
        return self.status.presets

    @property
    def schedule(self) -> Schedule:
        """Get the last known schedule, ensuring it's not None."""
        if self._last_schedule is None:
            raise Eq3StateException("Schedule not set")
        return self._last_schedule

    async def async_connect(self) -> None:
        """Connect to the thermostat."""

        try:
            await asyncio.wait_for(self._conn.connect(), self._connection_timeout)
            await self._conn.start_notify(
                Eq3Characteristic.NOTIFY, self._on_message_received
            )
            (
                self._last_device_data,
                self._last_status,
                self._last_schedule,
            ) = await asyncio.gather(
                self.async_get_device_data(),
                self.async_get_status(),
                self.async_get_schedule(),
            )
        except BleakError as ex:
            raise Eq3ConnectionException("Could not connect to the device") from ex
        except TimeoutError as ex:
            raise Eq3TimeoutException("Timeout during connection") from ex

        await self.trigger_event(
            Eq3Event.CONNECTED,
            device_data=self.device_data,
            status=self.status,
            schedule=self.schedule,
        )

    async def async_disconnect(self) -> None:
        """Shutdown the connection to the thermostat."""

        exception = Eq3ConnectionException("Connection closed")
        if self._device_data_future is not None and not self._device_data_future.done():
            self._device_data_future.set_exception(exception)

        if self._status_future is not None and not self._status_future.done():
            self._status_future.set_exception(exception)

        if self._schedule_future is not None and not self._schedule_future.done():
            self._schedule_future.set_exception(exception)

        try:
            await self._conn.disconnect()
        except BleakError as ex:
            raise Eq3ConnectionException("Could not disconnect from the device") from ex
        except TimeoutError as ex:
            raise Eq3TimeoutException("Timeout during disconnection") from ex

    async def async_get_device_data(self) -> DeviceData:
        """Query device identification information, e.g. the serial number."""

        return await self._async_write_command_with_device_data_response(IdGetCommand())

    async def async_get_status(self) -> Status:
        """Query the thermostat status."""

        return await self._async_write_command_with_status_response(
            InfoGetCommand(time=datetime.now())
        )

    async def async_get_schedule(self) -> Schedule:
        """Query the schedule."""

        return await self._async_write_commands_with_schedule_response(
            [ScheduleGetCommand(day=week_day) for week_day in WeekDay]
        )

    async def async_configure_window_open(
        self, temperature: float, duration: timedelta
    ) -> Status:
        """Configures the window open behavior. The duration is specified in 5 minute increments."""

        return await self._async_write_command_with_status_response(
            WindowOpenConfigureCommand(
                window_open_temperature=temperature,
                window_open_time=duration,
            )
        )

    async def async_configure_window_open_temperature(
        self, temperature: float
    ) -> Status:
        """Configures the window open temperature."""

        return await self.async_configure_window_open(
            temperature, self.presets.window_open_time
        )

    async def async_configure_window_open_duration(
        self,
        duration: timedelta | float,
    ) -> Status:
        """Configures the window open duration."""

        if isinstance(duration, float):
            duration = timedelta(minutes=duration)

        return await self.async_configure_window_open(
            self.presets.window_open_temperature, duration
        )

    async def async_configure_presets(
        self,
        comfort_temperature: float,
        eco_temperature: float,
    ) -> Status:
        """Set the thermostats preset temperatures comfort (sun) and eco (moon)."""

        return await self._async_write_command_with_status_response(
            ComfortEcoConfigureCommand(
                comfort_temperature=comfort_temperature,
                eco_temperature=eco_temperature,
            )
        )

    async def async_configure_comfort_temperature(
        self, comfort_temperature: float
    ) -> Status:
        """Sets the thermostat's comfort temperature."""

        return await self.async_configure_presets(
            comfort_temperature, self.presets.eco_temperature
        )

    async def async_configure_eco_temperature(self, eco_temperature: float) -> Status:
        """Sets the thermostat's eco temperature."""

        return await self.async_configure_presets(
            self.presets.comfort_temperature, eco_temperature
        )

    async def async_configure_temperature_offset(
        self, temperature_offset: float
    ) -> Status:
        """Sets the thermostat's temperature offset."""

        return await self._async_write_command_with_status_response(
            OffsetConfigureCommand(offset=temperature_offset)
        )

    async def async_set_mode(self, operation_mode: OperationMode) -> Status:
        """Set new operation mode."""

        command: ModeSetCommand

        match operation_mode:
            case OperationMode.AUTO:
                command = ModeSetCommand(mode=OperationMode.AUTO)
            case OperationMode.MANUAL:
                command = ModeSetCommand(
                    mode=OperationMode.MANUAL
                    | Eq3Temperature.encode(self.status.target_temperature)
                )
            case OperationMode.OFF:
                command = ModeSetCommand(
                    mode=OperationMode.MANUAL | Eq3Temperature.encode(EQ3BT_OFF_TEMP)
                )
            case OperationMode.ON:
                command = ModeSetCommand(
                    mode=OperationMode.MANUAL | Eq3Temperature.encode(EQ3BT_ON_TEMP)
                )

        return await self._async_write_command_with_status_response(command)

    async def async_set_away(
        self,
        away_until: datetime,
        temperature: float,
    ) -> Status:
        """Set away mode."""

        return await self._async_write_command_with_status_response(
            AwaySetCommand(
                mode=OperationMode.AWAY | Eq3Temperature.encode(temperature),
                away_until=away_until,
            )
        )

    async def async_set_temperature(self, temperature: float) -> Status:
        """Set new target temperature."""

        if temperature == EQ3BT_OFF_TEMP:
            return await self.async_set_mode(OperationMode.OFF)

        if temperature == EQ3BT_ON_TEMP:
            return await self.async_set_mode(OperationMode.ON)

        return await self._async_write_command_with_status_response(
            TemperatureSetCommand(temperature=temperature)
        )

    async def async_set_preset(self, preset: Eq3Preset) -> Status:
        """Sets the thermostat to the given preset."""

        command: ComfortSetCommand | EcoSetCommand

        match preset:
            case Eq3Preset.COMFORT:
                command = ComfortSetCommand()
            case Eq3Preset.ECO:
                command = EcoSetCommand()

        return await self._async_write_command_with_status_response(command)

    async def async_set_boost(self, enable: bool) -> Status:
        """Sets boost mode."""

        return await self._async_write_command_with_status_response(
            BoostSetCommand(enable=enable)
        )

    async def async_set_locked(self, enable: bool) -> Status:
        """Locks or unlocks the thermostat."""

        return await self._async_write_command_with_status_response(
            LockSetCommand(enable=enable)
        )

    async def async_delete_schedule(
        self, week_days: list[WeekDay] | WeekDay | None = None
    ) -> Schedule:
        """Deletes the schedule."""

        week_days = (
            [week_days]
            if isinstance(week_days, WeekDay)
            else week_days or list(WeekDay)
        )

        return await self._async_write_commands_with_schedule_response(
            [ScheduleSetCommand(day=week_day, hours=[]) for week_day in week_days]
        )

    async def async_set_schedule(self, schedule: Schedule) -> Schedule:
        """Sets the schedule."""

        return await self._async_write_commands_with_schedule_response(
            [
                ScheduleSetCommand(
                    day=schedule_day.week_day,
                    hours=[
                        ScheduleHourStruct(
                            target_temp=schedule_hour.target_temperature,
                            next_change_at=schedule_hour.next_change_at,
                        )
                        for schedule_hour in schedule_day.schedule_hours
                    ],
                )
                for schedule_day in schedule.schedule_days
            ]
        )

    ### Internal ###

    async def __aenter__(self) -> Self:
        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.async_disconnect()

    async def _async_write_command_with_device_data_response(
        self, command: Eq3Struct
    ) -> DeviceData:
        """Write a command to the thermostat and wait for a device data response."""

        if self._device_data_future is not None:
            raise Eq3AlreadyAwaitingResponseException(
                "Already awaiting a device data command response"
            )

        self._device_data_future = asyncio.Future()

        await self._async_write_command(command)

        try:
            device_data = await asyncio.wait_for(
                self._device_data_future, self._command_timeout
            )
        except TimeoutError as ex:
            raise Eq3TimeoutException("Timeout during device data command") from ex
        finally:
            self._device_data_future = None

        return device_data

    async def _async_write_command_with_status_response(
        self, command: Eq3Struct
    ) -> Status:
        """Write a command to the thermostat and wait for a status response."""

        if self._status_future is not None:
            raise Eq3AlreadyAwaitingResponseException(
                "Already awaiting a status command response"
            )

        self._status_future = asyncio.Future()

        await self._async_write_command(command)

        try:
            status = await asyncio.wait_for(self._status_future, self._command_timeout)
        except TimeoutError as ex:
            raise Eq3TimeoutException("Timeout during status command") from ex
        finally:
            self._status_future = None

        return status

    async def _async_write_commands_with_schedule_response(
        self, commands: list[Eq3Struct]
    ) -> Schedule:
        """Write commands to the thermostat and wait for a schedule response."""

        if self._schedule_future is not None:
            raise Eq3AlreadyAwaitingResponseException(
                "Already awaiting a schedule command response"
            )

        self._schedule_future = asyncio.Future()
        self._schedule_future_counter = len(commands)

        for command in commands:
            await self._async_write_command(command)

        try:
            schedule = await asyncio.wait_for(
                self._schedule_future, self._command_timeout
            )
        except TimeoutError as ex:
            raise Eq3TimeoutException("Timeout during schedule command") from ex
        finally:
            self._schedule_future = None

        return schedule

    async def _async_write_command(self, command: Eq3Struct) -> None:
        """Write a command to the thermostat."""

        if not self._conn.is_connected:
            raise Eq3ConnectionException("Not connected")

        data = command.to_bytes()

        async with self._lock:
            try:
                await asyncio.wait_for(
                    self._conn.write_gatt_char(Eq3Characteristic.WRITE, data),
                    self._command_timeout,
                )
            except BleakError as ex:
                raise Eq3CommandException("Error during write") from ex
            except TimeoutError as ex:
                raise Eq3TimeoutException("Timeout during write") from ex

    def _on_disconnected(self, client: BleakClient) -> None:
        """Handle disconnection from the thermostat."""

        asyncio.create_task(self.trigger_event(Eq3Event.DISCONNECTED))

    async def _on_message_received(
        self, handle: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle received messages from the thermostat."""

        data_bytes = bytes(data)
        command = DataclassStruct(Eq3Message).parse(data_bytes)

        match command.cmd:
            case Command.ID_RETURN:
                device_data = DeviceData.from_bytes(data_bytes)
                return await self._on_device_data_received(device_data)
            case Command.INFO_RETURN:
                if not command.is_status_command:
                    return

                status = Status.from_bytes(data_bytes)
                return await self._on_status_received(status)
            case Command.SCHEDULE_RETURN:
                schedule = Schedule.from_bytes(data_bytes)
                return await self._on_schedule_received(schedule)
            case _:
                raise Eq3InternalException(f"Unknown command: {command}")

    async def _on_device_data_received(self, device_data: DeviceData) -> None:
        """Handle received device data."""

        self._last_device_data = device_data

        if self._device_data_future is not None:
            return self._device_data_future.set_result(device_data)

        await self.trigger_event(Eq3Event.DEVICE_DATA_RECEIVED, device_data=device_data)

    async def _on_status_received(self, status: Status) -> None:
        """Handle received status."""

        self._last_status = status

        if self._status_future is not None:
            return self._status_future.set_result(status)

        await self.trigger_event(Eq3Event.STATUS_RECEIVED, status=status)

    async def _on_schedule_received(self, schedule: Schedule) -> None:
        """Handle received schedule."""

        if self._last_schedule is None:
            self._last_schedule = schedule

        self._last_schedule.merge(schedule)

        if self._schedule_future is not None:
            self._schedule_future_counter -= 1

            if self._schedule_future_counter == 0:
                return self._schedule_future.set_result(self._last_schedule)

        else:
            await self.trigger_event(
                Eq3Event.SCHEDULE_RECEIVED, schedule=self._last_schedule
            )

    ### Callbacks ###

    @overload
    def register_callback(
        self,
        event: Literal[Eq3Event.DISCONNECTED],
        callback: Union[Callable[[], None], Callable[[], Awaitable[None]]],
    ) -> None: ...

    @overload
    def register_callback(
        self,
        event: Union[Literal[Eq3Event.CONNECTED]],
        callback: Union[
            Callable[[DeviceData, Status, Schedule], None],
            Callable[[DeviceData, Status, Schedule], Awaitable[None]],
        ],
    ) -> None: ...

    @overload
    def register_callback(
        self,
        event: Literal[Eq3Event.DEVICE_DATA_RECEIVED],
        callback: Union[
            Callable[[DeviceData], None], Callable[[DeviceData], Awaitable[None]]
        ],
    ) -> None: ...

    @overload
    def register_callback(
        self,
        event: Literal[Eq3Event.STATUS_RECEIVED],
        callback: Union[Callable[[Status], None], Callable[[Status], Awaitable[None]]],
    ) -> None: ...

    @overload
    def register_callback(
        self,
        event: Literal[Eq3Event.SCHEDULE_RECEIVED],
        callback: Union[
            Callable[[Schedule], None], Callable[[Schedule], Awaitable[None]]
        ],
    ) -> None: ...

    def register_callback(
        self,
        event: Eq3Event,
        callback: Union[Callable[..., None], Callable[..., Awaitable[None]]],
    ) -> None:
        """Register a callback for a specific event."""

        if callback in self._callbacks[event]:
            return

        self._callbacks[event].append(callback)

    def unregister_callback(
        self,
        event: Eq3Event,
        callback: Union[Callable[..., None], Callable[..., Awaitable[None]]],
    ) -> None:
        """Unregister a callback for a specific event."""

        if callback not in self._callbacks[event]:
            return

        self._callbacks[event].remove(callback)

    @overload
    async def trigger_event(self, event: Literal[Eq3Event.DISCONNECTED]) -> None: ...

    @overload
    async def trigger_event(
        self,
        event: Literal[Eq3Event.CONNECTED],
        *,
        device_data: DeviceData,
        status: Status,
        schedule: Schedule,
    ) -> None: ...

    @overload
    async def trigger_event(
        self,
        event: Literal[Eq3Event.DEVICE_DATA_RECEIVED],
        *,
        device_data: DeviceData,
    ) -> None: ...

    @overload
    async def trigger_event(
        self,
        event: Literal[Eq3Event.STATUS_RECEIVED],
        *,
        status: Status,
    ) -> None: ...

    @overload
    async def trigger_event(
        self,
        event: Literal[Eq3Event.SCHEDULE_RECEIVED],
        *,
        schedule: Schedule,
    ) -> None: ...

    async def trigger_event(
        self,
        event: Eq3Event,
        *,
        device_data: DeviceData | None = None,
        status: Status | None = None,
        schedule: Schedule | None = None,
    ) -> None:
        """Call the callbacks for a specific event."""

        async_callbacks = [
            callback
            for callback in self._callbacks[event]
            if asyncio.iscoroutinefunction(callback)
        ]
        sync_callbacks = [
            callback
            for callback in self._callbacks[event]
            if not asyncio.iscoroutinefunction(callback)
        ]

        args: (
            tuple[DeviceData, Status, Schedule]
            | tuple[DeviceData]
            | tuple[Status]
            | tuple[Schedule]
            | tuple[()]
        )

        match event:
            case Eq3Event.DISCONNECTED:
                args = ()
            case Eq3Event.CONNECTED:
                if device_data is None or status is None or schedule is None:
                    raise Eq3InternalException(
                        "device_data, status, and schedule must not be None for CONNECTED event"
                    )
                args = (device_data, status, schedule)
            case Eq3Event.DEVICE_DATA_RECEIVED:
                if device_data is None:
                    raise Eq3InternalException(
                        "device_data must not be None for DEVICE_DATA_RECEIVED event"
                    )
                args = (device_data,)
            case Eq3Event.STATUS_RECEIVED:
                if status is None:
                    raise Eq3InternalException(
                        "status must not be None for STATUS_RECEIVED event"
                    )
                args = (status,)
            case Eq3Event.SCHEDULE_RECEIVED:
                if schedule is None:
                    raise Eq3InternalException(
                        "schedule must not be None for SCHEDULE_RECEIVED event"
                    )
                args = (schedule,)

        await asyncio.gather(*[callback(*args) for callback in async_callbacks])

        for callback in sync_callbacks:
            callback(*args)
