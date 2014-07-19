#!/usr/bin/env python
from brmdoor_nfc import NFCDevice
from binascii import hexlify

nfc = NFCDevice()
nfc.close()
nfc.open()
print hexlify(nfc.scanUID())
print "Device is opened:", nfc.opened()
print "Closing device"
nfc.close()
print "Device is opened:", nfc.opened()
