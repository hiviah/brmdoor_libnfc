# Brmdoor via libnfc

This is an access-control system implementation via contactless ISO 14443A cards
and a PN53x-based reader. So you basically swipe your card, and if it's in
database, the door unlocks.

Info about authorized users and their cards and keys is stored in sqlite database.

This was originally designed for Raspberry (Raspbian), but it also runs on
desktop PC if you have the PN532 USB reader.

The daemon is implemented in `brmdoor_nfc_daemon.py`.

## NFC smartcard API

This project shows how to use libnfc from python to send APDUs to NFC
smartcards. Have a look at `test_nfc.py` for some examples, currently it
shows four interactions with NFC smartcards:

* read NDEF message from token (Mifare Desfire, Yubikey Neo)
* do HMAC-SHA1 authenthication (Yubikey Neo)
* read Track 2 Equivalent Data from Visa
* execute signature for payment on Mastercard

It is much more general in use than to use it as authenthicator to open door.

## Building

You need just to run `make`. Additional dependencies:

- [libnfc](https://github.com/nfc-tools/libnfc/releases), already present in Raspbian 8 repositories
- [SWIG](http://www.swig.org/)
- [WiringPi2 pythonic binding](https://github.com/WiringPi/WiringPi2-Python) (for switching lock on Raspberry)

## Howto

1. Create the database

        python create_authenticator_db.py authenthicator_db.sqlite

2. Copy sample config file, edit your pins, DB file location, timeouts

        cp brmdoor_nfc.config.sample brmdoor_nfc.config

3. Add some users

  - either authenthication by UID, e.g.:

        brmdoor_adduser.py -c brmdoor_nfc.config -a uid 34795FCC SomeUserName

  - authenthication by Yubikey's HMAC-SHA1 programmed on slot 2

        brmdoor_adduser.py -c brmdoor_nfc.config -a hmac 40795FCCAB0701 SomeUserName 000102030405060708090a0b0c0d0e0f31323334

  - to program Yubikey slot 2 to use HMAC with given key, use:

        ykpersonalize -2 -ochal-resp -ohmac-sha1 -ohmac-lt64 -oserial-api-visible

Finally, run the daemon:

        sudo python brmdoor_nfc_daemon.py brmdoor_nfc.config

## Configuring libnfc devices

If you have PN532 device on other bus than USB (e.g. SPI), first search for it using:

    sudo nfc-scan-device -i

After that, create file `/etc/nfc/libnfc.conf` with line describing your device
from `nfc-scan-device` above, e.g. for SPI device:

    device.connstring = "pn532_spi:/dev/spidev0.0"

This daemon expects the library to be already configured to find the PN532 device.

If you installed libnfc from source, the default directory might be
`/usr/local/etc/nfc` instead of `/etc/nfc`.
