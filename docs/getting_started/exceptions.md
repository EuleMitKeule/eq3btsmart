
# Exceptions

The `eq3btsmart` library provides a few exceptions that you can catch to handle errors.
If you want to catch all exceptions, you can catch the base exception `Eq3Exception`.

## Exception Types

The following exceptions are available:

Exception | Description
--- | ---
`Eq3Exception` | Base exception for all exceptions in the library.
`Eq3ConnectionException` | Exception that is raised when a connection error occurs.
`Eq3CommandException` | Exception that is raised when a command fails.
`Eq3TimeoutException` | Exception that is raised when a timeout occurs.
`Eq3AlreadyAwaitingResponseException` | Exception that is raised when a command that was sent previously is still awaiting a response.
`Eq3InvalidDataException` | Exception that is raised when parsing the provided data fails.
`Eq3InvalidStateException` | Exception that is raised when an action is not allowed in the current state.
`Eq3InternalException` | Exception that is raised when an internal error occurs.

## Example

In this example, we connect to the thermostat and catch the `Eq3ConnectionException` and `Eq3TimeoutException` exceptions.

```py
import asyncio
from eq3btsmart import Thermostat, Eq3ConnectionException, Eq3TimeoutException

thermostat = Thermostat("00:1A:22:12:34:56") # Replace with your thermostat's MAC address

async def main():
    try:
        await thermostat.async_connect()
    except Eq3ConnectionException as e:
        print(f"Connection error: {e}")
    except Eq3TimeoutException as e:
        print(f"Timeout error: {e}")
    finally:
        await thermostat.async_disconnect()
```
