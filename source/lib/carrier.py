#!/bin/sh
'''which' python3 > /dev/null && exec python3 "$0" "$@" || exec python "$0" "$@"
'''

#
# Copyright (c) 2019, Manfred Constapel
# This file is licensed under the terms of the MIT license.
#

#
# soft-reset of a TI mmWave EVM with TI's DCA1000EVM or mmWaveICBoost via FTDI
#

import sys
import time
import usb
import serial

from lib.ports import *

from lib.utility import *
from lib.shell import *

# ------------------------------------------------

try:
    
    from pyftdi import gpio
    from pyftdi import ftdi
    from pyftdi import spi
    from pyftdi import serialext
    from pyftdi import usbtools
    
    FTDI_USB = (0x0451, 0xfd03)

    ftdi.Ftdi.add_custom_vendor(FTDI_USB[0])
    ftdi.Ftdi.add_custom_product(*FTDI_USB)

    url = 'ftdi://{:#x}:{:#x}/{}'
    
except ImportError as e:
    print_log(e, sys._getframe())

# ------------------------------------------------

def ftdi_reset(vid, pid, delay=100):
    try:

        ftdi3 = gpio.GpioController()
        mask3 = 0b11110000  # hi=output, lo=input (GPIO on D4 to D7)
        ftdi3.configure(url=url.format(vid, pid, 3), direction=mask3)
            
        ftdi3.write(int('35', 16)) 
        time.sleep(delay / 1000 / 2)
        
        ftdi3.write(int('35', 16))   # CDBUS6 (pin 45) -> RESET MCU low
        time.sleep(delay / 1000 / 2)
        
        ftdi3.write(int('75', 16))  # CDBUS6 (pin 45) -> RESET MCU high    
        return True
    except:
        pass
    return False
