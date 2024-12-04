# Registering Callbacks

The thermostat provides a few callbacks that you can register to get notified about messages from the thermostat or changes in the connection state.
Callbacks can either be synchronous or asynchronous.

> **Note:** The latest `DeviceData`, `Status`, and `Schedule` can also be queried and are returned by the `async_get_status()`, `async_get_device_data()`, and `async_get_schedule()` methods.

## Events

The following events are available:

Event | Description | Arguments
--- | --- | ---
`Eq3Event.CONNECTED` | The thermostat is connected. | `DeviceData`, `Status`, `Schedule`
`Eq3Event.DISCONNECTED` | The thermostat is disconnected. | None
`Eq3Event.DEVICE_DATA_RECEIVED` | Device data was received. | `DeviceData`
`Eq3Event.STATUS_RECEIVED` | Status data was received. | `Status`
`Eq3Event.SCHEDULE_RECEIVED` | Schedule data was received. | `Schedule`

## Example

In this example, we connect to the thermostat and register a callback for the `Eq3Event.STATUS_RECEIVED` event.

```py
import asyncio
from eq3btsmart import Thermostat, Eq3Event, Status

thermostat = Thermostat("00:1A:22:12:34:56") # Replace with your thermostat's MAC address

def status_received_callback(status: Status):
    print(f"Received status: {status}")

async def main():
    await thermostat.async_connect()

    thermostat.register_callback(Eq3Event.STATUS_RECEIVED, status_received_callback)

    await thermostat.async_get_status() # Request the current status
    await asyncio.sleep(10) # Wait for 10 seconds

    await thermostat.async_disconnect()
```
