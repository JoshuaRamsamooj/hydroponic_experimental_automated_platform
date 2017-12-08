from db_connect import DBConnect
from heap import *
import datetime
import random

heap_level = Heap()


now = datetime.datetime.now() - datetime.timedelta(days=0)
dt = now.strftime('%Y-%m-%d %H:%M:%S')

trough_levels_table = "trough_levels"

db_connection= DBConnect()
db, cursor = db_connection.connect()

level = []

for i in range(1,6): # gets sensor data for all the troughs 
    l = heap_level.get_level("trough_"+str(i))[0]
    level.append(l)

sql2 = "insert into "+trough_levels_table+" (trough_1, " \
      "trough_2, trough_3, trough_4, trough_5, data_date) values (%s, %s, %s, %s, %s, %s)"


cursor.execute(sql2, (level[0],level[1],level[2],level[3],level[4], dt))

db.commit()
db.close()
