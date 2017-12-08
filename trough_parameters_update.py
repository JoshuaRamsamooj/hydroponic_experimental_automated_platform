from db_connect import DBConnect
from heap import *
import datetime
import random

heap_parameters = Heap()

i=0

now = datetime.datetime.now() - datetime.timedelta(days=i)
dt = now.strftime('%Y-%m-%d %H:%M:%S')

trough_parameters_table = "trough_parameters"

db_connection= DBConnect()
db, cursor = db_connection.connect()



humidity, temperature = heap_parameters.get_humidity_temperature()
light = heap_parameters.get_light()


sql1 = "insert into "+trough_parameters_table+" (temperature, humidity, " \
      "light, data_date) values (%s, %s, %s, %s)"

cursor.execute(sql1, (temperature, humidity, light, dt))

db.commit()
db.close()
