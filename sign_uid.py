#!/usr/bin/env python2

import sys
import os
import axolotl_curve25519 as curve

def signUid(private_key, uid):
    """
    Create an Ed25519 signature for UID
    :param private_key: Binary representation of Ed25519 key
    :param uid: UID, decoded to binary from hex
    :return: singature in binary format
    """
    random64 = os.urandom(64)
    signature = curve.calculateSignature(random64, private_key, uid)
    return signature

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print >> sys.stderr, "Usage: sign_uid.py uid_hex ed25519_private_key_hex"
        print >> sys.stderr, "Outputs binary signature, you will probably want to redirect it to a file"
        sys.exit(1)

    private_key = sys.argv[3].decode("hex")
    uid_bin = sys.argv[1].decode("hex")
    sys.stdout.write(signUid(private_key, uid_bin))
