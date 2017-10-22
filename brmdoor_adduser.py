#!/usr/bin/env python

"""
Adds user into database of authorized users.
"""

import sys
import sqlite3

from optparse import OptionParser

from brmdoor_nfc_daemon import BrmdoorConfig

def addUidAuth(cursor, uid_hex, nick):
    """
    Add user authenticated by UID. UID should be in hex, 4, 7 or 10 bytes long.
    """
    try:
        uid_hex.decode("hex")
        sql = """INSERT INTO authorized_uids
            (uid_hex, nick)
            values (?, ?)
        """
        sql_data = (uid_hex, nick)
        cursor.execute(sql, sql_data)
    except TypeError:
        print >> sys.stderr, "UID must be in proper hex encoding"
        sys.exit(1)
        
def addHmacAuth(cursor, uid_hex, nick, key_hex):
    """
    Add user authenticated by Yubikey HMAC-SHA1. UID should be in hex, 4, 7
    or 10 bytes long. HMAC key in key_hex must be exactly 20 bytes in hex.
    """
    try:
        uid_hex.decode("hex")
        if len(key_hex.decode("hex")) != 20:
            print >> sys.stderr, "Key must be exactly 20 bytes long!"
            sys.exit(1)
        sql = """INSERT INTO authorized_hmac_keys
            (uid_hex, nick, key_hex)
            VALUES (?, ?, ?)
        """
        sql_data = (uid_hex, nick, key_hex)
        cursor.execute(sql, sql_data)
    except TypeError:
        print >> sys.stderr, "UID and key must be in proper hex encoding"
        sys.exit(1)

def addNdefAuth(cursor, uid_hex, nick):
    """
    Add user authenticated by NDEF message on Desfire. UID should be in hex, 4, 7 or 10 bytes long.
    """
    try:
        uid_hex.decode("hex")
        sql = """INSERT INTO authorized_desfires
            (uid_hex, nick)
            values (?, ?)
        """
        sql_data = (uid_hex, nick)
        cursor.execute(sql, sql_data)
    except TypeError:
        print >> sys.stderr, "UID must be in proper hex encoding"
        sys.exit(1)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-c", "--config", action="store", type="string", dest="config",
        help="Configuration file")
    parser.add_option("-a", "--authtype", action="store", type="string", dest="authtype",
        help="Authenthication type - uid, hmac or ndef")
    (opts, args) = parser.parse_args()

    if opts.config is None:
        print >> sys.stderr, "You must specify config file via the -c option!"
        parser.print_help()
        sys.exit(1)
        
    if opts.authtype not in ["uid", "hmac", "ndef"]:
        print >> sys.stderr, "You must specify authentication type via -a option!"
        print >> sys.stderr, "Acceptable choices: uid, hmac, ndef"
        sys.exit(1)
        
    config = BrmdoorConfig(opts.config)
    conn = sqlite3.connect(config.authDbFilename)
    cursor = conn.cursor()
    
    if opts.authtype == "uid":
        if len(args) < 2:
            print >> sys.stderr, "You must two additional arguments, hex UID and nick"
            print >> sys.stderr, "Example:"
            print >> sys.stderr, "brmdoor_adduser.py -c brmdoor.config -a uid 34795FCC SomeUserName"
            sys.exit(1)
        addUidAuth(cursor, args[0], args[1])
    elif opts.authtype == "hmac":
        if len(args) < 3:
            print >> sys.stderr, "You must three additional arguments, hex UID and nick and hex key"
            print >> sys.stderr, "brmdoor_adduser.py -c brmdoor.config -a hmac 40795FCCAB0701 SomeUserName 000102030405060708090a0b0c0d0e0f31323334"
            sys.exit(1)
        addHmacAuth(cursor, args[0], args[1], args[2])
    elif opts.authtype == "ndef":
        if len(args) < 2:
            print >> sys.stderr, "You must two additional arguments, hex UID and nick"
            print >> sys.stderr, "Example:"
            print >> sys.stderr, "brmdoor_adduser.py -c brmdoor.config -a ndef 34795FCC SomeUserName"
            sys.exit(1)
    addNdefAuth(cursor, args[0], args[1])

    conn.commit()
    conn.close()
