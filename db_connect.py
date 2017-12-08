import MySQLdb

# this class connects to the database. 
# anychanges in db credentials are made here

class DBConnect():

	def __init__(self):
		pass

	def connect(self):
		db = MySQLdb.connect("localhost", "root", "root", "heap")
		cursor = db.cursor()
		return db, cursor

