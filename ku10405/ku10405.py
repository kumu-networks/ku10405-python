"""Copyright (C) Kumu Networks, Inc. All rights reserved.

THIS SOFTWARE IS PROVIDED UNDER A SOFTWARE LICENSE AGREEMENT BY KUMU NETWORKS. BY DOWNLOADING THE
SOFTWARE AND/OR CLICKING THE APPLICABLE BUTTON TO COMPLETE THE INSTALLATION PROCESS, YOU AGREE TO BE
BOUND BY THE TERMS OF THIS AGREEMENT. IF YOU DO NOT WISH TO BECOME A PARTY TO THIS AGREEMENT AND BE
BOUND BY ITS TERMS AND CONDITIONS, DO NOT INSTALL OR USE THE SOFTWARE, AND RETURN THE SOFTWARE
WITHIN THIRTY (30) DAYS OF RECEIPT. ALL RETURNS TO KUMU WILL BE SUBJECT TO KUMU's THEN-CURRENT
RETURN POLICY. IF YOU ARE ACCEPTING THESE TERMS ON BEHALF OF AN ENTITY, YOU AGREE THAT YOU HAVE
AUTHORITY TO BIND THE ENTITY TO THESE TERMS.

THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

from pyftdi.spi import SpiController


class KU10405:
    """This class controls the KU10405 chip via an FT232H SPI controller. Users should only concern
    themselves with the constructor and set_tap method.

    Example usage:
        from ku10405 import KU10405
        dut = KU10405()
        dut.set_tap(0, 100, 200)
    """

    # The apply pin both applies changes and indicates trim bits being set. When CS is high, a
    # rising edge of the apply pin indicates that settings should be applied. Trim bits are
    # programmed when the apply pin is high while CS is low during the rising edge of the first
    # clock cycle.
    APPLY_PIN = 7

    def __init__(self, readback=True, ftdi_url='ftdi://ftdi:232h/1'):
        """An FT232H chip must be connected to your computer for this constructor to succeed. It
        sets up the SPI/GPIO interface and configures readback.

        When readback is enabled, set_tap will throw an error if the readback of any write does not
        match what was programmed. Readback does have an impact on performance because it requires
        an extra SPI transaction for every call to set_tap, but for safety it should not be disabled
        unless speed is your top priority. Note that for readback to work, the appropriate switch on
        the board must be set.

        Args:
            readback (bool, optional): Set to False to disable readback error checking
        """
        self._readback = readback

        # Setup SPI interface
        self._spi_controller = SpiController()
        self._spi_controller.configure(ftdi_url)
        self._spi = self._spi_controller.get_port(cs=0, mode=0, freq=1e6)

        # Setup GPIO interface
        self._gpio = self._spi_controller.get_gpio()
        self._gpio.set_direction(1 << self.APPLY_PIN, 1 << self.APPLY_PIN)  # make APLS an output
        self._set_apply(False)

        # We're always going to use address 0. This is here just in case that changes.
        self._addr = 0

    def set_tap(self, channel, mag, phase, enable=True, apply=True):
        """Sets the tap at the given channel to the given magnitude and phase. Magnitude and phase
        values control bits, not logical values. Disable the channel by setting enable to False.
        Changes are only applied if apply is set to True. The end result is the same if you always
        set apply to True or only set it to True on the last call of a sequence.

        Args:
            channel (int): Which channel to set (range: [0-3])
            mag (int): 14-bit attenuation (range: [0, 2^14))
            phase (int): 16-bit phase (range: [0, 2^16))
            enable (bool, optional): Set to False to disable this channel
            apply (bool, optional): Set to False if you don't want to apply these changes yet

        Raises:
            TypeError: raised if any arguments have the wrong type
            ValueError: raised if any arguments are out-of-range
        """
        if not all(isinstance(val, int) for val in (channel, mag, phase)):
            raise TypeError('Channel, magnitude, and phase must be integers')
        if not all(isinstance(val, bool) for val in (enable, apply)):
            raise TypeError('Enable and apply must be bools')
        if not 0 <= channel <= 3:
            raise ValueError('Address and channel must be in range [0, 3]')
        if not 0 <= mag <= 16383:
            raise ValueError('Magnitude must be in range [0, 16383]')
        if not 0 <= phase <= 65535:
            raise ValueError('Phase must be in range [0, 65535]')

        coarse_write, _ = \
            self._write(channel, 'coarse', mag >> 9, phase >> 11, enable)
        fine_write, coarse_read = \
            self._write(channel, 'fine', (mag >> 4) & 0x1F, (phase >> 5) & 0x3F)
        trim_write, fine_read = \
            self._write(channel, 'trim', mag & 0xF, phase & 0x1F)

        if self._readback:
            # Do a dummy write so we can get the trim readback. Note that this assumes we are not
            # using address 3!
            trim_read = self._spi.exchange((0xFFFF).to_bytes(2, byteorder='big'), duplex=True)
            trim_read = (trim_read[0] << 8) | trim_read[1]

            if coarse_write != coarse_read or fine_write != fine_read or trim_write != trim_read:
                raise IOError(
                    'Readbacks do not match! Wrote coarse {}, fine {}, trim {}, but '
                    'read coarse {}, fine {}, trim {}'.format(coarse_write, fine_write, trim_write,
                                                              coarse_read, fine_read, trim_read))

        if apply:
            self._set_apply(True)
            self._set_apply(False)

    def _write(self, channel, reg_type, mag, phase, enable=None):
        if reg_type not in ('coarse', 'fine', 'trim'):
            raise ValueError('Unrecognized register type {}'.format(reg_type))
        if reg_type == 'coarse' and enable is None:
            raise ValueError('Enable must be specified for coarse write')
        if reg_type in ('coarse', 'fine') and not 0 <= mag <= 31:
            raise ValueError('Coarse/fine magnitudes must be in range [0, 31]')
        if reg_type == 'trim' and not 0 <= mag <= 15:
            raise ValueError('Trim magnitude must be in range [0, 15]')
        if reg_type in ('coarse', 'trim') and not 0 <= phase <= 31:
            raise ValueError('Coarse/trim phases must be in range [0, 31]')
        if reg_type == 'fine' and not 0 <= phase <= 63:
            raise ValueError('Fine phase must be in range [0, 63]')

        wdata = (self._addr << 14) | (channel << 12)
        if reg_type == 'coarse':
            wdata |= (enable << 10) | (phase << 5) | mag
        elif reg_type == 'fine':
            wdata |= (1 << 11) | (phase << 5) | mag
        else:  # trim
            wdata |= (phase << 5) | mag
            self._set_apply(True)

        rdata = self._spi.exchange(wdata.to_bytes(2, byteorder='big'), duplex=True)
        rdata = (rdata[0] << 8) | rdata[1]

        if reg_type == 'trim':
            self._set_apply(False)

        return wdata, rdata

    def _set_apply(self, value):
        if not isinstance(value, bool):
            raise TypeError('GPIO value must be a bool.')
        self._gpio.write(value << self.APPLY_PIN)
