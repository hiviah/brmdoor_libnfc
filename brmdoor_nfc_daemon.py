#!/usr/bin/env python2

import sys
import logging
import logging.handlers
import time
import ConfigParser
import threading
import irc.client
import ssl
import Queue
import re

from binascii import hexlify
from functools import partial

from nfc_smartcard import NFCDevice, NFCError
from brmdoor_authenticator import UidAuthenticator, YubikeyHMACAuthenthicator, DesfireEd25519Authenthicator
import unlocker

# Map request to change channel's topic to its new prefix. Prefix and rest are delimited with |
# Channel prefix must include the | character at end, e.g. "OPEN |" or "CLOSED |"
channelPrefixMap = {}

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
            if len(self.ircChannels) < 1:
                print >> sys.stderr, "You must specify at least one channel for IRC when IRC is enabled"
                sys.exit(1)
            self.ircUseTLS = self.config.getboolean("irc", "tls")
            self.ircReconnectDelay = self.config.getint("irc", "reconnect_delay")
        self.useOpenSwitch = self.config.getboolean("open_switch", "enabled")
        if self.useOpenSwitch:
            self.switchStatusFile = self.config.get("open_switch", "status_file")
            self.switchOpenValue = self.config.get("open_switch", "open_value")

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
                    e = threading.Event()
                    e.wait(timeout=0.3)
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
            logging.info("Request topic")
            channelPrefixMap[self.ircThread.channels[0]] = "OPEN |"
            self.ircThread.getTopic(self.ircThread.channels[0])

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
        e = threading.Event()
        e.wait(timeout=self.unknownUidTimeoutSecs)

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
        self.connection = None

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

    def getTopic(self, channel):
        """ Request topic. You need to wait in currenttopic callback for result """
        with self.threadLock:
            self.connection.topic(channel)

    def setTopic(self, channel, newTopic):
        with self.threadLock:
            return self.connection.topic(channel, newTopic)

    def onConnect(self, connection, event):
        for channel in self.channels:
            connection.join(channel)

    def onDisconnect(self, connection, event):
        logging.info("Disconnected, waiting for %s seconds before reconnect", self.reconnectDelay)
        self.setConnected(False)
        time.sleep(self.reconnectDelay)
        self.setConnected(self.connect())

    def onJoin(self, connection, event):
        nick, _ = event.source.split("!", 2)
        if (nick == config.ircNick):
            logging.info("Joined channel, event: %s", event)
        logging.debug("join event - source %s, target: %s, type: %s", event.source, event.target, event.type)
        #connection.privmsg(self.channels[0], "brmbot-libfc starting")

    def onTopic(self, connection, event):
        global channelPrefixMap
        channel = event.arguments[0]
        topic = event.arguments[1]
        logging.info("Current topic: channel %s, topic %s", channel, topic)
        logging.info("Topic event - source %s, target: %s, type: %s", event.source, event.target, event.type)
        # if change was requested, update channel topic
        if channelPrefixMap.get(channel):
            #update topic part before |, or replace entirely if | is not present
            topicParts = topic.split("|", 1)
            restOfTopic = ""
            if (len(topicParts) > 1):
                restOfTopic = topicParts[1]

            newTopic = channelPrefixMap[channel] + restOfTopic
            logging.info("Setting new topic for channel %s: %s", channel, newTopic)
            self.setTopic(channel, newTopic)
            del channelPrefixMap[channel] # remove request

    def onNoTopic(self, connection, event):
        channel = event.arguments[0]
        topic = event.arguments[1]
        logging.info("No topic: channel %s, topic %s", channel, topic)
        logging.info("No topic event - source %s, target: %s, type: %s", event.source, event.target, event.type)

    def run(self):
        logging.debug("Starting IRC thread")
        while True:
            try:
                connected = self.connect()
                logging.info("IRC connected: %s", connected)
                self.setConnected(connected)
                self.connection.add_global_handler("welcome", partial(IrcThread.onConnect, self))
                self.connection.add_global_handler("disconnect", partial(IrcThread.onDisconnect, self))
                self.connection.add_global_handler("join", partial(IrcThread.onJoin, self))
                self.reactor.server().add_global_handler("notopic", partial(IrcThread.onNoTopic, self))
                self.reactor.server().add_global_handler("currenttopic", partial(IrcThread.onTopic, self))

                # Topic handler requires sadly completely different API to retrieve topic
                # see https://github.com/jaraco/irc/issues/132

                while self.getConnected():
                    self.reactor.process_once(timeout=5)
                    try:
                        with self.threadLock:
                            msg = self.msgQueue.get_nowait()
                            self.connection.privmsg_many(self.channels, msg)
                    except Queue.Empty:
                        pass
            except Exception:
                logging.exception("Exception in IRC thread")
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
        self.statusFile = config.switchStatusFile
        self.openValue = config.switchOpenValue
        self.ircThread = ircThread
        threading.Thread.__init__(self)

    def run(self):
        logging.info("Switch thread start")
        if self.ircThread is None: #no point in running this thread if we can't report it anywhere
            return

        lastStatus = None #Some random value so that first time it will be registered as change
        while True:
            try:
                switchFile = open(self.statusFile)
                status = switchFile.read(1)
                switchFile.close()
                if status != lastStatus:
                    logging.info("Open switch status changed, new status: %s", status)
                    lastStatus = status
                    if status == self.openValue:
                        strStatus = "OPEN |"
                    else:
                        strStatus = "CLOSED |"

                    if self.ircThread.connected:
                        with self.ircThread.threadLock:
                            for channel in self.ircThread.channels:
                                #TODO: getTopic always returns None, the problem is in implementenation
                                topic = self.ircThread.getTopic(channel)
                                if not topic or not re.match(r"^\s*(OPEN|CLOSED) \|", topic):
                                    newTopic = strStatus
                                else:
                                    newTopic = re.sub(r"^\s*(OPEN|CLOSED) \|", strStatus, topic)
                                self.ircThread.setTopic(channel, newTopic)
            except (IOError, OSError):
                logging.exception("Could not read switch status")
                pass #silently ignore non-existent file and other errors, otherwise it'd spam log
            except Exception:
                logging.exception("Exception in open switch thread")
            e = threading.Event()
            e.wait(timeout=1)


if __name__  == "__main__":
    
    if len(sys.argv) < 2:
        print >> sys.stderr, "Syntax: brmdoor_nfc_daemon.py brmdoor_nfc.config"
        sys.exit(1)
    
    config = BrmdoorConfig(sys.argv[1])
    fmt="%(asctime)s %(levelname)s %(message)s [%(pathname)s:%(lineno)d]"

    if config.logFile == "-":
        logging.basicConfig(stream=sys.stderr, level=config.logLevel, format=fmt)
    else:
        handler = logging.handlers.RotatingFileHandler(filename=config.logFile, maxBytes=1000000, backupCount=5)
        handler.setLevel(config.logLevel)
        handler.setFormatter(logging.Formatter(fmt))
        mainLogger = logging.getLogger('')
        mainLogger.addHandler(handler)
        mainLogger.setLevel(config.logLevel)

    ircMsgQueue = Queue.Queue()
    ircThread = None
    openSwitchThread = None

    if config.useIRC:
        ircThread = IrcThread(config, ircMsgQueue)
        ircThread.setDaemon(True)
        ircThread.start()
    if config.useOpenSwitch:
        openSwitchThread = OpenSwitchThread(config, ircThread)
        openSwitchThread.setDaemon(True)
        openSwitchThread.start()

    nfcScanner = NFCScanner(config, ircMsgQueue, ircThread)
    nfcScanner.run()

