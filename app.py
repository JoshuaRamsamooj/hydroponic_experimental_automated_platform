from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, session
from db_connect import *
from heap import Heap
from random import randint
import json
import time
import operator
import os
from validate_email_address import validate_email
from passlib.hash import sha256_crypt
from functools import wraps
import subprocess
from datetime import timedelta
from flask.ext.uploads import UploadSet, configure_uploads, IMAGES
from ndvi import NDVI


app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(seconds=3600) # logout after 30 mins of inactivity 
photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = '/home/pi/heap/heap/static/img'
configure_uploads(app,photos)
db_connection = DBConnect()
flask_heap = Heap()
flask_ndvi = NDVI()

refresh_time = 1

display_names = {
	"email":"Alarms Recipients' Emails",
	"k": "K - Ratio",
	"sman": "Secondary Macro Nutrients - Ratio",
	"n": "N - Ratio",
	"mn": "Micro Nutrients - Ratio",
	"p": "P - Ratio",
	"water": "Water - Ratio",
	"threshold": "Minimum Threshold",
	"maxlevel": "Maximum Threshold",
	"sensor_height": "Sensor Height",
	"length": "Length",
	"radius": "Radius",
	"base_radius": "Base Radius",
	"base_area": "Base Area",
	"top_radius": "Top Radius",
	"temperature": "Temperature",
	"humidity": "Humidity",
	"light": "Light",
	"trough_1":"Trough 1",
	"trough_2":"Trough 2",
	"trough_3":"Trough 3",
	"trough_4":"Trough 4",
	"trough_5":"Trough 5",
	"tank_6":"Tank 6",
	"tank_7":"Tank 7",
	"tank_8":"Tank 8",
	"tank_9":"Tank 9",
	"tank_10":"Tank 10",
	"tank_mixing":"Mixing Tank",
	"tank_water":"Water Tank",
	"valve_1":"Valve 1",
	"valve_2":"Valve 2",
	"valve_3":"Valve 3",
	"valve_4":"Valve 4",
	"valve_5":"Valve 5",
	"valve_drain":"Drain Valve",
	"valve_base":"Mixing Tank Base Valve",
	"pump_6":"Pump 6",
	"pump_7":"Pump 7",
	"pump_8":"Pump 8",
	"pump_9":"Pump 9",
	"pump_10":"Pump 10",
	"pump_water":"Water Pump",
	"pump_mixing":"Mixing Pump",
	"pump_air":"Air Pump",
	'':'',
	"camera": "Camera",
	"pump_max_voltage": "Operating Range Maximum",
	"pump_min_voltage": "Operating Range Minimum",
	"pump_intercept" : "Pump Equation Intercept",
	"flow_min" : "Flow Meter Minimum",
	"pump_supply_voltage": "Pump Supply Voltage",
	"pump_gradient" : "Pump Equation Gradient",
	"level_schedule" : "Trough Level Capture",
	"ambient_schedule": "Ambient Conditions Capture", 
	"camera_schedule": "Image Capture (With NDVI Calculation)",
	"camera_schedule_no_ndvi": "Image Capture (Without NDVI Calculation)",
	"analog0": "Additional Input 0",
	"analog1": "Additional Input 1",
	"analog2": "Additional Input 2",
	"analog3": "Additional Input 3",
	"analog4": "Additional Input 4",
	"analog5": "Additional Input 5",
	"analog6": "Additional Input 6",
	"analog7": "Additional Input 7",
	"kp": "Level Controller Gain",
	"dt": "Level Controller Deadtime"
}

def get_latest_alarm():
	try:
		db, cursor = db_connection.connect()
		sql = "select alarm_id from alarms order by alarm_id desc limit 1"
		cursor.execute(sql)
		latest_id = cursor.fetchall()[0][0]
		cursor.close()
		db.close()
		return latest_id
	except:
		return 0

latest_alarm_id = get_latest_alarm()

def cnt_alarms():
	# end point to check number of alarms
	db, cursor = db_connection.connect()
	sql = "select count(*) from alarms where alarm_status=1"
	cursor.execute(sql)
	alarm_count = cursor.fetchall()[0][0]
	cursor.close()
	db.close()

	return alarm_count

# login required decorator
def login_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)

		else:
			return redirect(url_for('login'))

	return wrap

def admin_required(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'admin' in session and 'logged_in' in session:
			return f(*args, **kwargs)

		else:
			return redirect(url_for('index'))

	return wrap

@app.route("/_get_equipment_data")
@login_required
def _get_equipment_data():

	def get_equipment_data():
		while True:

			try:
				db_connection = DBConnect()
				db, cursor = db_connection.connect()
				
				sql = "select * from equipment_status"
				cursor.execute(sql)
				results = cursor.fetchall()

				data = {}

				for row in results:
					equipment, value = row
					data[equipment] = value
				
				sql_critical = "select affected_equipment from alarms where alarm_status=1 and alarm_priority = 'critical'"
				sql_high = "select affected_equipment from alarms where alarm_status=1 and alarm_priority = 'high'"
				sql_medium = "select affected_equipment from alarms where alarm_status=1 and alarm_priority = 'medium'"
				sql_low = "select affected_equipment from alarms where alarm_status=1 and alarm_priority = 'low'"

				# critical ==================================        
				cursor.execute(sql_critical)
				results = cursor.fetchall()
				critical = []

				for row in results:
					critical += row[0].replace(' ','').split(',')
					# removes spaces

				critical = list(set(critical))  # unique affected_components

				# high ==================================        
				cursor.execute(sql_high)
				results = cursor.fetchall()
				high = []

				for row in results:
					high += row[0].replace(' ','').split(',')
					# removes spaces

				high = list(set(high))  # unique affected_components

				# medium ==================================        
				cursor.execute(sql_medium)
				results = cursor.fetchall()
				medium = []

				for row in results:
					medium += row[0].replace(' ','').split(',')
					# removes spaces

				medium = list(set(medium))  # unique affected_components

				# low ==================================        
				cursor.execute(sql_low)
				results = cursor.fetchall()
				low = []

				for row in results:
					low += row[0].replace(' ','').split(',')
					# removes spaces

				low = list(set(low))  # unique affected_components


				critical = critical
				high = [x for x in high if x not in critical]
				medium = [x for x in medium if x not in critical+high]
				low = [x for x in low if x not in critical+high+medium]

				db.commit()
				cursor.close()
				db.close()

				data['critical'] = critical
				data['high'] = high
				data['medium'] = medium
				data['low'] = low

 
			except Exception as e:
				# # print e
				data = {}
 
			data = json.dumps(data)
			yield 'data: {0}\n\n'.format(data)
			time.sleep(refresh_time)
	
	return Response(get_equipment_data(), 
		mimetype='text/event-stream')


@app.route("/_toggle_trough", methods=['POST'])
@admin_required
def toggle_trough():

	try:
		trough = request.form['trough']
		state = request.form['state']

		# update state for that trough in database

		if state == "true":
			# # print relay
			flask_heap.set_heapdata(trough, 'state', '1')
			# put off in db

		elif state == "false":
			flask_heap.set_heapdata(trough, 'state', '0')
			

		return jsonify({'status': True})

	except:

		return jsonify({'status': False})

@app.route("/_toggle_system", methods=['POST'])
@login_required
def toggle_system():

	try:
		state = request.form['state']

		if state == "true":
			flask_heap.set_heapdata('system_variables', 'system_state', '1')
			# put off in db

		elif state == "false":
			# ensure dosing pumps are off
			flask_heap.turn_off_gpio(22)
			flask_heap.turn_off_gpio(15)
			flask_heap.turn_off_gpio(18)
			flask_heap.turn_off_gpio(23)
			flask_heap.turn_off_gpio(24)
			flask_heap.turn_off_gpio(25)
			

			# turn off all relays
			flask_heap.turn_on_gpio(5)
			flask_heap.turn_on_gpio(6)
			flask_heap.turn_on_gpio(13)
			flask_heap.turn_on_gpio(19)
			flask_heap.turn_on_gpio(26)
			flask_heap.turn_on_gpio(12)
			flask_heap.turn_on_gpio(16)
			flask_heap.turn_on_gpio(20)
			flask_heap.turn_on_gpio(21)

			flask_heap.set_heapdata('system_variables', 'system_state', '0')
			flask_heap.set_heapdata('system_variables', 'plant_lights', '0')
			flask_heap.set_heapdata('system_variables', 'air_pump', '0')
			
			# restart pi
			os.system('sudo shutdown -r now')

		return jsonify({'status': True})

	except:
		return jsonify({'status': False})

@app.route("/_toggle_switch", methods=['POST'])
@login_required
def toggle_switch():

	try:
		toggle_switch = request.form['toggle_switch']
		state = request.form['state']


		if toggle_switch == 'plant_lights':
			relay = 20
		elif toggle_switch == 'air_pump':
			relay = 21

		if state == "true":
			flask_heap.turn_on_relays([relay])
			flask_heap.set_heapdata('system_variables', toggle_switch, '1')
			if toggle_switch == "air_pump":
				flask_heap.set_heapdata('equipment_status', 'pump_air', "'ON'")

		elif state == "false":
			flask_heap.turn_off_relays([relay])
			flask_heap.set_heapdata('system_variables', toggle_switch, '0')
			if toggle_switch == "air_pump":
				flask_heap.set_heapdata('equipment_status', 'pump_air', "'OFF'")

		return jsonify({'status': True})

	except:

		return jsonify({'status': False})


@app.route("/")
@login_required
def index():
	states={}

	if flask_heap.get_heapdata('system_variables', 'system_state') == 1:
		states['system_state'] = 'on'
	else:
		states['system_state'] = 'off' 

	if flask_heap.get_heapdata('system_variables', 'air_pump') == 1:
		states['air_pump'] = 'on'
	else:
		states['air_pump'] = 'off'  

	if flask_heap.get_heapdata('system_variables', 'plant_lights') == 1:
		states['plant_lights'] = 'on'
	else:
		states['plant_lights'] = 'off'  

	
	return render_template('index.html', 
		alarmcount=cnt_alarms(),
		states = states)

@app.route('/alarms/')
@login_required
def hello():
	return redirect(url_for('currentalarms'))

@app.route("/alarms/currentalarms/")
@login_required
def currentalarms():
	db, cursor = db_connection.connect()
	# current alarms ==========================================

	current_alarms_sql = "select alarm_id, alarm_description, alarm_date, alarm_priority, affected_equipment from alarms where alarm_status = 1 order by alarm_id desc"

	cursor.execute(current_alarms_sql)
	rows = cursor.fetchall()

	current_alarms = []
	for row in rows:
		this_alarm = {}
		# get description
		this_alarm['description'] = row[1]
		# get priority
		this_alarm['priority'] = row[3]
		# get date
		this_alarm['date'] = row[2]
		# get id
		this_alarm['id'] = row[0]

		# get equipment affected
		affected_equipment = row[4]
		affected_equipment = affected_equipment.replace(' ','').split(',')
		affected_equipment = [display_names[x] for x in affected_equipment]
		affected_equipment = ', '.join(affected_equipment)

		this_alarm['affected_equipment'] = affected_equipment

		current_alarms.append(this_alarm)

	cursor.close()
	db.close()
	# def any_new_alarms():
	return render_template("currentalarms.html",
						   currentAlarms=current_alarms,
						   alarmcount=cnt_alarms())


# alarm logs ==============================================
@app.route("/alarms/alarmlogs/")
@login_required
def alarmlogs():

	db, cursor = db_connection.connect()

	sql = "select alarm_id, alarm_description, " \
	  "alarm_date, clear_date, alarm_priority, affected_equipment," \
	  "alarm_status, user from alarms order by alarm_id desc"

	cursor.execute(sql)
	results = cursor.fetchall()
	alarms = []

	for row in results:
		alarm_id, alarm_description, alarm_date, clear_date, alarm_priority, affected_equipment, alarm_status, user = row
		
		affected_equipment = affected_equipment.replace(' ','').split(',')
		affected_equipment = [display_names[x] for x in affected_equipment]
		affected_equipment = ', '.join(affected_equipment)

		current_row = [alarm_id, alarm_description, alarm_date, clear_date, alarm_priority, affected_equipment, alarm_status, user]
		alarms.append(current_row)

	cursor.close()
	db.close()

	return render_template("alarmlogs.html",
						   alarms=alarms,
						   alarmcount=cnt_alarms())


@app.route("/_clear_alarm", methods=['POST'])
@login_required
def clear_alarm():

	try:
		db, cursor = db_connection.connect()

		alarmid = request.form['alarmid']
		# # print alarmid
		cleardate = time.strftime('%Y-%m-%d %H:%M:%S')

		sql = "update alarms set alarm_status=0, clear_date=%s, user=%s where alarm_id="+str(alarmid)

		cursor.execute(sql, (cleardate, session['username']))
		db.commit()

		cursor.close()
		db.close()

		return jsonify({'status': True})

	except:
		return jsonify({'status': False})


@app.route("/_count_alarms")
@login_required
def count_alarms():
	# end point to check number of alarms
	def check_alarms():
		while True:
			try:
				db, cursor = db_connection.connect()
				sql = "select count(*) from alarms where alarm_status=1"
				cursor.execute(sql)
				alarm_count = cursor.fetchall()[0][0]
				yield 'data: {0}\n\n'.format(alarm_count)
				cursor.close()
				db.close()
			except: 
				alarm_count = ''
				yield 'data: {0}\n\n'.format(alarm_count)

			time.sleep(refresh_time)

	return Response(check_alarms(), mimetype='text/event-stream')


@app.route("/_get_alarms")
@login_required
def get_alarms():
	def check_new_alarms():
		while True:
			try:
			
				db, cursor = db_connection.connect()
				# get current latest id
				sql = "select alarm_id from alarms order by alarm_id desc limit 1"

				cursor.execute(sql)
				current_latest_id = cursor.fetchall()[0][0]
				cursor.close()
				db.close()

				global latest_alarm_id

				if current_latest_id > latest_alarm_id:
					
					latest_alarm_id = current_latest_id
					new_alarms = True

				else:
					latest_alarm_id=latest_alarm_id
					new_alarms = False

			except:
				new_alarms = False

			yield 'data: {0}\n\n'.format(new_alarms)
			time.sleep(refresh_time)

	return Response(check_new_alarms(), mimetype='text/event-stream')



# data=============================================================

# ----images--------------

@app.route("/_clear_image", methods=['POST'])
@login_required
def clear_image():


	try:
		db, cursor = db_connection.connect()

		imageid = request.form['imageid']
		imagename = request.form['imagename']

		
		sql = "delete from images where image_id="+str(imageid)

		
		cursor.execute(sql)
		db.commit()

		cursor.close()
		db.close()

		# delete file form storage
		image_location = "/home/pi/heap/heap/static/img/"+imagename
		os.remove(image_location)

		return jsonify({'status': True})

	except Exception as e:
		# print "Error: ", e
		return jsonify({'status': False})



@app.route("/_take_image", methods=['POST'])
@login_required
def take_image():

	result = subprocess.check_output('/home/pi/heap/venv/bin/python /home/pi/heap/heap/image_capture_subprocess.py', shell=True)

	if 'True' in result:
		return jsonify({'newImage': True})

	else:
		return jsonify({'newImage': False})


@app.route("/_take_image_only", methods=['POST'])
@login_required
def take_image_only():

	result = subprocess.check_output('/home/pi/heap/venv/bin/python /home/pi/heap/heap/image_only_capture_subprocess.py', shell=True)

	if 'True' in result:
		return jsonify({'newImage': True})

	else:
		return jsonify({'newImage': False})



@app.route("/data/additionalsensors/")
@login_required
def data_additionalsensors():
	return render_template("data_sensors.html")


@app.route("/data/images/")
@login_required
def data_images():

	db_connection = DBConnect()
	db, cursor = db_connection.connect()

	sql = "select image_id, image_name, image_date, ndvi from images ORDER BY image_date DESC"

	cursor.execute(sql)
	results = cursor.fetchall()
	
	images=[]

	for row in results:
		image_id, image_name, image_data, ndvi = row

		images.append([image_id, image_name, image_data])


	cursor.close()
	db.close()

	return render_template("data_images.html", 
		alarmcount=cnt_alarms(),
		images=images)


@app.route("/data/trends/")
@login_required
def data_trends():
	db_connection = DBConnect()
	db, cursor = db_connection.connect()

	sql = "select temperature, humidity, light, (UNIX_TIMESTAMP(data_date)*1000)-14400000 from trough_parameters"

	cursor.execute(sql)
	results = cursor.fetchall()
	temperature_data = []
	humidity_data = []
	light_data = []

	for row in results:
		temperature, humidity, light, data_date = row
		data_date=float(data_date)
		# # print temperature, humidity, light, data_date
		temperature_row = [data_date, temperature]
		humidity_row = [data_date, humidity]
		light_row = [data_date, light]
		
		temperature_data.append(temperature_row)
		humidity_data.append(humidity_row)
		light_data.append(light_row)

	sql = "select trough_1, trough_2, trough_3, trough_4, trough_5, (UNIX_TIMESTAMP(data_date)*1000)-14400000 from trough_levels"
	cursor.execute(sql)
	levels = cursor.fetchall()
	trough_1_data = []
	trough_2_data = []
	trough_3_data = []
	trough_4_data = []
	trough_5_data = []

	

	for row in levels:
		trough_1, trough_2, trough_3, trough_4, trough_5, data_date = row
		data_date=float(data_date)
		# # print temperature, humidity, light, data_date
		trough_1_row = [data_date, trough_1]
		trough_2_row = [data_date, trough_2]
		trough_3_row = [data_date, trough_3]
		trough_4_row = [data_date, trough_4]
		trough_5_row = [data_date, trough_5]
		
		trough_1_data.append(trough_1_row)
		trough_2_data.append(trough_2_row)
		trough_3_data.append(trough_3_row)
		trough_4_data.append(trough_4_row)
		trough_5_data.append(trough_5_row)

	sql = "select ndvi, (UNIX_TIMESTAMP(image_date)*1000)-14400000 from images where data_point = 1"

	cursor.execute(sql)
	ndvi = cursor.fetchall()

	trough_1_ndvi = []
	trough_2_ndvi = []
	trough_3_ndvi = []
	trough_4_ndvi = []
	trough_5_ndvi = []

	for row in ndvi:
		trough_all_ndvi, data_date = row

		data_date=float(data_date)

		trough_1, trough_2, trough_3,trough_4,trough_5 = [float(x) for x in trough_all_ndvi.split(',')]

		trough_1_row = [data_date, trough_1]
		trough_2_row = [data_date, trough_2]
		trough_3_row = [data_date, trough_3]
		trough_4_row = [data_date, trough_4]
		trough_5_row = [data_date, trough_5]
		
		trough_1_ndvi.append(trough_1_row)
		trough_2_ndvi.append(trough_2_row)
		trough_3_ndvi.append(trough_3_row)
		trough_4_ndvi.append(trough_4_row)
		trough_5_ndvi.append(trough_5_row)


	# ---------------------------------------

	# get dosing logs =======================

	sql = "select trough, sum(volume) as volume, (UNIX_TIMESTAMP(date)*1000)-14400000 from doselogs group by trough, date order by date, trough"
	cursor.execute(sql)
	logs = cursor.fetchall()
	trough_1_dose_data = []
	trough_2_dose_data = []
	trough_3_dose_data = []
	trough_4_dose_data = []
	trough_5_dose_data = []

		for row in logs:
		trough, volume, date = row

		date=float(date)

		if trough=='trough_1':
			trough_1_dose_data.append([date, int(volume)])

		elif trough=='trough_2':
			trough_2_dose_data.append([date, int(volume)])

		elif trough=='trough_3':
			trough_3_dose_data.append([date, int(volume)])

		elif trough=='trough_4':
			trough_4_dose_data.append([date, int(volume)])

		else:
			trough_5_dose_data.append([date, int(volume)])


	#-----------------------------------------


	cursor.close()
	db.close()

	# sort data for highcharts
	temperature_data.sort(key=operator.itemgetter(0))
	humidity_data.sort(key=operator.itemgetter(0))
	light_data.sort(key=operator.itemgetter(0))  
	trough_1_data.sort(key=operator.itemgetter(0))
	trough_2_data.sort(key=operator.itemgetter(0))
	trough_3_data.sort(key=operator.itemgetter(0))
	trough_4_data.sort(key=operator.itemgetter(0))
	trough_5_data.sort(key=operator.itemgetter(0))
	trough_1_ndvi.sort(key=operator.itemgetter(0))
	trough_2_ndvi.sort(key=operator.itemgetter(0))
	trough_3_ndvi.sort(key=operator.itemgetter(0))
	trough_4_ndvi.sort(key=operator.itemgetter(0))
	trough_5_ndvi.sort(key=operator.itemgetter(0))
	trough_1_dose_data.sort(key=operator.itemgetter(0))
	trough_2_dose_data.sort(key=operator.itemgetter(0))
	trough_3_dose_data.sort(key=operator.itemgetter(0))
	trough_4_dose_data.sort(key=operator.itemgetter(0))
	trough_5_dose_data.sort(key=operator.itemgetter(0))


	return render_template("data_trends.html", 
		alarmcount=cnt_alarms(),
		temperature_data=temperature_data,
		humidity_data=humidity_data,
		light_data=light_data,
		trough_1_data=trough_1_data,
		trough_2_data=trough_2_data,
		trough_3_data=trough_3_data,
		trough_4_data=trough_4_data,
		trough_5_data=trough_5_data,
		trough_1_ndvi=trough_1_ndvi,
		trough_2_ndvi=trough_2_ndvi,
		trough_3_ndvi=trough_3_ndvi,
		trough_4_ndvi=trough_4_ndvi,
		trough_5_ndvi=trough_5_ndvi,
		trough_1_dose_data=trough_1_dose_data,
		trough_2_dose_data=trough_2_dose_data,
		trough_3_dose_data=trough_3_dose_data,
		trough_4_dose_data=trough_4_dose_data,
		trough_5_dose_data=trough_5_dose_data)

# /data===================================================

# settings =========================================================
def get_trough_data(trough):

	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]
	cm_list= ['threshold', 'maxlevel', 'sensor_height', 'length', 'radius']

	sql_trough = "select * from "+trough+" where parameter in ('n','p','k','mn', 'sman', 'water','threshold', 'maxlevel', 'sensor_height', 'length', 'radius')  order by field (parameter, 'n','p','k','mn', 'sman', 'water','threshold', 'maxlevel', 'sensor_height', 'length', 'radius');"

	cm2_list = []

	cursor.execute(sql_trough)
	results = cursor.fetchall()

	for row in results:
		parameter, value = row

		value = ('%f' %value).rstrip('0').rstrip('.')

		display_name = display_names[parameter]
		if parameter in cm_list:
			dimension = 'cm'
		elif parameter in cm2_list:
			dimension = 'cm2'
		else: dimension = ''
		temp.append([trough, display_name, parameter, value, dimension])

	cursor.close()
	db.close()

	return temp

def get_trough_states():

	states={}

	if flask_heap.get_heapdata('trough_1', 'state') == 1:
		states['trough_1'] = 'on'
	else:
		states['trough_1'] = 'off' 

	if flask_heap.get_heapdata('trough_2', 'state') == 1:
		states['trough_2'] = 'on'
	else:
		states['trough_2'] = 'off' 

	if flask_heap.get_heapdata('trough_3', 'state') == 1:
		states['trough_3'] = 'on'
	else:
		states['trough_3'] = 'off' 

	if flask_heap.get_heapdata('trough_4', 'state') == 1:
		states['trough_4'] = 'on'
	else:
		states['trough_4'] = 'off' 

	if flask_heap.get_heapdata('trough_5', 'state') == 1:
		states['trough_5'] = 'on'
	else:
		states['trough_5'] = 'off' 

	return states


def get_tank_data(tank):

	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]
	
	sql_tank = "select * from "+tank+" where parameter in ('sensor_height','base_radius','top_radius')  order by field (parameter,  'sensor_height','base_radius','top_radius');"

	cursor.execute(sql_tank)
	results = cursor.fetchall()

	for row in results:
		parameter, value = row
		display_name = display_names[parameter]

		value = ('%f' %value).rstrip('0').rstrip('.')
		
		temp.append([tank, display_name, parameter, value, 'cm'])

	cursor.close()
	db.close()

	return temp


def get_mixing_tank_data():

	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]

	sql_mixing_tank = "select * from tank_mixing where parameter in ('sensor_height','base_area', 'kp', 'dt')  order by field (parameter,  'sensor_height','base_area', 'kp', 'dt');"
	
	cursor.execute(sql_mixing_tank)
	results = cursor.fetchall()

	for row in results:
		parameter, value = row

		value = ('%f' %value).rstrip('0').rstrip('.')

		display_name = display_names[parameter]
		if parameter == 'base_area':
			temp.append(['tank_mixing', display_name, parameter, value, 'cm2'])
		elif parameter == 'sensor_height':
			temp.append(['tank_mixing', display_name, parameter, value, 'cm'])
		else:
			temp.append(['tank_mixing', display_name, parameter, value, ''])

	cursor.close()
	db.close()

	return temp


def get_pump_data(tank):

	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]

	sql_pump = "select * from "+tank+" where parameter in ('flow_min')  order by field (parameter,  'flow_min');"
	
	cursor.execute(sql_pump)
	results = cursor.fetchall()

	for row in results:
		parameter, value = row
		value = ('%f' %value).rstrip('0').rstrip('.')
		display_name = display_names[parameter]

		voltage_list = ['pump_supply_voltage', 'pump_min_voltage', 'pump_max_voltage']


		if parameter in voltage_list:
			temp.append([tank, display_name, parameter, value, 'v'])
		elif parameter == 'pump_gradient':
			temp.append([tank, display_name, parameter, value, 'mlsv'])
			# ml per second per volt
		elif parameter == 'pump_intercept':
			temp.append([tank, display_name, parameter, value, 'mls'])
		elif parameter == 'flow_min':
			temp.append([tank, display_name, parameter, value, 'mls'])
			#ml per second


	cursor.close()
	db.close()

	return temp


def get_schedule_data():

	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]

	sql_mixing_tank = "select * from schedules where parameter in ('level_schedule','ambient_schedule', 'camera_schedule', 'camera_schedule_no_ndvi', 'analog0', 'analog1', 'analog2', 'analog3', 'analog4', 'analog5', 'analog6', 'analog7')  order by field (parameter,  'level_schedule','ambient_schedule', 'camera_schedule', 'camera_schedule_no_ndvi', 'analog0', 'analog1', 'analog2', 'analog3', 'analog4', 'analog5', 'analog6', 'analog7');"
	
	cursor.execute(sql_mixing_tank)
	results = cursor.fetchall()

	for row in results:
		parameter, value = row
		if value == 'disabled':
			value = 'Disabled'
		elif value == '0 */6 * * *':
			value = 'Every 6 Hours'
		elif value == '0 */12 * * *':
			value = 'Every 12 Hours'
		elif value == '0 9 * * *':
			value = 'Every Day at 9am'
		elif value == '0 9 * * 1':
			value = 'Every Monday at 9am'
		else:
			value = value
		display_name = display_names[parameter]
		temp.append(['schedules', display_name, parameter, value, 'time'])

	cursor.close()
	db.close()

	return temp

def get_alarm_data():

	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]

	sql_mixing_tank = "select * from alarm_settings"
	
	cursor.execute(sql_mixing_tank)
	results = cursor.fetchall()

	for row in results:
		parameter, value = row
		display_name = display_names[parameter]
		temp.append(['alarm_settings', display_name, parameter, value, 'email'])

	cursor.close()
	db.close()

	return temp

def get_users():
	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	temp=[]

	sql_users = "select username, password from users  where admin='0' order by user_id desc"
	
	cursor.execute(sql_users)
	results = cursor.fetchall()

	for row in results:
		user, password = row
		temp.append([user,password])

	cursor.close()
	db.close()

	return temp



def cron_validator(cron):
	cron = cron.split(' ')
	cron_new = []
	# print cron
	if len(cron) != 5:
		return False
	else:
		for t in cron:
			cron_new.append(t.strip('*/'))
			# t.replace("*/", "")
		cron = cron_new

		if cron[0]!='':
			if int(cron[0]) > 59 or int(cron[0]) < 0:
				return False

		if cron[1] != '':
			if int(cron[1]) > 23 or int(cron[0]) < 0:
				return False

		if cron[2] != '':
			if int(cron[2]) > 31 or int(cron[0]) < 1:
				return False

		if cron[3] != '':
			if int(cron[3]) > 12 or int(cron[0]) < 1:
				return False

		if cron[4] != '':
			if int(cron[4]) > 6 or int(cron[4]) < 0:
				return False

	return True

@app.route("/settings/")
@admin_required
def settings():
	db_connection = DBConnect()
	db, cursor = db_connection.connect()
	
	trough_1 = get_trough_data('trough_1')
	trough_2 = get_trough_data('trough_2')
	trough_3 = get_trough_data('trough_3')
	trough_4 = get_trough_data('trough_4')
	trough_5 = get_trough_data('trough_5')
	trough_states = get_trough_states()

	tank_6 = get_tank_data('tank_6')
	tank_7 = get_tank_data('tank_7')
	tank_8 = get_tank_data('tank_8')
	tank_9 = get_tank_data('tank_9')
	tank_10 = get_tank_data('tank_10')
	tank_water = get_tank_data('tank_water')
	tank_mixing = get_mixing_tank_data()

	pump_6 = get_pump_data('tank_6')
	pump_7 = get_pump_data('tank_7')
	pump_8 = get_pump_data('tank_8')
	pump_9 = get_pump_data('tank_9')
	pump_10 = get_pump_data('tank_10')

	schedule = get_schedule_data()
	alarms = get_alarm_data()

	users = get_users()
	
	cursor.close()
	db.close()

	return render_template("settings.html",
						   alarmcount=cnt_alarms(),
						   trough_1 = trough_1,
						   trough_2 = trough_2,
						   trough_3 = trough_3,
						   trough_4 = trough_4,
						   trough_5 = trough_5,
						   tank_6=tank_6,
						   tank_7=tank_7,
						   tank_8=tank_8,
						   tank_9=tank_9,
						   tank_10=tank_10,
						   tank_water=tank_water,
						   tank_mixing=tank_mixing,
						   pump_6=pump_6,
						   pump_7=pump_7,
						   pump_8=pump_8,
						   pump_9=pump_9,
						   pump_10=pump_10,
						   schedule=schedule,
						   alarms=alarms,
						   users=users,
						   trough_states=trough_states)



# endpoint to take image??
@app.route("/_edit_table", methods=['POST'])
@admin_required
def edit_table():

	newValue = request.form['newValue']
	table = request.form['table']
	record = request.form['record']
	dimension = request.form['dimension']

	non_nums = ['time', 'email']

	if dimension not in non_nums:
		try:
			x = float(newValue) + 1

			flask_heap.set_heapdata(table, record, newValue)
			return jsonify({
				'status': True,
				'newValue': newValue})

		except Exception as e:
			# print e
			message = "Invalid Entry!"
			return jsonify({
				'status': False,
				'message': message})


	elif dimension=='email':
		emails = newValue.replace(' ','').split(',')

		if len(emails) != len(set(emails)):
			newValue = ",".join(list(set(emails)))
			flask_heap.set_heapdata("alarm_settings", record, "'"+newValue+"'")
			message = "Repeated Emails Removed!"
			return jsonify({
				'status': 'warning',
				'message': message,
				'newValue': newValue})

		for e in emails:
			if validate_email(e) == False:
				message = "Invalid Entry!"
				return jsonify({
					'status': False,
					'message': message})

		flask_heap.set_heapdata("alarm_settings", record, "'"+newValue+"'")
		return jsonify({
			'status': True,
			'newValue': newValue})

	
	elif dimension=='time':

		if newValue == 'disabled':
			flask_heap.set_heapdata("schedules", record, "'"+newValue+"'")
			os.system('sudo /home/pi/heap/venv/bin/python update_root_cron.py')
			newValue = 'Disabled'

		elif newValue == '0 */6 * * *':
			flask_heap.set_heapdata("schedules", record, "'"+newValue+"'")
			os.system('sudo /home/pi/heap/venv/bin/python update_root_cron.py')
			newValue = 'Every 6 Hours'

		elif newValue == '0 */12 * * *':
			flask_heap.set_heapdata("schedules", record, "'"+newValue+"'")
			os.system('sudo /home/pi/heap/venv/bin/python update_root_cron.py')
			newValue = 'Every 12 Hours'

		elif newValue == '0 9 * * *':
			flask_heap.set_heapdata("schedules", record, "'"+newValue+"'")
			os.system('sudo /home/pi/heap/venv/bin/python update_root_cron.py')
			newValue = 'Every Day at 9am'

		elif newValue == '0 9 * * 1':
			flask_heap.set_heapdata("schedules", record, "'"+newValue+"'")
			os.system('sudo /home/pi/heap/venv/bin/python update_root_cron.py')
			newValue = 'Every Monday at 9am'
		else:
			cron_is_valid = cron_validator(newValue)
			if cron_is_valid == False:
				message = "Invalid Entry!"
				return jsonify({
					'status': False,
					'message': message})
			else:
				flask_heap.set_heapdata("schedules", record, "'"+newValue+"'")
				os.system('sudo /home/pi/heap/venv/bin/python update_root_cron.py')
				return jsonify({
					'status': True,
					'newValue': newValue})

		return jsonify({
			'status': True,
			'newValue': newValue})
	
	else: return jsonify({'newValue': newValue})


# data delete ================
@app.route("/_delete_data", methods=['POST'])
@admin_required
def delete_data():
	table = request.form['table']
	drange = request.form['drange']

	t1 = drange[:19]
	t2 = drange[-19:]

	try:
		db_connection = DBConnect()
		db, cursor = db_connection.connect()

		if table == 'logs':
			col = 'alarm_date'
			table = 'alarms'
			sql = "delete from "+table+" where "+col+" between '"+t1+"' and '"+t2+"' and alarm_status=0"

		elif table == 'levels':
			col = 'data_date'
			table = 'trough_levels'
			sql = "delete from "+table+" where "+col+" between '"+t1+"' and '"+t2+"'"

		elif table == 'doselogs':
			col = 'date'
			table = 'doselogs'
			sql = "delete from "+table+" where "+col+" between '"+t1+"' and '"+t2+"'"

		else:
			col = 'data_date'
			table = 'trough_parameters'
			sql = "delete from "+table+" where "+col+" between '"+t1+"' and '"+t2+"'"
		
		cursor.execute(sql)
		db.commit()
		
		cursor.close()
		db.close()

		return jsonify({'status': True})

	except:
		return jsonify({'status': False})


# users ================
@app.route("/_delete_user", methods=['POST'])
@admin_required
def delete_user():
	username = request.form['username']
	try:
		db_connection = DBConnect()
		db, cursor = db_connection.connect()

		sql = "delete from users where username = '"+username+"'"
		
		cursor.execute(sql)
		db.commit()
		
		cursor.close()
		db.close()

		return jsonify({'status': True})

	except:
		return jsonify({'status': False})


@app.route("/_create_user", methods=['POST'])
@admin_required
def create_user():
	username = request.form['username']
	password = request.form['password']

	if username=='' or password=='' or len(username.split(' '))>1 or len(password.split(' '))>1:
		return jsonify({
			'status': False,
			'message':'Invalid Input!'})

	else:
		try:
			db_connection = DBConnect()
			db, cursor = db_connection.connect()

			sql = "insert into users (username, password, admin)  values ('"+username+"', '"+password+"', 0)"
			
			cursor.execute(sql)
			db.commit()
			
			cursor.close()
			db.close()

			return jsonify({'status': True})

		except Exception as e:
			if "Duplicate" in str(e[1]):
				return jsonify({
					'status': False,
					'message':'User already exists!'})
			
			return jsonify({
				'status': False,
				'message':'Database Error!'})


@app.route("/login", methods=['GET', 'POST'])
def login():
	if 'logged_in' not in session:
		if request.method == "POST":
			try:
				session.permanent = True

				username = request.form['username']
				password = request.form['password']

				db_connection = DBConnect()
				db, cursor = db_connection.connect()

				sql = "select * from users where binary username='"+username+"'"

				result = cursor.execute(sql)

				if int(result)==0:
					return jsonify({'status': False})

				else:
					result = cursor.fetchone()
					db_username = result[1]
					db_password= result[2]
					db_admin = result[3]

					if int(db_admin)==1:
						# check hased password
						pwmatch = sha256_crypt.verify(password, db_password)
						if pwmatch == False:
							return jsonify({'status': False})
						else:
							session['logged_in'] = True
							session['username'] = username
							session['admin'] = True
							return jsonify({'status': True})

					else:
						if password != db_password:
							return jsonify({'status': False})
						else:
							session['logged_in'] = True
							session['username'] = username
							return jsonify({'status': True})

				cursor.close()
				db.close()

			except Exception as e:
				return render_template("login.html")


		return render_template("login.html")

	else:
		return redirect(url_for('index'))


@app.route("/logout")
def logout():
	# drop session
	session.clear()
	return redirect(url_for('login'))

@app.route("/_get_user_info", methods=['POST'])
@admin_required
def get_user_info():

	username = request.form['username']
	alarms=[]
	try:

		db_connection = DBConnect()
		db, cursor = db_connection.connect()

		sql = "select alarm_id from alarms where user = '"+username+"'"
		cursor.execute(sql)
		results = cursor.fetchall()

		for row in results:
			alarm_id = str(row[0])
			alarms.append(alarm_id)

		cursor.close()
		db.close()

		return jsonify({
			'status': True,
			'user_info_alarms': alarms})

	except Exception as e:
		return jsonify({'status': False})


@app.route("/_test_dosing_pump", methods=['POST'])
@admin_required
def test_dosing_pump():

	tank = request.form['tank']
	flask_heap.time_dose(tank, 10)
	return jsonify({'status': True})

start = 0
end = 0

@app.route("/_calibrate_pump", methods=['POST'])
@admin_required
def calibrate_pump():
	try:

		pump = request.form['pump']
		if pump=='pump_10':
			tank = "tank_"+pump[-2:]
		else:
			tank = "tank_"+pump[-1:]
		stage = request.form['stage']

		global start, end

		pump_pin = int(flask_heap.get_heapdata(tank,"pump_pin"))

		if stage=='1':
			flask_heap.turn_on_gpio(pump_pin)
			start = time.time()
			return jsonify({
				'status': True,
				'stage': '1'})

		elif stage=='2':
			flask_heap.turn_off_gpio(pump_pin)
			end = time.time()
			operating_flow = round(float(50)/float(end-start),2)
			flask_heap.set_heapdata(tank, 'operating_flow', str(operating_flow))
			return jsonify({
				'status': True,
				'stage': '2'})

	except Exception as e:
		print 'error: ', e
		return jsonify({
			'status': False,
			'message': 'Calibration Failed!'})


@app.route("/_troubleshoot", methods=['POST'])
@admin_required
def troubleshoot():

	try:
		device = request.form['device']
		command = '/home/pi/heap/venv/bin/python /home/pi/heap/heap/troubleshoot.py '+str(device)
		os.system(command)

		return jsonify({'status': True})

	except:

		return jsonify({'status': False})


#========NDVI Calc====================================

@app.route('/ndvicalc/', methods = ['GET', 'POST'])
@login_required
def ndvicalc():
	try:
		if request.method == 'POST' and 'photo' in request.files:
			
			filename = photos.save(request.files['photo'])
			image_location = '/home/pi/heap/heap/static/img/'+filename
			ndvi = flask_ndvi.getNDVIHMI(image_location)
			ndvi = 'NDVI = '+str(ndvi)
			os.system('rm -rf /home/pi/heap/heap/static/img/'+filename)
			return render_template("ndvicalc.html", ndvi=ndvi) 
		else:
			return render_template("ndvicalc.html", ndvi='')

	except:
		return render_template("ndvicalc.html", ndvi='Error!')


# testing ==================================================

@app.route('/test')
def test():
	return render_template("test.html")

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=5000, debug=True,  threaded=True)

