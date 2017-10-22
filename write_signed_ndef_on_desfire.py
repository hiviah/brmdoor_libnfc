#!/usr/bin/env python

import sys
import os
import tempfile

from binascii import hexlify

from nfc_smartcard import NFCDevice, NFCError
from sign_uid import signUid

if len(sys.argv) < 2:
    print "Usage: write_signed_ndef_on_desfire.py private_key_in_hex"
    sys.exit(3)

tempFd = None
tempFname = None

try:
    print "Opening NFC reader"
    nfc = NFCDevice()
    nfc.pollNr = 0xFF #poll indefinitely
    print "Waiting for Desfire card to appear in the reader"
    uid_hex = hexlify(nfc.scanUID())
    key = sys.argv[1].decode("hex")

    print "Got UID %s" % uid_hex
    signature = signUid(key, uid_hex.decode("hex"))
    (tempFd, tempFname) = tempfile.mkstemp(dir="/tmp")
    os.write(tempFd, signature)
    os.close(tempFd)
    print "Wrote signature into %s" % tempFname
except NFCError, e:
    #this exception happens also when scanUID times out
    print("Failed to wait for Desfire card: %s" % e)
    if tempFname:
        os.unlink(tempFname)
    sys.exit(1)
except Exception, e:
    print("Something went wrong when writing the signature to file:", e)
    if tempFname:
        os.unlink(tempFname)
    sys.exit(2)
finally:
    nfc.close()
    nfc.unload()

# We'll just call the command line tools so that we don't need to copy&paste the NDEF writing code to nfc_smartcard.cpp
print "Formatting card"
res = os.system("mifare-desfire-format -y")
if res != 0:
    print "Formatting failed"
    sys.exit(4)
print "Creating NDEF file/application"
res = os.system("mifare-desfire-create-ndef -y")
if res != 0:
    print "Creating NDEF failed"
    sys.exit(4)
print "Writing NDEF with signature onto Desfire"
res = os.system("mifare-desfire-write-ndef -y -i %s" % tempFname)
if res != 0:
    print "Writing NDEF failed"
    sys.exit(4)

print "All done"
