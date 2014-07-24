# Brmdoor via libnfc

This is an access-control system implementation via contactless ISO 14443A cards
and a PN53x-based reader. So you basically swipe your card, and if it's in
database, the door unlocks.

It's primarily intended for Raspberry Pi, but can work for other plaforms that
can work with libnfc (including common x86 systems).

## Aims

People have made few implementations that kind of work
[1](https://www.brmlab.cz/project/brmdoor),
[2](https://github.com/hiviah/brmdoor-pn532/tree/pn532), but are
messy - either due to limitations of hardware or plagued by having to simulate
backward compatbility errors.

So we need and have:

  - clean, documented C++ code and swig wrapper interfacing libnfc directly
  - clean, documented Python code
  - documentation (doxygen)
  - sqlite support - no need to recompile for access control list change, just
    edit the sqlite database
  - extensibility

## Building

You need just to run `make`. Additional dependencies:

- [SWIG](http://www.swig.org/)
- [WiringPi2 pythonic binding](https://github.com/WiringPi/WiringPi2-Python) (for switching lock on Raspberry)

## Howto

1. Create the database

        python create_authenticator_db.py authenthicator_db.sqlite

2. Copy sample config file, edit your pins, DB file location, timeouts

        cp brmdoor_nfc.config.sample brmdoor.config

3. Add some users

  - either authenthication by UID, e.g.:

        brmdoor_adduser.py -c brmdoor.config -a uid 34795FCC SomeUserName

  - authenthication by Yubikey's HMAC-SHA1 programmed on slot 2

        brmdoor_adduser.py -c brmdoor.config -a hmac 40795FCCAB0701 SomeUserName 000102030405060708090a0b0c0d0e0f31323334

Finally, run the daemon:

        python brmdoor_nfc_daemon.py brmdoor.config


