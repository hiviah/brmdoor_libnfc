#!/usr/bin/env python
from brmdoor_nfc import NFCDevice
from binascii import hexlify

nfc = NFCDevice()
print hexlify(nfc.scanUID())
