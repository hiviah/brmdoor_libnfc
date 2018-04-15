#!/usr/bin/env python2

import sys
import os
import os.path
import sqlite3

from brmdoor_adduser import addUidAuth
from create_authenticator_db import createTables

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "import_jendasap_cards.py <cards_from_sap.txt> <destination.sqlite>"
        print "This will generate and COMPLETELY OVERWRITE the UID table in destination.sqlite"
        print "This is useful for initial import, but for individual cards use brmdoor_adduser.py"
        sys.exit(1)

    destSqliteFname = sys.argv[2]
    srcCardsFname = sys.argv[1]
    nickUidList = []
    with file(srcCardsFname) as f:
        lineNo = 0
        for line in f:
            lineNo += 1
            line = line.rstrip()
            if line == "":
                continue
            parts = line.rstrip().split(" ")
            if len(parts) != 2:
                print "Skipping line %d, expected two parts - nick, uid, got: %s" % (lineNo, repr(parts))
                continue
            nickUidList.append(parts)

    dbExists =  os.path.isfile(destSqliteFname)
    conn = sqlite3.connect(destSqliteFname)
    cursor = conn.cursor()
    if dbExists:
        cursor.execute("DELETE FROM authorized_uids")
    else:
        createTables(cursor)

    for (nick, uid) in nickUidList:
        addUidAuth(cursor, uid, nick)

    conn.commit()
    conn.close()
    print "Converted %d nick-uid pairs into authorized_uids table" % (len(nickUidList),)

