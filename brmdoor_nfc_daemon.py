#!/usr/bin/env python2

import sys
import logging
import time
import ConfigParser
import threading
import irc.client
import ssl
import Queue

from binascii import hexlify
from functools import partial

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
        self.useIRC = self.config.getboolean("irc", "enabled")
        if self.useIRC:
            self.ircServer = self.config.get("irc", "server")
            self.ircPort = self.config.getint("irc", "port")
            self.ircNick = self.config.get("irc", "nick")
            self.ircPassword = self.config.get("irc", "password") if self.config.has_option("irc", "password") else None
            self.ircChannels = self.config.get("irc", "channels").split(" ")
            self.ircUseTLS = self.config.getboolean("irc", "tls")
            self.ircReconnectDelay = self.config.getint("irc", "reconnect_delay")
        self.useOpenSwitch = self.config.getboolean("open-switch", "enabled")
        if self.useOpenSwitch:
            self.switchStatusFile = self.config.get("open-switch", "status_file")

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
            
    def __init__(self, config, msgQueue, ircThread):
        """Create worker reading UIDs from PN53x reader.
        """
        self.authenticator = UidAuthenticator(config.authDbFilename)
        self.hmacAuthenticator = None
        self.desfireAuthenticator = None
        self.unknownUidTimeoutSecs = config.unknownUidTimeoutSecs
        self.lockOpenedSecs = config.lockOpenedSecs
        self.msgQueue = msgQueue
        self.ircThread = ircThread
        
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
            config.desfirePubkey.decode("hex")
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

    def sendIrcMessage(self, msg):
        """
        Send message to IRC bot. Message is dropped if bot is not connected
        :param msg: message to be displayed in joined channels
        """
        if not self.ircThread:
            return
        if self.ircThread.getConnected():
            self.msgQueue.put(msg)

    def actOnUid(self, uid_hex):
        """
        Do something with the UID scanned. Try to authenticate it against
        database and open lock if authorized.
        """
        record = self.authenticator.fetchUidRecord(uid_hex)
        
        #direct UID match
        if record is not None:
            logging.info("Unlocking for UID %s", record)
            self.sendIrcMessage("Unlocking door")
            self.unlocker.unlock()
            return
        
        #test for Yubikey HMAC auth
        record = self.hmacAuthenticator.checkHMACforUID(uid_hex)
        
        if record is not None:
            logging.info("Unlocking after HMAC for UID %s", record)
            self.sendIrcMessage("Unlocking door")
            self.unlocker.unlock()
            return

        #test for Desfire NDEF auth
        record = self.desfireAuthenticator.checkUIDSignature(uid_hex)

        if record is not None:
            logging.info("Unlocking after Desfire NDEF ed25519 check for UID %s", record)
            self.sendIrcMessage("Unlocking door")
            self.unlocker.unlock()
            return

        logging.info("Unknown UID %s", uid_hex)
        self.sendIrcMessage("Denied unauthorized card")
        time.sleep(self.unknownUidTimeoutSecs)
        
class IrcThread(threading.Thread):
    """
    Class for showing messages about lock events and denied/accepted cards
    """
    def __init__(self, config, msgQueue):
        """
        Create thread for IRC connection.

        :param config - BrmdoorConfig object
        :param msgQueue: Queue.Queue instance where we will get messages to show
        """
        self.server = config.ircServer
        self.port = config.ircPort
        self.nick = config.ircNick
        self.password = config.ircPassword
        self.channels = config.ircChannels
        self.useSSL = config.ircUseTLS
        self.reconnectDelay = config.ircReconnectDelay
        self.msgQueue = msgQueue
        self.connection = None
        self.reactor = None
        self.connected = False
        self.threadLock = threading.Lock()

        threading.Thread.__init__(self)

    def setConnected(self, connected):
        with self.threadLock:
            self.connected = connected

    def getConnected(self):
        with self.threadLock:
            return self.connected

    def connect(self):
        """
        Connect to server.
        :returns true if connection was successful
        """
        try:
            ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
            self.reactor = irc.client.Reactor()
            self.connection = self.reactor.server().connect(
                self.server,
                self.port,
                self.nick,
                self.password,
                "brmdoor-libnfc",
                connect_factory=ssl_factory if self.useSSL else lambda sock: sock,
            )

            return True
        except irc.client.ServerConnectionError, e:
            logging.error("Could not connect to IRC server: %s", e)
            return False

    def onConnect(self, connection, event):
        for channel in self.channels:
            connection.join(channel)

    def onDisconnect(self, connection, event):
        logging.info("Disconnected, waiting for %s seconds before reconnect", self.reconnectDelay)
        self.setConnected(False)
        time.sleep(self.reconnectDelay)
        self.setConnected(self.connect())

    def run(self):
        logging.debug("Starting IRC thread")
        while True:
            connected = self.connect()
            logging.info("IRC connected: %s", connected)
            self.setConnected(connected)
            self.connection.add_global_handler("welcome", partial(IrcThread.onConnect, self))
            self.connection.add_global_handler("disconnect", partial(IrcThread.onDisconnect, self))

            while self.getConnected():
                self.reactor.process_once(timeout=5)
                try:
                    msg = self.msgQueue.get_nowait()
                    self.connection.privmsg_many(self.channels, msg)
                except Queue.Empty:
                    pass
            else:
                time.sleep(self.reconnectDelay)

class OpenSwitchThread(threading.Thread):
    """
    Class for watching OPEN/CLOSED switch that
    """
    def __init__(self, config, ircThread):
        """
        Create thread for IRC connection.

        :param config - BrmdoorConfig object
        :param ircThread: IrcThread through which we can set and receive current topics
        """
        self.statusFile = config.statusFile
        threading.Thread.__init__(self)

    def run(self):
        while True:
            time.sleep(1)


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

    ircMsgQueue = Queue.Queue()
    ircThread = None
    if config.useIRC:
        ircThread = IrcThread(config, ircMsgQueue)
        ircThread.setDaemon(True)
        ircThread.start()

    nfcScanner = NFCScanner(config, ircMsgQueue, ircThread)
    nfcScanner.run()

