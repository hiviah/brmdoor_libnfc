import sqlite3

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
		return "<UidRecord: uid: %s, nick: %s>" % (self.uid_hex, self.nick)

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


#test routine
if __name__ == "__main__":
	authenticator = UidAuthenticator("test_uids_db.sqlite")
	
	record = authenticator.fetchUidRecord("043a1482cc2280")
	print "For UID 043a1482cc2280 we found:", str(record)
	
	record = authenticator.fetchUidRecord("34795fad")
	print "For UID 34795fad we found:", str(record)
	
	record = authenticator.fetchUidRecord("01020304")
	print "For UID 01020304 we found:", str(record)
	
	authenticator.shutdown()
