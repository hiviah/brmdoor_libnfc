#!/usr/bin/env python

import sys
import logging
import time
import ConfigParser

from binascii import hexlify


from nfc_smartcard import NFCDevice, NFCError
from brmdoor_authenticator import UidAuthenticator, YubikeyHMACAuthenthicator, DesfireEd25519Authenthicator
import unlocker

class BrmdoorConfigError(ConfigParser.Error):
    """
    Signifies that config has missing or bad values.
    """
    pass

class BrmdoorConfig(object):
    """
    Configuration parser. Holds config variables from config file.
    """
    
    _defaults = {
        "lock_opened_secs": "5",
        "unknown_uid_timeout_secs": "5",
        "log_level": "info"
    }
    
    def __init__(self, filename):
        """
        Parse and read config from given filename.
        
        @throws ConfigParser.Error if parsing failed
        @throws BrmdoorConfigError if some value was missing or invalid
        """
        self.config = ConfigParser.SafeConfigParser(defaults=BrmdoorConfig._defaults)
        self.config.read(filename)
        
        self.authDbFilename = self.config.get("brmdoor", "auth_db_filename")
        self.desfirePubkey = self.config.get("brmdoor", "desfire_ed25519_pubkey")
        self.lockOpenedSecs = self.config.getint("brmdoor", "lock_opened_secs")
        self.unknownUidTimeoutSecs = self.config.getint("brmdoor", "unknown_uid_timeout_secs")
        self.logFile = self.config.get("brmdoor", "log_file")
        self.logLevel = self.convertLoglevel(self.config.get("brmdoor", "log_level"))
        self.unlocker = self.config.get("brmdoor", "unlocker")
    
    def convertLoglevel(self, levelString):
        """Converts string 'debug', 'info', etc. into corresponding
        logging.XXX value which is returned.
        
        @raises BrmdoorConfigError if the level is undefined
        """
        try:
            return getattr(logging, levelString.upper())
        except AttributeError:
            raise BrmdoorConfigError("No such loglevel - %s" % levelString)

class NFCScanner(object):
    """Thread reading data from NFC reader"""
            
    def __init__(self, config):
        """Create worker reading UIDs from PN53x reader.
        """
        self.authenticator = UidAuthenticator(config.authDbFilename)
        self.hmacAuthenticator = None
        self.desfireAuthenticator = None
        self.unknownUidTimeoutSecs = config.unknownUidTimeoutSecs
        self.lockOpenedSecs = config.lockOpenedSecs
        
        unlockerClassName = config.unlocker
        unlockerClass = getattr(unlocker, unlockerClassName)
        self.unlocker = unlockerClass(config)

    def run(self):
        """
        Waits for a card to get into reader field. Reads its UID and
        compares to database of authorized users. Unlocks lock if
        authorized.
        """
        self.nfc = NFCDevice()
        self.hmacAuthenticator = YubikeyHMACAuthenthicator(
            config.authDbFilename, self.nfc
        )
        self.desfireAuthenticator = DesfireEd25519Authenthicator(
            config.authDbFilename, self.nfc,
            config.desfirePubkey
        )
        #self.nfc.pollNr = 0xFF #poll indefinitely
        while True:
            try:
                uid_hex = hexlify(self.nfc.scanUID())
                logging.debug("Got UID %s", uid_hex)
                if len(uid_hex) > 0:
                    self.actOnUid(uid_hex)
                else:
                    #prevent busy loop if reader goes awry
                    time.sleep(0.3)
            except NFCError, e:
                #this exception happens also when scanUID times out
                logging.debug("Failed to wait for RFID card: %s", e)
            except KeyboardInterrupt:
                logging.info("Exiting on keyboard interrupt")
                self.nfc.close()
                self.nfc.unload()
                self.unlocker.lock()
                sys.exit(2)
            except Exception:
                logging.exception("Exception in main unlock thread")
                
    def actOnUid(self, uid_hex):
        """
        Do something with the UID scanned. Try to authenticate it against
        database and open lock if authorized.
        """
        record = self.authenticator.fetchUidRecord(uid_hex)
        
        #direct UID match
        if record is not None:
            logging.info("Unlocking for UID %s", record)
            self.unlocker.unlock()
            return
        
        #test for Yubikey HMAC auth
        record = self.hmacAuthenticator.checkHMACforUID(uid_hex)
        
        if record is not None:
            logging.info("Unlocking after HMAC for UID %s", record)
            self.unlocker.unlock()
            return

        #test for Desfire NDEF auth
        record = self.desfireAuthenticator.checkUIDSignature(uid_hex)

        if record is not None:
            logging.info("Unlocking after Desfire NDEF ed25519 check for UID %s", record)
            self.unlocker.unlock()
            return

        logging.info("Unknown UID %s", uid_hex)
        time.sleep(self.unknownUidTimeoutSecs)
        


if __name__  == "__main__":
    
    if len(sys.argv) < 2:
        print >> sys.stderr, "Syntax: brmdoor_nfc_daemon.py brmdoor_nfc.config"
        sys.exit(1)
    
    config = BrmdoorConfig(sys.argv[1])
    
    if config.logFile == "-":
        logging.basicConfig(stream=sys.stderr, level=config.logLevel,
            format="%(asctime)s %(levelname)s %(message)s [%(pathname)s:%(lineno)d]")
    else:
        logging.basicConfig(filename=config.logFile, level=config.logLevel,
            format="%(asctime)s %(levelname)s %(message)s [%(pathname)s:%(lineno)d]")
    
    nfcScanner = NFCScanner(config)
    nfcScanner.run()
    
