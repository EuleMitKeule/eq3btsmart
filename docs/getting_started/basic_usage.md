
# Basic Usage

Here are some examples of how to use the library to interact with your thermostat.

## Connection Process and Basic Control

In this example, we connect to the thermostat, read the current temperature, set a new temperature and disconnect.
The full list of available commands can be found in the [Thermostat reference](../reference/thermostat.md).

```py
import asyncio
from eq3btsmart import Thermostat

thermostat = Thermostat("00:1A:22:12:34:56") # Replace with your thermostat's MAC address

async def main():
    await thermostat.async_connect()

    print(f"Current temperature: {thermostat.status.target_temperature} °C")
    await thermostat.async_set_temperature(20.5)

    await thermostat.async_disconnect()
```

You can also use the asynchronous context manager syntax to automatically connect and disconnect.

```py
import asyncio
from eq3btsmart import Thermostat

async def main():
    async with Thermostat("00:1A:22:12:34:56") as thermostat:
        print(f"Current temperature: {thermostat.status.target_temperature} °C")
        await thermostat.async_set_temperature(20.5)
```

## Fetching State

You can also fetch the current state of the thermostat.

```py
import asyncio
from eq3btsmart import Thermostat

async def main():
    async with Thermostat("00:1A:22:12:34:56") as thermostat:
        device_data = await thermostat.async_get_device_data()
        status = await thermostat.async_get_status()
        schedule = await thermostat.async_get_schedule()

        print(f"Device data: {device_data}")
        print(f"Status: {status}")
        print(f"Schedule: {schedule}")
```
