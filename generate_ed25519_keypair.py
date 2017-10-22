#!/usr/bin/env python2

"""
Used to generate keypair for signing NDEF messages for Mifare NDEF authentication
"""

import os
import axolotl_curve25519 as curve

from binascii import hexlify

random32 = os.urandom(32)

private_key = curve.generatePrivateKey(random32)
public_key = curve.generatePublicKey(private_key)

print "private key in hex:", hexlify(private_key)
print "public key in hex :", hexlify(public_key)

