
# Pairing

Before using the library, you need to pair your bluetooth adapter with the thermostat.
On Linux, this can be done using the `bluetoothctl` command line tool.
This also allows you to get the MAC address of the thermostat.

```bash
bluetoothctl
```

Now you can scan for devices and look for names like `CC-RT-BLE`.

```bash
agent on
scan on
```

When you found your thermostat, you can pair with it.
Depending on the firmware version of your thermostat, you may need to enter a pin.

```bash
pair <MAC_ADDRESS>
trust <MAC_ADDRESS>
connect <MAC_ADDRESS>
```
