#!/usr/bin/env python
import sys

from nfc_smartcard import NFCDevice, NFCError
from binascii import hexlify

def formatAPDU(apdu):
    return " ".join(["%02X" % ord(b) for b in apdu])
    
tests = {
    # Reading of file E104, where usually NDEF message is
    "ndef4": [
            "00 A4 04 00 07 D2760000850101",
            "00 a4 00 0c 02 E104",
            "00 b0 00 00 30",
    ],

    # Yubikey Neo command for HMAC-SHA1 of string 'Sample #2'
    "yubikey": [
            "00 A4 04 00 07 A0 00 00 05 27 20 01",
            "00 01 38 00 09 53 61 6D 70 6C 65 20 23 32"
    ],

    # Mastercard payment via 2PAY.SYS.DDF01 smartcard application
    "mastercard": [
        "00 a4 04 00 0e 32 50 41 59 2e 53 59 53 2e 44 44 46 30 31 00", #select 2PAY.SYS.DDF01
        "00 a4 04 00 07 a0 00 00 00 04 10 10 00", # select Mastercard app a0 00 00 00 04 10 10
        "80 a8 00 00 02 83 00 00", # get processing options
        "00 b2 01 14 00", # read record 01 14 (contains CDOL1)
        "00 b2 01 1c 00", # read record 01 1c (contains issuer's public key and certificate)
        "00 b2 01 24 00", # read record 01 24 (contains ICC public key)
        "00 b2 02 24 00", # read record 02 24 (contains ICC certificate)
        # generate application cryptogram - sign the payment for 50 CZK (data formatted according to CDOL1)
        "80 ae 50 00 2b 00 00 00 00 50 00 00 00 00 00 00 00 02 03 00 00 00 00 00 02 03 14 03 14 00 cb 6d 9a 2c 22 00 00 00 00 00 00 00 00 00 00 1f 03 00 00"
    ],

    # Visa read track 2 equivalent data - contains card number, cardholder name, etc
    "visa": [
        "00 A4 04 00 07 A0 00 00 00 03 10 10 00", # select VISA app A0 00 00 00 03 10 10
        "00 B2 02 0C 00"                          # select record 02 0c - Track 2 Equivalent Data
    ],
}

# default test if not selected otherwise in sys.argv[1]
apdu_test = "desfire-ndef4"

if len(sys.argv) > 1:
    apdu_test = sys.argv[1]

print "Available tests: %s" % ", ".join(sorted(tests.keys() + "desfire-ndef4")) #desfire-ndef4 has a bit postprocessing
print "Selected test: %s" % apdu_test

# select apdus according to test name
if apdu_test in tests:
    hex_apdus = tests[apdu_test]
    apdus = [hex_apdu.replace(" ","").decode("hex") for hex_apdu in hex_apdus]

    try:
        nfc = NFCDevice()
        uid = nfc.scanUID()
        print "UID", hexlify(uid)
        #nfc.close()
        #nfc.open()

        print "Now trying to send ISO14443-4 APDUs"
        try:
            #nfc.selectPassiveTarget()
            for apdu in apdus:
                print "Command APDU:", formatAPDU(apdu)
                rapdu = nfc.sendAPDU(apdu)
                print "Response APDU valid: %s, SW %04x, data %s" % (rapdu.valid(), rapdu.sw(), hexlify(rapdu.data()))
        except NFCError, e:
            print "Failed to transmit APDU:", e.what()

        print "Device is opened:", nfc.opened()
        print "Closing device"
        nfc.close()
        print "Device is opened:", nfc.opened()
        nfc.unload()
    except NFCError, e:
        print "Reading UID failed:", e.what()
elif apdu_test == "desfire-ndef4":
    try:
        nfc = NFCDevice()
        uid = nfc.scanUID()
        print "UID", hexlify(uid)
        #nfc.close()
        #nfc.open()

        ndef = nfc.readDesfireNDEF()
        print ndef
        print "Device is opened:", nfc.opened()
        print "Closing device"
        nfc.close()
        print "Device is opened:", nfc.opened()
        nfc.unload()
    except NFCError, e:
        print "Reading UID failed:", e.what()
