import os
import sqlite3
import hmac
import hashlib
import logging

from brmdoor_nfc import NFCError


class UidRecord(object):
	"""Represents UID<->nick pair"""
	
	def __init__(self, uid_hex, nick):
		"""
		Create instance binding UID to nick. UIDs should be either 4, 7
		or 10 bytes long, but that's ISO14443 thing - this object has
		no such limitation.
		
		UID will be stored in uppercase hex, converted if necessary.
		
		@param uid_hex: uid in hex
		@param nick: nickname this UID belongs to
		"""
		self.uid_hex = uid_hex.upper()
		self.nick = nick
	
	def __str__(self):
		return "(uid: %s, nick: %s)" % (self.uid_hex, self.nick)
	
	def __repr__(self):
		return "<UidRecord: uid: %s, nick: %s>" % \
			(repr(self.uid_hex), repr(self.nick))

class UidAuthenticator(object):
	"""Checks UIDs of ISO14443 RFID cards against database."""
	
	def __init__(self, filename):
		"""
		Connects to database by given filename and later checks UIDs
		against that database.
		"""
		#open in autocommit mode - we are not changing anything
		self.conn = sqlite3.connect(filename, isolation_level=None)

	def fetchUidRecord(self, uid_hex):
		"""
		Returns first record that matches given UID or None if nothing
		is found.
		
		@param uid_hex: uid to match in hex
		@returns UidRecord instance if found, None otherwise
		"""
		cursor = self.conn.cursor()
		sql = "SELECT nick FROM authorized_uids WHERE UPPER(uid_hex)=?"
		sql_data =(uid_hex.upper(),)
		
		cursor.execute(sql, sql_data)
		record = cursor.fetchone()
		
		if record is None:
			return None
		
		nick = record[0]
		return UidRecord(uid_hex, nick)
	
	def shutdown(self):
		"""Closes connection to database"""
		self.conn.close()


class YubikeyHMACAuthenthicator(object):
	"""
	Uses Yubikey Neo's built-in HMAC functionality on slot 2 (needs to be
	configured using Yubikey tools to be on this slot).
	"""
	def __init__(self, filename, nfcReader):
		"""
		Connects to database by given filename and later checks UIDs
		against that database.
		"""
		#again autocommit mode
		self.conn = sqlite3.connect(filename, isolation_level=None)
		self.nfcReader = nfcReader
	
	def hmacCheck(self, key, challenge, result):
		"""
		Returns true iff HMAC-SHA1 with given key and challenge string
		transforms into given result.
		"""
		hashed = hmac.new(key, challenge, hashlib.sha1)
		#We should use hmac.compare_digest(), but that's in new Python
		#version only. Here timing side channels are not much of concern.
		return hashed.digest() == result

	def checkHMACforUID(self, uid_hex):
		"""
		Checks if UID is in database. If so
		@param uid_hex: uid to match in hex
		@returns UidRecord instance if found, None otherwise
		"""
		cursor = self.conn.cursor()
		sql = "SELECT nick, key_hex FROM authorized_hmac_keys WHERE UPPER(uid_hex)=?"
		sql_data =(uid_hex.upper(),)
		
		cursor.execute(sql, sql_data)
		record = cursor.fetchone()
		
		if record is None:
			return None
		
		nick = record[0]
		secretKey = record[1].decode("hex")
		
		challenge = os.urandom(32)
		
		# Select HMAC-SHA1 on slot 2 from Yubikey
		apdusHex = [
			"00 A4 04 00 07 A0 00 00 05 27 20 01",
			"00 01 38 00 %02x %s" % (len(challenge), challenge.encode("hex"))
		]
		
		rapdu = None
		
		for apduHex in apdusHex:
			try:
				apdu = apduHex.replace(" ", "").decode("hex")
				rapdu = self.nfcReader.sendAPDU(apdu)
				if not rapdu.valid or rapdu.sw() != 0x9000:
					raise NFCError("HMAC - response SW is not 0x9000")
			except NFCError, e:
				logging.debug("Yubikey HMAC command failed: %s" % e.what())
				return None
			
		if not self.hmacCheck(secretKey, challenge, rapdu.data()):
			logging.info("HMAC check failed for UID %s", uid_hex)
			return None
		
		return UidRecord(uid_hex, nick)
	
	def shutdown(self):
		"""Closes connection to database"""
		self.conn.close()
	
#test routine
if __name__ == "__main__":
	authenticator = UidAuthenticator("test_uids_db.sqlite")
	
	record = authenticator.fetchUidRecord("043a1482cc2280")
	print "For UID 043a1482cc2280 we found:", repr(record)
	
	record = authenticator.fetchUidRecord("34795fad")
	print "For UID 34795fad we found:", repr(record)
	
	record = authenticator.fetchUidRecord("01020304")
	print "For UID 01020304 we found:", repr(record)
	
	authenticator.shutdown()
