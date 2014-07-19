#!/usr/bin/env python
from brmdoor_nfc import NFCDevice, NFCError
from binascii import hexlify

try:
	nfc = NFCDevice()
	nfc.close()
	nfc.open()
	print hexlify(nfc.scanUID())
	print "Device is opened:", nfc.opened()
	print "Closing device"
	nfc.close()
	print "Device is opened:", nfc.opened()
except NFCError, e:
	print "Reading UID failed:", e.what()
