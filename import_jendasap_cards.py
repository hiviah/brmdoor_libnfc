#!/usr/bin/env python2

import sys
import os
import os.path
import sqlite3

from brmdoor_adduser import addUidAuth, addNdefAuth
from create_authenticator_db import createTables

from optparse import OptionParser

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-d", "--desfire", dest="use_desfire",
                      help="import Desfire table", action="store_true", default=False)

    (options, args) = parser.parse_args()

    if len(args) < 2:
        print "import_jendasap_cards.py [--desfire] <cards_from_sap.txt> <destination.sqlite>"
        print "This will generate and COMPLETELY OVERWRITE the UID/Desfire table in destination.sqlite"
        print "This is useful for initial import, but for individual cards use brmdoor_adduser.py"
        sys.exit(1)

    if options.use_desfire:
        destTable = "authorized_desfires"
        importFunc = addNdefAuth
    else:
        destTable = "authorized_uids"
        importFunc = addUidAuth

    destSqliteFname = args[1]
    srcCardsFname = args[0]
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
        cursor.execute("DELETE FROM %s" % destTable)
    else:
        createTables(cursor)

    for (nick, uid) in nickUidList:
        importFunc(cursor, uid, nick)

    conn.commit()
    conn.close()
    print "Converted %d nick-uid pairs into %s table" % (len(nickUidList), destTable)

