"""Support for eQ-3 Bluetooth Smart thermostats."""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from types import TracebackType
from typing import Awaitable, Callable, Literal, Self, Union, overload

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from construct_typed import DataclassStruct

from eq3btsmart._adapters import _Eq3Temperature
from eq3btsmart._structures import (
    _AwaySetCommand,
    _BoostSetCommand,
    _ComfortEcoConfigureCommand,
    _ComfortSetCommand,
    _EcoSetCommand,
    _Eq3Message,
    _Eq3Struct,
    _IdGetCommand,
    _InfoGetCommand,
    _LockSetCommand,
    _ModeSetCommand,
    _OffsetConfigureCommand,
    _ScheduleGetCommand,
    _ScheduleHourStruct,
    _ScheduleSetCommand,
    _TemperatureSetCommand,
    _WindowOpenConfigureCommand,
)
from eq3btsmart.const import (
    DEFAULT_COMMAND_TIMEOUT,
    DEFAULT_CONNECTION_TIMEOUT,
    EQ3_OFF_TEMP,
    EQ3_ON_TEMP,
    Eq3Event,
    Eq3OperationMode,
    Eq3Preset,
    Eq3WeekDay,
    _Eq3Characteristic,
    _Eq3Command,
)
from eq3btsmart.exceptions import (
    Eq3CommandException,
    Eq3ConnectionException,
    Eq3InternalException,
    Eq3InvalidDataException,
    Eq3StateException,
    Eq3TimeoutException,
)
from eq3btsmart.models import DeviceData, Presets, Schedule, Status

__all__ = ["Thermostat"]


class _ResponseType(Enum):
    """Expected response types for queued commands."""

    DEVICE_DATA = auto()
    STATUS = auto()
    SCHEDULE = auto()


@dataclass
class _QueuedCommand:
    """Represents a command waiting for a response."""

    command: _Eq3Struct
    response_type: _ResponseType
    future: asyncio.Future
    schedule_count: int = 0


class Thermostat:
    """Representation of an eQ-3 Bluetooth Smart thermostat."""

    def __init__(
        self,
        device: BLEDevice,
        connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT,
        command_timeout: int = DEFAULT_COMMAND_TIMEOUT,
    ):
        """Initialize the thermostat.

        The thermostat will be in a disconnected state after initialization.

        Args:
            device (BLEDevice): The BLEDevice instance.
            connection_timeout (int, optional): The connection timeout in seconds. Defaults to DEFAULT_CONNECTION_TIMEOUT.
            command_timeout (int, optional): The command timeout in seconds. Defaults to DEFAULT_COMMAND_TIMEOUT.
        """
        self._last_status: Status | None = None
        self._last_device_data: DeviceData | None = None
        self._last_schedule: Schedule | None = None

        self._conn: BleakClient | None = None
        self._device = device
        self._callbacks: defaultdict[
            Eq3Event, list[Union[Callable[..., None], Callable[..., Awaitable[None]]]]
        ] = defaultdict(list)
        self._command_queue: deque[_QueuedCommand] = deque()
        self._lock = asyncio.Lock()
        self._connection_timeout = connection_timeout
        self._command_timeout = command_timeout

    @property
    def is_connected(self) -> bool:
        """Check if the thermostat is connected.

        Returns:
            bool: True if connected, False otherwise.
        """
        return conn.is_connected if (conn := self._conn) else False

    @property
    def device_data(self) -> DeviceData:
        """Get the last known device data, ensuring it's not None.

        Returns:
            DeviceData: The last known device data.

        Raises:
            Eq3StateException: If the device data is None. This occurs when the thermostat has not been connected yet.
        """
        if self._last_device_data is None:
            raise Eq3StateException("Device data not set")
        return self._last_device_data

    @property
    def status(self) -> Status:
        """Get the last known status, ensuring it's not None.

        Returns:
            Status: The last known status.

        Raises:
            Eq3StateException: If the status is None. This occurs when the thermostat has not been connected yet.
        """
        if self._last_status is None:
            raise Eq3StateException("Status not set")
        return self._last_status

    @property
    def presets(self) -> Presets:
        """Get the presets from the last known status.

        Presets are only available since firmware version MIN_PRESETS_FW_VERSION.

        Returns:
            Presets: The presets.

        Raises:
            Eq3StateException: If the presets are None. This occurs when the thermostat has not been connected yet or if the thermostat's firmware does not support presets.
        """
        if self.status.presets is None:
            raise Eq3StateException("Presets not set")
        return self.status.presets

    @property
    def schedule(self) -> Schedule:
        """Get the last known schedule, ensuring it's not None.

        Returns:
            Schedule: The last known schedule.

        Raises:
            Eq3StateException: If the schedule is None. This occurs when the thermostat has not been connected
        """
        if self._last_schedule is None:
            raise Eq3StateException("Schedule not set")
        return self._last_schedule

    async def async_connect(self) -> None:
        """Connect to the thermostat.

        After connecting, the device data, status, and schedule will be queried and stored.
        When the connection is established, the CONNECTED event will be triggered.

        Raises:
            Eq3StateException: If the thermostat is already connected.
            Eq3ConnectionException: If the connection fails.
            Eq3TimeoutException: If the connection times out.
            Eq3CommandException: If an error occurs while sending a command.
        """
        if self.is_connected:
            raise Eq3StateException("Already connected")

        try:
            self._conn = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self._device.name or "",
                disconnected_callback=self._on_disconnected,
                max_attempts=3,
                timeout=self._connection_timeout,
            )
            await self._conn.start_notify(
                _Eq3Characteristic.NOTIFY, self._on_message_received
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

        await self._trigger_event(
            Eq3Event.CONNECTED,
            device_data=self.device_data,
            status=self.status,
            schedule=self.schedule,
        )

    async def async_disconnect(self) -> None:
        """Disconnect from the thermostat.

        Before disconnection all pending futures will be cancelled.
        When the disconnection is complete, the DISCONNECTED event will be triggered.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3ConnectionException: If the disconnection fails.
            Eq3TimeoutException: If the disconnection times out.
        """
        if not self.is_connected or self._conn is None:
            raise Eq3StateException("Not connected")

        exception = Eq3ConnectionException("Connection closed")

        while self._command_queue:
            queued_command = self._command_queue.popleft()
            if not queued_command.future.done():
                queued_command.future.set_exception(exception)

        try:
            await self._conn.disconnect()
        except BleakError as ex:
            raise Eq3ConnectionException("Could not disconnect from the device") from ex
        except TimeoutError as ex:
            raise Eq3TimeoutException("Timeout during disconnection") from ex

    async def async_get_device_data(self) -> DeviceData:
        """Query the latest device data.

        Returns:
            DeviceData: The device data.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
        """
        return await self._async_write_command_with_device_data_response(
            _IdGetCommand()
        )

    async def async_get_status(self) -> Status:
        """Query the latest status.

        Returns:
            Status: The status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
        """
        return await self._async_write_command_with_status_response(
            _InfoGetCommand(time=datetime.now())
        )

    async def async_get_schedule(self) -> Schedule:
        """Query the schedule.

        Returns:
            Schedule: The schedule.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
        """
        return await self._async_write_commands_with_schedule_response(
            [_ScheduleGetCommand(day=week_day) for week_day in Eq3WeekDay]
        )

    async def async_set_temperature(self, temperature: float) -> Status:
        """Set the target temperature.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.
        If the temperature is EQ3_OFF_TEMP, the thermostat will be turned off.
        If the temperature is EQ3_ON_TEMP, the thermostat will be turned on.

        Args:
            temperature (float): The new target temperature in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature is invalid.
        """
        if temperature == EQ3_OFF_TEMP:
            return await self.async_set_mode(Eq3OperationMode.OFF)

        if temperature == EQ3_ON_TEMP:
            return await self.async_set_mode(Eq3OperationMode.ON)

        return await self._async_write_command_with_status_response(
            _TemperatureSetCommand(temperature=temperature)
        )

    async def async_set_mode(self, operation_mode: Eq3OperationMode) -> Status:
        """Set the operation mode.

        Args:
            operation_mode (Eq3OperationMode): The new operation mode.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the operation mode is not supported.
        """
        command: _ModeSetCommand

        match operation_mode:
            case Eq3OperationMode.AUTO:
                command = _ModeSetCommand(mode=Eq3OperationMode.AUTO)
            case Eq3OperationMode.MANUAL:
                command = _ModeSetCommand(
                    mode=Eq3OperationMode.MANUAL
                    | _Eq3Temperature.encode(self.status.target_temperature)
                )
            case Eq3OperationMode.OFF:
                command = _ModeSetCommand(
                    mode=Eq3OperationMode.MANUAL | _Eq3Temperature.encode(EQ3_OFF_TEMP)
                )
            case Eq3OperationMode.ON:
                command = _ModeSetCommand(
                    mode=Eq3OperationMode.MANUAL | _Eq3Temperature.encode(EQ3_ON_TEMP)
                )
            case _:
                raise Eq3InvalidDataException(
                    f"Unsupported operation mode: {operation_mode}"
                )

        return await self._async_write_command_with_status_response(command)

    async def async_set_preset(self, preset: Eq3Preset) -> Status:
        """Activate a preset.

        Args:
            preset (Eq3Preset): The preset to activate.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
        """
        match preset:
            case Eq3Preset.COMFORT:
                command = _ComfortSetCommand()
            case _:
                command = _EcoSetCommand()

        return await self._async_write_command_with_status_response(command)

    async def async_set_boost(self, enable: bool) -> Status:
        """Enable or disable the boost mode.

        The boost mode will set the target temperature to EQ3_ON_TEMP for 300 seconds and then revert to the previous target temperature.

        Args:
            enable (bool): True to enable the boost mode, False to disable it.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
        """
        return await self._async_write_command_with_status_response(
            _BoostSetCommand(enable=enable)
        )

    async def async_set_locked(self, enable: bool) -> Status:
        """Lock or unlock the thermostat.

        When locked, the thermostat's manual controls are disabled.

        Args:
            enable (bool): True to lock the thermostat, False to unlock it.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
        """
        return await self._async_write_command_with_status_response(
            _LockSetCommand(enable=enable)
        )

    async def async_set_away(
        self,
        away_until: datetime,
        temperature: float,
    ) -> Status:
        """Set the thermostat to away mode.

        The thermostat will be set to away mode until the specified date and time.
        The target temperature will be set to the specified temperature.
        Temperatures are in degrees Celsius and specified in 0.5 degree increments.

        Args:
            away_until (datetime): The date and time until the thermostat should be in away mode.
            temperature (float): The target temperature in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature or date is invalid.
        """
        return await self._async_write_command_with_status_response(
            _AwaySetCommand(
                mode=Eq3OperationMode.AWAY | _Eq3Temperature.encode(temperature),
                away_until=away_until,
            )
        )

    async def async_set_schedule(self, schedule: Schedule) -> Schedule:
        """Set the schedule.

        The schedule allows setting different target temperatures for each day of the week and different times of the day.
        It is only applied when the thermostat is in AUTO mode.

        Args:
            schedule: The schedule to set.

        Returns:
            The updated schedule.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If any of the schedule data is invalid.
        """
        return await self._async_write_commands_with_schedule_response(
            [
                _ScheduleSetCommand(
                    day=schedule_day.week_day,
                    hours=[
                        _ScheduleHourStruct(
                            target_temp=schedule_hour.target_temperature,
                            next_change_at=schedule_hour.next_change_at,
                        )
                        for schedule_hour in schedule_day.schedule_hours
                    ],
                )
                for schedule_day in schedule.schedule_days
            ]
        )

    async def async_delete_schedule(
        self, week_days: list[Eq3WeekDay] | Eq3WeekDay | None = None
    ) -> Schedule:
        """Delete the schedule for the specified week days.

        If no week days are specified, the schedule for all week days will be deleted.

        Args:
            week_days (list[WeekDay] | WeekDay | None, optional): The week days for which the schedule should be deleted.
                Can be a single WeekDay, a list of WeekDay, or None. Defaults to None.

        Returns:
            Schedule: The updated schedule after deletion.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs during the command.
            Eq3TimeoutException: If the command times out.
        """
        week_days = (
            [week_days]
            if isinstance(week_days, Eq3WeekDay)
            else week_days or list(Eq3WeekDay)
        )

        return await self._async_write_commands_with_schedule_response(
            [_ScheduleSetCommand(day=week_day, hours=[]) for week_day in week_days]
        )

    async def async_configure_presets(
        self,
        comfort_temperature: float,
        eco_temperature: float,
    ) -> Status:
        """Set the thermostat's preset temperatures.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.
        The initial values are 21.0 degrees Celsius for comfort and 17.0 degrees Celsius for eco.
        The comfort temperature is indicated by the sun symbol and the eco temperature by the moon symbol.

        Args:
            comfort_temperature (float): The comfort temperature in degrees Celsius.
            eco_temperature (float): The eco temperature in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the presets are not available or the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperatures are invalid.
        """
        return await self._async_write_command_with_status_response(
            _ComfortEcoConfigureCommand(
                comfort_temperature=comfort_temperature,
                eco_temperature=eco_temperature,
            )
        )

    async def async_configure_comfort_temperature(
        self, comfort_temperature: float
    ) -> Status:
        """Set the thermostat's comfort temperature.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.
        The initial value is 21.0 degrees Celsius.
        The comfort temperature is indicated by the sun symbol.

        Args:
            comfort_temperature (float): The comfort temperature in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the presets are not available or the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature is invalid.
        """
        return await self.async_configure_presets(
            comfort_temperature, self.presets.eco_temperature
        )

    async def async_configure_eco_temperature(self, eco_temperature: float) -> Status:
        """Set the thermostat's eco temperature.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.
        The initial value is 17.0 degrees Celsius.
        The eco temperature is indicated by the moon symbol.

        Args:
            eco_temperature (float): The eco temperature in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the presets are not available or the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature is invalid.
        """
        return await self.async_configure_presets(
            self.presets.comfort_temperature, eco_temperature
        )

    async def async_configure_temperature_offset(
        self, temperature_offset: float
    ) -> Status:
        """Configure the temperature offset.

        The temperature offset is added to the measured temperature to determine the current temperature the thermostat is using internally for its calculations.
        The initial value is 0.0 degrees Celsius.
        The offset is specified in 0.5 degree increments.
        The maximum offset is EQ3_MAX_TEMP_OFFSET and the minimum offset is EQ3_MIN_TEMP_OFFSET.

        Example:
            When the thermostat is set to 20.0 degrees and the actual temperature in the room is 18.0 degrees, the offset can be set to -2.0 degrees to align the thermostat with the actual temperature.

        Args:
            temperature_offset (float): The temperature offset in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature is invalid.
        """
        return await self._async_write_command_with_status_response(
            _OffsetConfigureCommand(offset=temperature_offset)
        )

    async def async_configure_window_open(
        self, temperature: float, duration: timedelta | float | int
    ) -> Status:
        """Configure the window open behaviour.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.
        Durations are specified in 5 minute increments.
        The initial values are 12.0 degrees Celsius and 15 minutes.
        If a float is provided for the duration, it will be converted to a timedelta with minutes as the unit.

        Args:
            temperature (float): The temperature at which the window open behavior should be triggered in degrees Celsius.
            duration (timedelta | float): The duration for which the window open behavior should be active.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the presets are not available or the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature or duration is invalid.
        """
        if isinstance(duration, float) or isinstance(duration, int):
            duration = timedelta(minutes=duration)

        return await self._async_write_command_with_status_response(
            _WindowOpenConfigureCommand(
                window_open_temperature=temperature,
                window_open_time=duration,
            )
        )

    async def async_configure_window_open_temperature(
        self, temperature: float
    ) -> Status:
        """Configure the window open temperature.

        Temperatures are in degrees Celsius and specified in 0.5 degree increments.
        The initial value is 12.0 degrees Celsius.

        Args:
            temperature (float): The temperature at which the window open behavior should be triggered in degrees Celsius.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the presets are not available or the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the temperature is invalid.
        """
        return await self.async_configure_window_open(
            temperature, self.presets.window_open_time
        )

    async def async_configure_window_open_duration(
        self,
        duration: timedelta | float,
    ) -> Status:
        """Configure the window open duration.

        The duration is specified in 5 minute increments.
        The initial value is 15 minutes.
        If a float is provided, it will be converted to a timedelta with minutes as the unit.

        Args:
            duration (timedelta | float): The duration for which the window open behavior should be active.

        Returns:
            Status: The updated status.

        Raises:
            Eq3StateException: If the presets are not available or the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
            Eq3InvalidDataException: If the duration is invalid.
        """
        return await self.async_configure_window_open(
            self.presets.window_open_temperature, duration
        )

    async def __aenter__(self) -> Self:
        """Async context manager enter.

        Connects to the thermostat. After connecting, the device data, status, and schedule will be queried and stored.
        When the connection is established, the CONNECTED event will be triggered.

        Raises:
            Eq3StateException: If the thermostat is already connected.
            Eq3ConnectionException: If the connection fails.
            Eq3TimeoutException: If the connection times out.
            Eq3CommandException: If an error occurs while sending a command.
        """
        await self.async_connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Async context manager exit.

        Disconnects from the thermostat. Before disconnection all pending futures will be cancelled.
        When the disconnection is complete, the DISCONNECTED event will be triggered.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3ConnectionException: If the disconnection fails.
            Eq3TimeoutException: If the disconnection times out.
        """
        await self.async_disconnect()

    async def _async_write_command_with_device_data_response(
        self, command: _Eq3Struct
    ) -> DeviceData:
        """Write a command to the thermostat and wait for a device data response.

        Args:
            command (_Eq3Struct): The command to write.

        Returns:
            DeviceData: The device data.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3TimeoutException: If the command times out.
            Eq3CommandException: If an error occurs while sending the command.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        queued_command = _QueuedCommand(
            command=command, response_type=_ResponseType.DEVICE_DATA, future=future
        )

        self._command_queue.append(queued_command)
        await self._async_write_command(command)

        try:
            device_data = await asyncio.wait_for(future, self._command_timeout)
        except TimeoutError as ex:
            if queued_command in self._command_queue:
                self._command_queue.remove(queued_command)
            raise Eq3TimeoutException("Timeout during device data command") from ex

        return device_data

    async def _async_write_command_with_status_response(
        self, command: _Eq3Struct
    ) -> Status:
        """Write a command to the thermostat and wait for a status response.

        Args:
            command (_Eq3Struct): The command to write.

        Returns:
            Status: The status.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3TimeoutException: If the command times out.
            Eq3CommandException: If an error occurs while sending the command.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        queued_command = _QueuedCommand(
            command=command, response_type=_ResponseType.STATUS, future=future
        )

        self._command_queue.append(queued_command)
        await self._async_write_command(command)

        try:
            status = await asyncio.wait_for(future, self._command_timeout)
        except TimeoutError as ex:
            if queued_command in self._command_queue:
                self._command_queue.remove(queued_command)
            raise Eq3TimeoutException("Timeout during status command") from ex

        return status

    async def _async_write_commands_with_schedule_response(
        self, commands: list[_Eq3Struct]
    ) -> Schedule:
        """Write commands to the thermostat and wait for a schedule response.

        Args:
            commands (list[_Eq3Struct]): The commands to write.

        Returns:
            Schedule: The schedule.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3TimeoutException: If the command times out.
            Eq3CommandException: If an error occurs while sending the command.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        queued_command = _QueuedCommand(
            command=commands[0],
            response_type=_ResponseType.SCHEDULE,
            future=future,
            schedule_count=len(commands),
        )

        self._command_queue.append(queued_command)

        for command in commands:
            await self._async_write_command(command)

        try:
            schedule = await asyncio.wait_for(future, self._command_timeout)
        except TimeoutError as ex:
            if queued_command in self._command_queue:
                self._command_queue.remove(queued_command)
            raise Eq3TimeoutException("Timeout during schedule command") from ex

        return schedule

    async def _async_write_command(self, command: _Eq3Struct) -> None:
        """Write a command to the thermostat.

        Args:
            command (_Eq3Struct): The command to write.

        Raises:
            Eq3StateException: If the thermostat is not connected.
            Eq3CommandException: If an error occurs while sending the command.
            Eq3TimeoutException: If the command times out.
        """
        if not self.is_connected or self._conn is None:
            raise Eq3StateException("Not connected")

        data = command.to_bytes()

        async with self._lock:
            try:
                await asyncio.wait_for(
                    self._conn.write_gatt_char(_Eq3Characteristic.WRITE, data),
                    self._command_timeout,
                )
            except BleakError as ex:
                raise Eq3CommandException("Error during write") from ex
            except TimeoutError as ex:
                raise Eq3TimeoutException("Timeout during write") from ex

    def _on_disconnected(self, _: BleakClient) -> None:
        """Handle disconnection from the thermostat."""
        asyncio.create_task(self._trigger_event(Eq3Event.DISCONNECTED))

    async def _on_message_received(
        self, _: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle received messages from the thermostat."""
        data_bytes = bytes(data)
        command = DataclassStruct(_Eq3Message).parse(data_bytes)

        match command.cmd:
            case _Eq3Command.ID_RETURN:
                device_data = DeviceData._from_bytes(data_bytes)
                return await self._on_device_data_received(device_data)
            case _Eq3Command.INFO_RETURN:
                if not command.is_status_command:
                    return

                status = Status._from_bytes(data_bytes)
                return await self._on_status_received(status)
            case _Eq3Command.SCHEDULE_RETURN:
                schedule = Schedule._from_bytes(data_bytes)
                return await self._on_schedule_received(schedule)
            case _:
                raise Eq3InternalException(f"Unknown command: {command}")

    async def _on_device_data_received(self, device_data: DeviceData) -> None:
        """Handle received device data.

        Triggers the DEVICE_DATA_RECEIVED event.

        Args:
            device_data (DeviceData): The received device data.
        """
        self._last_device_data = device_data

        for i, queued_command in enumerate(self._command_queue):
            if (
                queued_command.response_type == _ResponseType.DEVICE_DATA
                and not queued_command.future.done()
            ):
                self._command_queue.remove(queued_command)
                queued_command.future.set_result(device_data)
                break

        await self._trigger_event(
            Eq3Event.DEVICE_DATA_RECEIVED, device_data=device_data
        )

    async def _on_status_received(self, status: Status) -> None:
        """Handle received status.

        Triggers the STATUS_RECEIVED event.

        Args:
            status (Status): The received status.
        """
        self._last_status = status

        for i, queued_command in enumerate(self._command_queue):
            if (
                queued_command.response_type == _ResponseType.STATUS
                and not queued_command.future.done()
            ):
                self._command_queue.remove(queued_command)
                queued_command.future.set_result(status)
                break

        await self._trigger_event(Eq3Event.STATUS_RECEIVED, status=status)

    async def _on_schedule_received(self, schedule: Schedule) -> None:
        """Handle received schedule.

        Merges the received schedule with the last known schedule and triggers the SCHEDULE_RECEIVED event.

        Args:
            schedule (Schedule): The received schedule.
        """
        if self._last_schedule is None:
            self._last_schedule = schedule

        self._last_schedule.merge(schedule)

        for i, queued_command in enumerate(self._command_queue):
            if (
                queued_command.response_type == _ResponseType.SCHEDULE
                and not queued_command.future.done()
            ):
                queued_command.schedule_count -= 1

                if queued_command.schedule_count == 0:
                    self._command_queue.remove(queued_command)
                    queued_command.future.set_result(self._last_schedule)
                break

        await self._trigger_event(
            Eq3Event.SCHEDULE_RECEIVED, schedule=self._last_schedule
        )

    @overload
    def register_callback(
        self,
        event: Literal[Eq3Event.DISCONNECTED],
        callback: Union[Callable[[], None], Callable[[], Awaitable[None]]],
    ) -> None: ...

    @overload
    def register_callback(
        self,
        event: Literal[Eq3Event.CONNECTED],
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

    @overload
    def unregister_callback(
        self,
        event: Literal[Eq3Event.DISCONNECTED],
        callback: Union[Callable[[], None], Callable[[], Awaitable[None]]],
    ) -> None: ...

    @overload
    def unregister_callback(
        self,
        event: Literal[Eq3Event.CONNECTED],
        callback: Union[
            Callable[[DeviceData, Status, Schedule], None],
            Callable[[DeviceData, Status, Schedule], Awaitable[None]],
        ],
    ) -> None: ...

    @overload
    def unregister_callback(
        self,
        event: Literal[Eq3Event.DEVICE_DATA_RECEIVED],
        callback: Union[
            Callable[[DeviceData], None], Callable[[DeviceData], Awaitable[None]]
        ],
    ) -> None: ...

    @overload
    def unregister_callback(
        self,
        event: Literal[Eq3Event.STATUS_RECEIVED],
        callback: Union[Callable[[Status], None], Callable[[Status], Awaitable[None]]],
    ) -> None: ...

    @overload
    def unregister_callback(
        self,
        event: Literal[Eq3Event.SCHEDULE_RECEIVED],
        callback: Union[
            Callable[[Schedule], None], Callable[[Schedule], Awaitable[None]]
        ],
    ) -> None: ...

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
    async def _trigger_event(self, event: Literal[Eq3Event.DISCONNECTED]) -> None: ...

    @overload
    async def _trigger_event(
        self,
        event: Literal[Eq3Event.CONNECTED],
        *,
        device_data: DeviceData,
        status: Status,
        schedule: Schedule,
    ) -> None: ...

    @overload
    async def _trigger_event(
        self,
        event: Literal[Eq3Event.DEVICE_DATA_RECEIVED],
        *,
        device_data: DeviceData,
    ) -> None: ...

    @overload
    async def _trigger_event(
        self,
        event: Literal[Eq3Event.STATUS_RECEIVED],
        *,
        status: Status,
    ) -> None: ...

    @overload
    async def _trigger_event(
        self,
        event: Literal[Eq3Event.SCHEDULE_RECEIVED],
        *,
        schedule: Schedule,
    ) -> None: ...

    async def _trigger_event(
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
            case _:
                if schedule is None:
                    raise Eq3InternalException(
                        "schedule must not be None for SCHEDULE_RECEIVED event"
                    )
                args = (schedule,)

        if async_callbacks:
            await asyncio.gather(*[callback(*args) for callback in async_callbacks])

        for callback in sync_callbacks:
            callback(*args)
