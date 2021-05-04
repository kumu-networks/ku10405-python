# ku10405-python

## Abstract

ku10405-python is a Python driver to control the KU10405 evaluation board.

## Dependencies / Installation

To use this driver, you'll need the following:
* python3 (tested with 3.6, but any 3.x should work)
* pyftdi
* libusb  (required by pyftdi)

[Pyftdi's documentation](https://eblot.github.io/pyftdi/installation.html) provides comprehensive
instructions for how to install pyftdi and libusb on any operating system.

## Usage

The following is a basic example of how to use the driver.

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
