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

import usb
import serial
import time
import sys

from pyftdi import gpio
from pyftdi import ftdi
from pyftdi import spi
from pyftdi import serialext
from pyftdi import usbtools

# ------------------------------------------------

VID, PID = 0x0451, 0xfd03

ftdi.Ftdi.add_custom_vendor(VID)
ftdi.Ftdi.add_custom_product(VID, PID)

url = 'ftdi://{:#x}:{:#x}/{}'

# ------------------------------------------------

if __name__ == "__main__":

    found = False
    
    all_devices = usb.core.find(find_all=True)
    tags = ('DEVICE ID', )
    #tags = ('DEVICE ID', 'CONFIGURATION', 'INTERFACE', 'ENDPOINT')
    for dev in all_devices:
        if '{:04x}:{:04x}'.format(VID, PID) in str(dev):
            for line in str(dev).split('\n'):
                if any(tag in line for tag in tags):
                    print(line.replace('=', ''), file=sys.stderr)
                    found = True
        
    if found:
    
        try:
            
            print('FTDI:C,GPIO -- FullReset()', file=sys.stderr)
               
            ftdi3 = gpio.GpioController()
            mask3 = 0b11110000  # hi=output, lo=input (GPIO on D4 to D7)
            ftdi3.configure(url=url.format(VID, PID, 3), direction=mask3)
                
            ftdi3.write(int('35', 16)) 
            time.sleep(0.25)
            
            ftdi3.write(int('35', 16))   # CDBUS6 (pin 45) -> RESET MCU low
            time.sleep(0.25)
            
            ftdi3.write(int('75', 16))  # CDBUS6 (pin 45) -> RESET MCU high    
            time.sleep(0.25)
            
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)
    
    else:
        print('FTDI chip has not been found.', file=sys.stderr)
        sys.exit(1)
