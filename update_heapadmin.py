from db_connect import DBConnect
from passlib.hash import sha256_crypt

try:

	db_connection = DBConnect()
	db, cursor = db_connection.connect()

	username = 'heapadmin'
	password = sha256_crypt.encrypt('heapadmin1234')

	sql = "insert into users (username, password, admin) values ('"+username+"','"+password+"', 1)"

	cursor.execute(sql)
	db.commit()

	cursor.close()
	db.close()

except Exception as e:
	print e