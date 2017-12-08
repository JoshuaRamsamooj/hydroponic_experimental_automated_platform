import RPi.GPIO as GPIO
import Adafruit_DHT as dht
from MCP23S17 import MCP23S17
from tsl2561 import TSL2561
import time
import random
import json
import numpy as nm
from db_connect import DBConnect
from picamera import PiCamera
from alarms import Alarm
from ndvi import NDVI
import os
import datetime
import math
import cv2


relay_names_dict = {
    5: "valve_1",
    6: "valve_2",
    13: "valve_3",
    19: "valve_4",
    26: "valve_5",
    12: "valve_drain",
    16: "pump_mixing",
    20: "",
    21: "pump_air",
}

class Heap(object):

    def __init__(self, inputs=[], outputs=[5,6,13,19,26,21,20,16,12,22,15,18,23,24,25]):  # !!!!!!!! set in out

        self.heap_db_connection = DBConnect()
        self.heap_alarm = Alarm()
        self.heap_ndvi = NDVI()

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(inputs,GPIO.IN)
        GPIO.setup(outputs,GPIO.OUT)
        GPIO.setwarnings(False)

        #relay chip
        self.mcp2 = MCP23S17(0,0,2)
        self.mcp2.setPortA_dir( 0b11111111 )
        self.mcp2.setPortB_dir( 0b11111111 )

        #trough chip
        self.mcp1 = MCP23S17(0,0,1)
        self.mcp1.setPortA_dir( 0b10101010 )
        self.mcp1.setPortB_dir( 0b10101010 )

        #tank chip
        self.mcp0 = MCP23S17(0,0,0)
        self.mcp0.setPortA_dir( 0b10101010 )
        self.mcp0.setPortB_dir( 0b10101010 )



    def sep_ports(self, ports):
        # seperate list into diff ports
        port_a = [a for a in ports if 0 <= a <= 7]
        port_b = [a-8 for a in ports if 8 <= a <= 15]

        return port_a, port_b


    def get_heapdata(self, table, parameter):
        db, cursor = self.heap_db_connection.connect()
        sql = "select value from "+table+" where parameter='"+parameter+"'"
        
        while True:
            try:
                # access db                
                # look for value of parameter in table   
                cursor.execute(sql)
                result = cursor.fetchall()[0][0]   
                break

            except:
                # Rollback in case there is any error
                db.rollback()

        cursor.close()
        db.close()

        return result

    def set_heapdata(self, table, parameter, value):
        # pass string for number and string in quotes for string
        db, cursor = self.heap_db_connection.connect()
        sql = "update "+table+" set value="+value+" where parameter='"+parameter+"'"
                
        while True:
            try:
                cursor.execute(sql)
                # Commit your changes in the database
                db.commit()
                break

            except:
                # Rollback in case there is any error
                db.rollback()

        
        cursor.close()
        db.close()




    def turn_on_relays(self, relays): # pass in [] if pin numbers (0 through 15; porta to portb)
        # relays are on mcp chip 2
        relays = [int(x) for x in relays]

        for relay in relays:
            name = relay_names_dict[relay]
            if relay == 20:
                self.turn_off_gpio(relay)
            else:
                self.set_heapdata('equipment_status', name, "'ON'")
                self.turn_off_gpio(relay)


    def turn_off_relays(self, relays): 

        relays = [int(x) for x in relays]

        for relay in relays:
            # gpio.high
            name = relay_names_dict[relay]
            if relay == 20:
                self.turn_on_gpio(relay)
                # GPIO.output(relay, GPIO.HIGH)
            else:
                self.set_heapdata('equipment_status', name, "'OFF'")
                self.turn_on_gpio(relay)
                # GPIO.output(relay, GPIO.HIGH)


    # ---------------- /relay control -----------------------------------------------------------------

    # ---------------- pump control -------------------------------------------------------------------

    def start_pump(self, pin, speed, freq=1000):
        self.pump = GPIO.PWM(pin, freq)
        self.pump.start(speed)


    def change_pump_speed(self, speed):
        self.pump.ChangeDutyCycle(speed)


    def stop_pump(self):
        self.pump.stop()


    def get_pwm(self, old_value, old_min, old_max): 
        new_value = (float(((old_value - old_min) * 100)) / float((old_max - old_min)))
        if new_value >= 100:
            return 100
        elif new_value <= 50:
            return 50
        else:
            return int(new_value)

    def p_controller(self, water_height):

        water_height = round(water_height,1)
        reference = 0
        setpoint = water_height + reference
        error = setpoint - reference

        kp= float(self.get_heapdata("tank_mixing","kp"))

        # start pump
        pwm = 100
        self.start_pump(int(self.get_heapdata("tank_water","pump_pin")), pwm)

        # update value on hmi
        self.set_heapdata('equipment_status', 'pump_water', "'"+str(pwm)+"%'")

        time.sleep(float(self.get_heapdata("tank_mixing","dt"))) # dead time

        timeout = time.time() + 60*5 #5 mins

        while error > 0:
            controller_output = error * kp
            pwm = self.get_pwm(controller_output, reference, setpoint)
            self.change_pump_speed(pwm)

            pump_flow = self.get_flow(int(self.get_heapdata("tank_water","flow_pin")))
            
            if pump_flow is False:
                self.stop_pump()
                self.set_heapdata('equipment_status', 'pump_water', "'0%'")
                return [False, 1]

            # update value on hmi
            self.set_heapdata('equipment_status', 'pump_water', "'"+str(pwm)+"%'")
            

            mixing_tank_level = self.get_level_mixing_tank("tank_mixing")[0]

            if mixing_tank_level is False or time.time()>timeout:
                self.stop_pump()
                self.set_heapdata('equipment_status', 'pump_water', "'0%'")
                return [False, 0]
            

            error = setpoint - mixing_tank_level
            # time.sleep(0.5)
            time.sleep(0.1)
            print "check ", pwm, error

        self.stop_pump()
        self.set_heapdata('equipment_status', 'pump_water', "'0%'")

        return [True, True]

  


    def time_dose(self, tank, ml_required):

        if tank=='tank_10':
            pump = "pump_"+tank[-2:]
        else:
            pump = "pump_"+tank[-1:]

        operating_flow = self.get_heapdata(tank,"operating_flow")
        pump_pin = int(self.get_heapdata(tank,"pump_pin"))
        min_flow = self.get_heapdata(tank,"flow_min") # ml/sec

        time_to_run = float(ml_required)/float(operating_flow)

        if operating_flow >= min_flow:
        
            self.turn_on_gpio(pump_pin)

            t1 = time.time()

            self.set_heapdata('equipment_status', pump, "'100%'")
        
            loop_time = t1+time_to_run
            while time.time() < loop_time:

                pump_flow = self.get_flow(flow_pin)

                if pump_flow is False:
                    return False

            self.turn_off_gpio(pump_pin)
            self.set_heapdata('equipment_status', pump, "'0%'")

            return True

        else:
            # flow to low to check for alarms here
            self.turn_on_gpio(pump_pin)
            t1 = time.time()

            self.set_heapdata('equipment_status', pump, "'100%'")

            te = time.time() - t1

            time_to_run = time_to_run - te

            if time_to_run <= 0:
                time_to_run = 0
            else:
                time_to_run = time_to_run

            time.sleep(time_to_run)
            self.turn_off_gpio(pump_pin)
            #set hmi % on here for the pump
            self.set_heapdata('equipment_status', pump, "'0%'")

            return True


    # ---------------- /pump control -------------------------------------------------------------------


    # ---------------- gpio control --------------------------------------------------------------------

    def turn_on_gpio(self, gpio):
        GPIO.output(gpio, GPIO.HIGH)


    def turn_off_gpio(self, gpio):
        GPIO.output(gpio, GPIO.LOW)

    # ---------------- /gpio control -------------------------------------------------------------------



    # ---------------- sensors -------------------------------------------------------------------------

    def get_humidity_temperature(self):
        try:
            t = float(self.get_heapdata('equipment_status', 'temperature')[:-2])
            h = float(self.get_heapdata('equipment_status', 'humidity')[:-2])

            return h,t

        except:
            return 0,0



    def get_light(self):
        try:
            light = int(self.get_heapdata('equipment_status', 'light')[:-4])
            return light
        except:
            return 0

    def get_data(self):
    
        try:
            h2,t2 = dht.read_retry(dht.AM2302, 27)
            h1,t1=h2,t2
             
            while abs(h2)>100 or abs(t2)>40:

                h2,t2 = dht.read_retry(dht.AM2302, 27)
                h1,t1=h2,t2

            h = (h1+h2)/2
            t = (t1+t2)/2

            h = round(h,1)
            t = round(t,1)

        except:
            h = 0
            t = 0

        self.set_heapdata('equipment_status', 'temperature', "'"+str(t)+" C'")
        self.set_heapdata('equipment_status', 'humidity', "'"+str(h)+" %'")

        try:
            tsl1 = TSL2561(0x39)
            tsl2 = TSL2561(0x29)

            light = int(0.5*float((tsl1.lux()+tsl2.lux())))
        except:
            light = 0

        self.set_heapdata('equipment_status', 'light', "'"+str(light)+" lux'")

        return h,t, light

    




    def get_info(self, sensorid):

        if sensorid=="trough_1": # N - deficient
            trig = 0
            echo = 1
            chip = self.mcp1
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="trough_2": # P- deficient
            trig = 2
            echo = 3
            chip = self.mcp1
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="trough_3": # K - deficient
            trig = 4
            echo = 5
            chip = self.mcp1
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="trough_4": # Full
            trig = 6
            echo = 7
            chip = self.mcp1
            height = self.get_heapdata(sensorid, "sensor_height")
        if sensorid=="trough_5": # water
            trig = 8
            echo = 9
            chip = self.mcp1
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_6": # N tank
            trig = 0
            echo = 1
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_7": # P tank
            trig = 2
            echo = 3
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_8": # K - tank
            trig = 4
            echo = 5
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_9": # micro nutrients - a
            trig = 6
            echo = 7
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_10": # micro - nutriends - b
            trig = 8
            echo = 9
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_mixing": # mixing tank
            trig = 10
            echo = 11
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")

        if sensorid=="tank_water": # water tank
            trig = 12
            echo = 13
            chip = self.mcp0
            height = self.get_heapdata(sensorid, "sensor_height")
        


        return trig, echo, chip, height

    def get_height(self, trig, echo, chip, height):

        t_timeout = time.time() + 1

        chip.setPort(trig,0)
        time.sleep(0.02)
        chip.setPort(trig,1)
        time.sleep(0.00001)
        chip.setPort(trig,0)

        while chip.getPort(echo) == False:
            if time.time() > t_timeout: 
                print 'fail 1'
                return False, False

        send = time.time()

        while chip.getPort(echo):
            if time.time() > t_timeout: 
                print 'fail 2'
                return False, False

        ret = time.time()
        distance = 0.5*340*100*(ret-send)
        level = height - round(distance,1)
        return round(level,1), round(distance,1)

    def reject_outliers(self, data):
        m = 0.9
        u = nm.mean(data)
        s = nm.std(data)
        filtered = [e for e in data if (u - m * s < e < u + m * s)]
        return filtered


    def get_level_mixing_tank(self, sensorid):

        trig, echo, chip, height = self.get_info(sensorid)
        
        # level, distance = self.get_height(trig, echo, chip, height)
        try_counter = 0

        while True:
            try:
                level, distance = self.get_height(trig, echo, chip, height)
                if level is False or distance is False:

                    try_counter=try_counter+1

                    if try_counter>3:
                        return False, False

                    time.sleep(0.1)

                else:
                    break

            except:
                pass


        try_counter = 0


        level = [level]
        distance = [distance]

        t = time.time() + 0.5 

        while time.time() <= t:

            while True:
                try:
                    l,d = self.get_height(trig, echo, chip, height)
                    if l is False or d is False:

                        try_counter=try_counter+1

                        if try_counter>3:
                            return False, False

                        time.sleep(0.1)

                    else:
                        break

                except:
                    pass

            level.append(l)
            distance.append(d)

        level = self.reject_outliers(level)
        distance = self.reject_outliers(distance)

        level = sum(level)/len(level)
        distance = sum(distance)/len(distance)

        #accounts for turbalances
        if level <= 0:
            level = 0
        else:
            level = round(level,2)
        
        self.set_heapdata('equipment_status', sensorid, "'"+str(round(level,1))+"cm'")

        return round(level,1), round(distance, 1)
        

    def troughs_affected(self, nutrient):

        if nutrient == 'tank_6':
            nutrient = 'n'
        elif nutrient == 'tank_7':
            nutrient = 'p'
        elif nutrient == 'tank_8':
            nutrient = 'k'
        elif nutrient == 'tank_9':
            nutrient = 'mn'
        elif nutrient == 'tank_10':
            nutrient = 'sman'
        elif nutrient == 'tank_water':
            nutrient = 'water'
        else:
            return ""
        
        affected = [1, 2, 3, 4, 5]
        for trough in range(1, 6):

            if int(self.get_heapdata("trough_"+str(trough), nutrient)) == 0:
                affected.remove(trough)

        affected = ','.join("trough_"+str(x) for x in affected)
        return affected

    def get_level(self, sensorid):

        trig, echo, chip, height = self.get_info(sensorid)

        trough_dict = {
        "trough_1":"Trough 1's",
        "trough_2":"Trough 2's",
        "trough_3":"Trough 3's",
        "trough_4":"Trough 4's",
        "trough_5":"Trough 5's",
        "tank_6":"Tank 6's",
        "tank_7":"Tank 7's",
        "tank_8":"Tank 8's",
        "tank_9":"Tank 9's",
        "tank_10":"Tank 10's",
        "tank_mixing":"Mixing Tank's",
        "tank_water":"Water Tank's"
        }
        
        try_counter = 0

        while True:
            try:
                level, distance = self.get_height(trig, echo, chip, height)
                if level is False or  distance is False:

                    try_counter=try_counter+1

                    if try_counter>3:
                        
                        alarm_description = "Failure of "+ trough_dict[sensorid]+" level sensor."
                        alarm_priority = "Medium"
                        alarm_type = "4"
                        affected_equipment = self.troughs_affected(sensorid)+", "+str(sensorid)
                        email = self.get_heapdata('alarm_settings', 'email')                        
                        self.heap_alarm.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)

                        return False, False

                    time.sleep(0.1)

                else:
                    break

            except:
                pass



        try_counter = 0


        level = [level]
        distance = [distance]

        t = time.time() + 0.5 

        while time.time() <= t:

            while True:
                try:
                    l,d = self.get_height(trig, echo, chip, height)
                    if l is False or d is False:

                        try_counter=try_counter+1

                        if try_counter>3:

                            alarm_description = "Failure of "+ trough_dict[sensorid]+" level sensor."
                            alarm_priority = "Medium"
                            alarm_type = "4"
                            affected_equipment = self.troughs_affected(sensorid)+", "+str(sensorid)
                            email = self.get_heapdata('alarm_settings', 'email')           
                            self.heap_alarm.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)

                            return False, False

                        time.sleep(0.1)

                    else:
                        break

                except:
                    pass

            level.append(l)
            distance.append(d)

  
        level = self.reject_outliers(level)
        distance = self.reject_outliers(distance)

        level = sum(level)/len(level)
        distance = sum(distance)/len(distance)

        if level <= 0:
            level = 0
        else:
            level = round(level,2)
        
        tanks = ["tank_6","tank_7","tank_8","tank_9","tank_10", "tank_water"]
        if sensorid in tanks:
            h1 = height
            h2 = level
            r1 = self.get_heapdata(sensorid, "base_radius")
            r2 = self.get_heapdata(sensorid, "top_radius")
            r3 = r2 - (float(h1*(r2-r1))/float((h1+h2)))
            ml = (nm.pi / 3) * ((r3 ** 2) + (r1 * r3) + (r1 ** 2)) * h2
            self.set_heapdata('equipment_status', sensorid, "'"+str(round(ml/1000,1))+"L'")

            return round(level), round(ml), level, round(distance, 1)

        elif sensorid == 'tank_mixing':
            self.set_heapdata('equipment_status', sensorid, "'"+str(round(level,1))+"cm'")

            return round(level,1), round(distance, 1)
        
        else: 
            self.set_heapdata('equipment_status', sensorid, "'"+str(round(level))+"cm'")

            return round(level), level, round(distance, 1)




    def get_flow(self, pin):

        check_time = time.time() + 2
        flow_state = self.mcp2.getPort(pin)

        while time.time() < check_time:

            new_flow_state = self.mcp2.getPort(pin)
            if new_flow_state != flow_state:
                return True
        
        return False                


    def get_required_volume(self, h1, h2, trough):

        
        r = self.get_heapdata(trough,"radius")
        length_of_pipe = self.get_heapdata(trough,"length")

        if h1>=h2:
            return 0

        area_of_circle = nm.pi * (r ** 2)

        theta_a = 2 * nm.arccos(float(nm.abs(r - h1)) / float(r))
        
        theta_b = 2 * nm.arccos(float(nm.abs(r - h2)) / float(r))

        area_of_a = 0.5 * (r ** 2) * (theta_a - nm.sin(theta_a))
        area_of_b = 0.5 * (r ** 2) * (theta_b - nm.sin(theta_b))

        if h1 >= r:
            area_of_a = area_of_circle - area_of_a
        else:
            area_of_a = area_of_a

        if h2 >= r:
            area_of_b = area_of_circle - area_of_b
        else:
            area_of_b = area_of_b

        required_area = area_of_b - area_of_a
        required_volume = required_area * length_of_pipe

        if required_volume<=0:
            return 0
        else:
            return required_volume 

        return required_volume


    def capture_image_only(self):

        try:
            diskSpaceToReserve = 1024 * 1024 * 1024 # Keep 1gb free on disk

            # check if there are any camera alarms
            db, cursor = self.heap_db_connection.connect()

            sql = "select affected_equipment from alarms where alarm_status = 1"
            
            cursor.execute(sql)
            data = cursor.fetchall()
            affected_equipment = []

            for d in data:
                affected_equipment += d[0].replace(' ','').split(',')

            affected_equipment = list(set(affected_equipment))  # unique affected_components

            
            if 'camera' in affected_equipment:
                return [False]

            elif self.get_free_space() < diskSpaceToReserve:

                # raise alarm saying low on memory, delete photos
                alarm_description = "Memory Low! Please delete photos to continue capturing."
                alarm_priority = "High"
                alarm_type = "4"
                affected_equipment = "camera"
                email = self.get_heapdata('alarms', 'email')
                self.heap_alarm.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)

                return [False]

            else:
                camera = PiCamera()
                camera.resolution = (1000,1000) # adjust this
                camera.start_preview()
                # Camera warm-up time
                time.sleep(2)

                # get date
                date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".jpg"
                image_location = "/home/pi/heap/heap/static/img/"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".jpg"

                camera.capture(image_location)

                sql = "insert into images (image_name, image_date, ndvi, data_point) values (%s, %s, %s, %s)"
                cursor.execute(sql, (image_name, date_time, '', '0'))
            

                db.commit()
                cursor.close()
                db.close()
                return [True, image_name]

        except Exception as e:
            print 'heap function',e
            return [False]

    def capture_image(self):

        try:
            diskSpaceToReserve = 1024 * 1024 * 1024 # Keep 1gb free on disk

            db, cursor = self.heap_db_connection.connect()

            sql = "select affected_equipment from alarms where alarm_status = 1"
            
            cursor.execute(sql)
            data = cursor.fetchall()
            affected_equipment = []

            for d in data:
                affected_equipment += d[0].replace(' ','').split(',')
                # removes spaces

            affected_equipment = list(set(affected_equipment))  # unique affected_components

            
            if 'camera' in affected_equipment:
                return [False]

            elif self.get_free_space() < diskSpaceToReserve:

                # raise alarm saying low on memory, delete photos
                alarm_description = "Memory Low! Please delete photos to continue capturing."
                alarm_priority = "High"
                alarm_type = "4"
                affected_equipment = "camera"
                email = self.get_heapdata('alarms', 'email')
                self.heap_alarm.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                

                return [False]

            else:
                camera = PiCamera()
                camera.resolution = (1000,1000) # adjust this
                camera.start_preview()
                # Camera warm-up time
                time.sleep(2)

                # get date
                date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                image_name = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".jpg"
                image_location = "/home/pi/heap/heap/static/img/"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")+".jpg"

                camera.capture(image_location)

                # put image name and date_time in db
                # ndvi = self.calcNDVI(image_location)
                ndvi = self.heap_ndvi.getNDVI(image_location)
                # ndvi = "0,0,0,0,0"

                sql = "insert into images (image_name, image_date, ndvi, data_point) values (%s, %s, %s, %s)"
                cursor.execute(sql, (image_name, date_time, ndvi, '1'))
            

                db.commit()
                cursor.close()
                db.close()
                return [True, image_name]

        except Exception as e:
            print 'heap function',e
            return [False]



    def get_free_space(self):
        st = os.statvfs(".")
        du = st.f_bavail * st.f_frsize
        return du

    def delete_image(self):
        pass
