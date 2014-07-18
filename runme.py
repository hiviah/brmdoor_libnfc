#!/usr/bin/env python
from brmdoor_nfc import NFCDevice

nfc = NFCDevice()
print nfc.scanUID()
