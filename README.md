# KU10405 API

This repo provides a simple interface for using the KU10405 chip. It has been tested successfully on
Ubuntu, Windows 10, and macOS Mojave.


## Dependencies/Installation

To use thie API, you'll need the following:
* python3
* pyftdi
* libusb

[Pyftdi's documentation](https://eblot.github.io/pyftdi/installation.html) provides comprehensive
instructions for how to install libusb and pyftdi on any operating system. Follow the instructions
for installing libusb, and then run `pip3 install pyftdi`.

If you're using Windows, pay special attention to the instructions! Be sure to download the latest
version (1.2.6.0 at the time of writing), and choose the `libusb-win32-devel-filter-1.2.6.0.exe`
installer. After installation the installer will prompt you about whether you want to install a
filter. Make sure your FTDI cable is plugged in, and then choose it as a filter. If you skip this
step you'll get an error from pyftdi saying that it can't find the device.

## Usage

The following is a basic example of how to use the API.

```python
from ku10405 import KU10405

dut = KU10405()  # create the object to control the chip
dut.set_tap(0, 100, 200)  # set channel 0's magnitude to 100 and phase to 200
dut.set_tap(1, 300, 400)  # set channel 1's magnitude to 300 and phase to 400
dut.set_tap(2, 0, 0, enable=False)  # disable channel 2
dut.set_tap(3, 0, 0, enable=False)  # disable channel 3
```

For details on more advanced usage (disable readback, delay application of settings, etc.), see the
documentation in the code.
