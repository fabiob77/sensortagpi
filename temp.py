#!/usr/bin/env python

from bluepy import btle
from time import sleep

sensor = btle.Peripheral('B4:99:4C:34:D5:9E')

sensor.writeCharacteristic(0x25, '\x01', withResponse=True)

sleep(1) # warm up

for i in range(10):
    t_data = sensor.readCharacteristic(0x21)
    msb = ord(t_data[3])
    lsb = ord(t_data[2])
    c = ((msb * 256 + lsb) / 4) * 0.03125
    f = c * 9/5.0 + 32
    print '%s degrees fahrenheit' % round(f, 2)
    sleep(2)

sensor.writeCharacteristic(0x24, '\x25', withResponse=True)
