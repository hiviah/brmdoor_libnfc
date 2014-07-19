#!/usr/bin/env python
from brmdoor_nfc import NFCDevice, NFCError
from binascii import hexlify

try:
	nfc = NFCDevice()
	print hexlify(nfc.scanUID())
	print "Device is opened:", nfc.opened()
	print "Closing device"
	nfc.close()
	print "Device is opened:", nfc.opened()
	nfc.unload()
except NFCError, e:
	print "Reading UID failed:", e.what()
