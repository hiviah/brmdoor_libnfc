#!/usr/bin/env python

"""
Creates and empty sqlite database file for brmdoor_authenticator.UidAuthenticator.

Give filename as first argument.
"""

import sys
import sqlite3

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >> sys.stderr, "You must specify filename as arg1 where the DB is to be created"
    
    filename = sys.argv[1]
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()
    
    cursor.execute("""CREATE TABLE authorized_uids(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid_hex TEXT,
        nick TEXT)
    """)
    cursor.execute("""CREATE TABLE authorized_hmac_keys(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               uid_hex TEXT,
               key_hex TEXT,
               nick TEXT)
    """)
    conn.commit()
    conn.close()
