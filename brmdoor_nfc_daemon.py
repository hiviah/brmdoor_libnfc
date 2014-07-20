#!/usr/bin/env python

import sys
import threading
import Queue
import logging
import time
import ConfigParser

from binascii import hexlify


from brmdoor_nfc import NFCDevice, NFCError
from brmdoor_authenticator import UidAuthenticator

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
		self.lockOpenedSecs = self.config.getint("brmdoor", "lock_opened_secs")
		self.logFile = self.config.get("brmdoor", "log_file")
		self.logLevel = self.convertLoglevel(self.config.get("brmdoor", "log_level"))
	
	def convertLoglevel(self, levelString):
		"""Converts string 'debug', 'info', etc. into corresponding
		logging.XXX value which is returned.
		
		@raises ValueError if the level is undefined
		"""
		try:
			return getattr(logging, levelString.upper())
		except AttributeError:
			raise BrmdoorConfigError("No such loglevel - %s" % levelString)

class NfcThread(threading.Thread):
	"""Thread reading data from NFC reader"""
	        
	def __init__(self, uidQueue):
		"""Create thread reading UIDs from PN53x reader.
		"""
		self.uidQueue = uidQueue
		threading.Thread.__init__(self)

	def run(self):
		"""
		Waits for a card to get into reader field. Reads its UID and
		stores it into uidQueue for later authentication check.
		"""
		self.nfc = NFCDevice()
		while True:
			try:
				uid_hex = hexlify(self.nfc.scanUID())
				logging.debug("Got UID %s" % uid_hex)
				if len(uid_hex) > 0:
					self.uidQueue.put(uid_hex)
					time.sleep(0.3)
			except NFCError, e:
				#this exception happens also when scanUID times out
				logging.debug("Failed to wait for RFID card: %s", e)
				

class UnlockThread(threading.Thread):
	"""Thread checking UIDs whether they are authorized"""
	        
	def __init__(self, uidQueue, authenticatorDBFname, lockOpenedSecs):
		"""Create thread reading UIDs from PN53x reader.
		"""
		self.uidQueue = uidQueue
		self.authenticatorDBFname = authenticatorDBFname
		self.lockOpenedSecs = lockOpenedSecs
		threading.Thread.__init__(self)

	def run(self):
		"""
		Reads hex UIDs from queue, tries to find them in sqlite database.
		
		If match in database is found, then unlock the lock (for now
		only logs).
		"""
		self.authenticator = UidAuthenticator(self.authenticatorDBFname)
		while True:
			uid_hex = self.uidQueue.get()
			
			record = self.authenticator.fetchUidRecord(uid_hex)
			
			if record is None:
				logging.info("Unknown UID %s", uid_hex)
				time.sleep(1)
			else:
				logging.info("Unlocking for %s", record)
				time.sleep(self.lockOpenedSecs)

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
	
	uidQueue = Queue.Queue(1)
	
	nfcThread = NfcThread(uidQueue)
	nfcThread.start()
	
	unlockThread = UnlockThread(uidQueue, config.authDbFilename, config.lockOpenedSecs)
	unlockThread.start()
	
	uidQueue.join()
	
