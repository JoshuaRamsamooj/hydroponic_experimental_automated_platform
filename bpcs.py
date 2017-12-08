from db_connect import DBConnect
from alarms import Alarm
from heap import Heap
import time
import numpy as nm
import datetime

# ----objects----------
alarm1 = Alarm()
heap1 = Heap()
db_connection1 = DBConnect()

def update_status():
    try:
        db1, cursor1 = db_connection1.connect()
        sql = "select affected_equipment from alarms where alarm_status = 1"
        cursor1.execute(sql)
        data = cursor1.fetchall()
        affected_equipment = []
        for d in data:
            affected_equipment += d[0].replace(' ','').split(',')

        off_troughs = []

        if heap1.get_heapdata('trough_1', 'state') == 0:
            off_troughs.append('trough_1')

        if heap1.get_heapdata('trough_2', 'state') == 0:
            off_troughs.append('trough_2')

        if heap1.get_heapdata('trough_3', 'state') == 0:
            off_troughs.append('trough_3')

        if heap1.get_heapdata('trough_4', 'state') == 0:
            off_troughs.append('trough_4')

        if heap1.get_heapdata('trough_5', 'state') == 0:
            off_troughs.append('trough_5')


        trough_not_to_service = affected_equipment + off_troughs
        trough_not_to_service = list(set(trough_not_to_service))

        troughs_to_service = [1, 2, 3, 4, 5]

        if "trough_1" in trough_not_to_service:
            troughs_to_service.remove(1)

        if "trough_2" in trough_not_to_service:
            troughs_to_service.remove(2)

        if "trough_3" in trough_not_to_service:
            troughs_to_service.remove(3)

        if "trough_4" in trough_not_to_service:
            troughs_to_service.remove(4)

        if "trough_5" in trough_not_to_service:
            troughs_to_service.remove(5)

        cursor1.close()
        db1.close()
        return troughs_to_service
    except Exception as e:
        print e
        return []


def raise_sensor_alarm():

    alarm_description = "Failure of Mixing Tank Level Sensor. Manually Drain Contents from Mixing Tank"
    alarm_priority = "High"
    alarm_type = "4,5"
    affected_equipment = "trough_1,trough_2,trough_3,trough_4,trough_5, tank_mixing"
    email = str(heap1.get_heapdata('alarm_settings', 'email'))
    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
    

def mix(runtime): 
    mixingpump_flowmeter = int(heap1.get_heapdata("tank_mixing","flow_pin"))

    mixingpump_relay = int(heap1.get_heapdata("tank_mixing","pump_pin"))
    heap1.turn_on_relays([mixingpump_relay])

    time.sleep(2) # wait a little to ensure flow 

    finish = time.time() + runtime # runtime mins from now

    while time.time() < finish:

        mixingpump_flow = heap1.get_flow(mixingpump_flowmeter)

        if mixingpump_flow is False:

            alarm_description = "Failure of Pump P12 (Mixing Pump)"
            alarm_priority = "High"
            alarm_type = "2,4"
            affected_equipment = "trough_1,trough_2,trough_3,trough_4,trough_5, pump_mixing"
            email = heap1.get_heapdata('alarm_settings', 'email')
            alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
            
            heap1.turn_off_relays([mixingpump_relay]) 

            return False

        time.sleep(1) # wait a little to allow sensor to toggle again

    heap1.turn_off_relays([mixingpump_relay])
    return True

def dose(trough):
    trough_relay = int(heap1.get_heapdata("trough_"+str(trough),"valve_pin"))  # relay controlling valve for that trough
    heap1.turn_on_relays([trough_relay])
    
    time.sleep(1) #if valve not opening same time, use this

    height = heap1.get_level_mixing_tank("tank_mixing")[0]
    if height is False:
        raise_sensor_alarm()
        heap1.turn_off_relays([trough_relay])
        return [False, 0]

    else:
        while height >= 2:

            dose_flow = heap1.get_flow(int(heap1.get_heapdata("trough_"+str(trough),"flow_pin")))
            
            if dose_flow is False:

                alarm_description = "Failure of Valve V"+str(trough)+""
                alarm_priority = "Medium"
                alarm_type = "1,4"
                affected_equipment = "trough_"+str(trough)+","+"valve_"+str(trough)
                email = heap1.get_heapdata('alarm_settings', 'email')
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                heap1.turn_off_relays([trough_relay])
                return [False, 1]

            time.sleep(1)

            height = heap1.get_level_mixing_tank("tank_mixing")[0]
            if height is False:
                raise_sensor_alarm()
                heap1.turn_off_relays([trough_relay])
                return [False, 0]

            
    time.sleep(20) # wait for remains to drain out 
    heap1.turn_off_relays([trough_relay])
    heap1.set_heapdata('equipment_status', 'tank_mixing', "'0cm'")
    return [True, True]


def rinse():

    rinse_water = heap1.p_controller(5)

    if rinse_water[0] is False: # means there is issue with pump

        if rinse_water[1] == 0:
            # sensor fail
            heap1.set_heapdata('equipment_status', 'pump_water', "'0%'")

            alarm_description = "Failure of Mixing Tank Level Sensor. Manually Drain Contents from Mixing Tank"
            alarm_priority = "High"
            alarm_type = "4,5"
            affected_equipment = "trough_1,trough_2,trough_3,trough_4,trough_5, tank_mixing"
            email = str(heap1.get_heapdata('alarm_settings', 'email'))
            alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
  
            return False

        elif rinse_water[1] == 1:
            #pump fail

            #reset hmi value when pump fails
            heap1.set_heapdata('equipment_status', 'pump_water', "'0%'")
            print "mixing tank failed"
            # raise an alarm
            # alarm_description = "Failure of Water pump."
            alarm_description = "Failure of Pump P11 (Water Pump)."
            alarm_priority = "High"
            alarm_type = "4,5"
            affected_equipment = troughs_affected("water")+",pump_water"
            email = str(heap1.get_heapdata('alarm_settings', 'email'))
            alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
            
            drain_tank()
            # cant rinse since the water pump has failed
            return False 


    _mix = mix(30)
    if _mix is False: 
        drain_tank()
        return False 

    _drain = drain_tank()
    if _drain is False: return False

    return True 



def drain_tank():

    drain_relay = int(heap1.get_heapdata("other_equipment","drain_valve_pin"))
    heap1.turn_on_relays([drain_relay])

    time.sleep(1) # if valve not opening same time, use this

    height = heap1.get_level_mixing_tank("tank_mixing")[0]
    if height is False:
        raise_sensor_alarm()
        heap1.turn_off_relays([drain_relay])
        return [False, 0]

    else:
        while height >= 2:

            drain_flow = heap1.get_flow(int(heap1.get_heapdata('tank_mixing','flow_pin_drain'))) 
            if drain_flow is False:            
                alarm_description = "Failure of Valve V6 (Drain Valve). Manually remove contents from mixing tank."
                alarm_priority = "High"
                alarm_type = "1,4"
                affected_equipment = "trough_1,trough_2,trough_3,trough_4,trough_5,valve_drain"
                email = heap1.get_heapdata('alarm_settings', 'email')
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                heap1.turn_off_relays([drain_relay])
                return False

            time.sleep(1)

            height = heap1.get_level_mixing_tank("tank_mixing")[0]

            if height is False:
                raise_sensor_alarm()
                heap1.turn_off_relays([drain_relay])
                return [False, 0]


    time.sleep(20) # wait for remains to drain out 
    heap1.turn_off_relays([drain_relay])
    heap1.get_level_mixing_tank("tank_mixing")[0]
    heap1.set_heapdata('equipment_status', 'tank_mixing', "'0cm'")
    return True


def dose_in_sections(number_of_times_to_dose, water_height, n_req, p_req, k_req, mn_req, sman_req, trough):

    for _ in xrange(number_of_times_to_dose):
        # add water
        water_added = heap1.p_controller(water_height)

        if water_added[0] is False: # means there is issue with pump

            # check if its pump or sensor
            if water_added[1] == 0:
                heap1.set_heapdata('equipment_status', 'pump_water', "'0%'")
                print "mixing tank failed"
                alarm_description = "Failure of Mixing Tank Level Sensor. Manually Drain Contents from Mixing Tank"
                alarm_priority = "High"
                alarm_type = "4,5"
                affected_equipment = "trough_1,trough_2,trough_3,trough_4,trough_5, tank_mixing"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                return False

            elif water_added[1] == 1:
                #pump fail
                heap1.set_heapdata('equipment_status', 'pump_water', "'0%'")
                print "mixing tank failed"
                alarm_description = "Failure of Pump P11 (Water Pump)"
                alarm_priority = "High"
                alarm_type = "4,5"
                affected_equipment = troughs_affected("water")+",pump_water"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                drain_tank()
                # cant rinse since the water pump has failed
                return False 

        # add n 
        if n_req != 0:  # accouts for the def in the particular chemical

            n_added = heap1.time_dose("tank_6", n_req)

            if n_added is False: # means there is issue with pump
                #reset hmi value when pump fails
                heap1.set_heapdata('equipment_status', 'pump_6', "'0%'")

                alarm_description = "Failure of Pump P6"
                alarm_priority = "Medium"
                alarm_type = "4,5"
                affected_equipment = troughs_affected("n")+",pump_6"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                if drain_tank() is False: return False
                rinse() # if drain false then you can rinse anyways
                return False 

        # add p 
        if p_req != 0:  # accouts for the def in the particular chemical

            p_added = heap1.time_dose("tank_7", p_req)

            if p_added is False: # means there is issue with pump

                heap1.set_heapdata('equipment_status', 'pump_7', "'0%'")

                alarm_description = "Failure of Pump P7"
                alarm_priority = "Medium"
                alarm_type = "4,5"
                affected_equipment = troughs_affected("p")+",pump_7"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                if drain_tank() is False: return False
                rinse() # if drain false then you can rinse anyways
                return False 

        # add k 
        if k_req != 0:  # accouts for the def in the particular chemical

            k_added = heap1.time_dose("tank_8", k_req)

            if k_added is False: # means there is issue with pump
                heap1.set_heapdata('equipment_status', 'pump_8', "'0%'")
                alarm_description = "Failure of Pump P8"
                alarm_priority = "Medium"
                alarm_type = "4,5"
                affected_equipment = troughs_affected("k")+",pump_8"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                if drain_tank() is False: return False
                return False 

        # add mn 
        if mn_req != 0:  # accouts for the def in the particular chemical

            mn_added = heap1.time_dose("tank_9", mn_req)

            if mn_added is False: # means there is issue with pump
                heap1.set_heapdata('equipment_status', 'pump_9', "'0%'")
                alarm_description = "Failure of Pump P9"
                alarm_priority = "Medium"
                alarm_type = "4,5"
                affected_equipment = troughs_affected("mn")+",pump_9"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                if drain_tank() is False: return False
                rinse() # if drain false then you can rinse anyways
                return False 

        # add sman 
        if sman_req != 0:  # accouts for the def in the particular chemical

            sman_added = heap1.time_dose("tank_10", sman_req)

            if sman_added is False: # means there is issue with pump
                heap1.set_heapdata('equipment_status', 'pump_10', "'0%'")
                alarm_description = "Failure of Pump P10"
                alarm_priority = "Medium"
                alarm_type = "4,5"
                affected_equipment = troughs_affected("sman")+",pump_10"
                email = str(heap1.get_heapdata('alarm_settings', 'email'))
                alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                
                if drain_tank() is False: return False
                rinse() # if drain false then you can rinse anyways
                return False 

        # --------
        # mixing
        # --------

        mix_solution = mix(heap1.get_heapdata("tank_mixing","pump_runtime"))
        if mix_solution is False:
            drain_tank()
            return False 

        # --------
        # dosing
        # --------

        dose_solution = dose(trough)
        
        if dose_solution[0] is False and dose_solution[1] == 1: 
            if drain_tank() is False: return False
            rinse() # if drain false then you cant rinse anyways
            return False 
        
        elif dose_solution[0] is False and dose_solution[1] == 0:
            return False
        # go to next time in loop

    return True



def troughs_affected(nutrient):
    affected = [1, 2, 3, 4, 5]
    for trough in range(1, 6):

        if int(heap1.get_heapdata("trough_"+str(trough), nutrient)) == 0:
            affected.remove(trough)

    affected = ','.join("trough_"+str(x) for x in affected)
    return affected


def shutdown():

    # ensure dosing pumps are off
    heap1.turn_off_gpio(22)
    heap1.turn_off_gpio(15)
    heap1.turn_off_gpio(18)
    heap1.turn_off_gpio(23)
    heap1.turn_off_gpio(24)
    heap1.turn_off_gpio(25)

    #turn off relays
    heap1.turn_on_gpio(5)
    heap1.turn_on_gpio(6)
    heap1.turn_on_gpio(13)
    heap1.turn_on_gpio(19)
    heap1.turn_on_gpio(26)
    heap1.turn_on_gpio(12)
    heap1.turn_on_gpio(16)
    heap1.turn_on_gpio(20)
    heap1.turn_on_gpio(21)

    heap1.set_heapdata('system_variables', 'air_pump', '0')
    heap1.set_heapdata('equipment_status', 'pump_air', 'OFF')
    heap1.set_heapdata('system_variables', 'plant_lights', '0')
    heap1.set_heapdata('system_variables', 'system_state', '0')

def startup():

    # ensure dosing pumps are off
    heap1.turn_off_gpio(22)
    heap1.turn_off_gpio(15)
    heap1.turn_off_gpio(18)
    heap1.turn_off_gpio(23)
    heap1.turn_off_gpio(24)
    heap1.turn_off_gpio(25)

    # ensure relays are off
    heap1.turn_on_gpio(5)
    heap1.turn_on_gpio(6)
    heap1.turn_on_gpio(13)
    heap1.turn_on_gpio(19)
    heap1.turn_on_gpio(26)
    heap1.turn_on_gpio(12)
    heap1.turn_on_gpio(16)
    heap1.turn_on_gpio(20)
    heap1.turn_on_gpio(21)

    # turn on lights and airpump
    heap1.turn_off_gpio(20)
    heap1.turn_off_gpio(21)

    # set air pump on in db
    # set plant lights on in db
    heap1.set_heapdata('system_variables', 'air_pump', '1')
    heap1.set_heapdata('equipment_status', 'pump_air', 'ON')
    heap1.set_heapdata('system_variables', 'system_state', '1')
    heap1.set_heapdata('system_variables', 'plant_lights', '1')
    # top 3 not necessary, being done by flask
    
    if drain_tank() is False: return False
    if rinse() is False: return False


heap1.set_heapdata('system_variables', 'system_pause', '0')

system_state_prev = int(heap1.get_heapdata("system_variables", "system_state"))
if system_state_prev == 1:
    startup()
    pass


system_state_prev = int(heap1.get_heapdata("system_variables", "system_state"))
if system_state_prev == 0:
    shutdown()
    while True: 
        time.sleep(1)
        # wait until system is turned on again

while True:

    for trough in range(1,6):
        print 'sleeping'
        time.sleep(5)
        print 'done sleeping'

        heap1.get_level('tank_6')
        heap1.get_level('tank_7')
        heap1.get_level('tank_8')
        heap1.get_level('tank_9')
        heap1.get_level('tank_10')
        heap1.get_level('tank_water')
        heap1.get_level_mixing_tank('tank_mixing')
        heap1.get_level('trough_1')
        heap1.get_level('trough_2')
        heap1.get_level('trough_3')
        heap1.get_level('trough_4')
        heap1.get_level('trough_5')

        # bypasses trough if it is not in troughs_to_serivce list
        troughs_to_service = update_status()

        print troughs_to_service
        time.sleep(5)

        if trough not in troughs_to_service:
            time.sleep(1)
            continue

        # get trough level
        trough_level = heap1.get_level("trough_"+str(trough))[0]
        if trough_level is False:
            continue

        # get threshold
        threshold_level = heap1.get_heapdata("trough_"+str(trough), "threshold")
        max_level = heap1.get_heapdata("trough_"+str(trough),"maxlevel")

        # check if trough level is below the threshold
        if trough_level < threshold_level:

            # --------
            # rinsing
            # --------
            rinse_tank = rinse()
            if rinse_tank is False:
                continue

            print 'about to dose'
            time.sleep(5)

            # set dosing in progress indicator ON here
            heap1.set_heapdata('system_variables', 'dosing_in_progess', '1')

            # determine how much you need to refill it
            amt_to_refill = max_level - trough_level

            print amt_to_refill, " - cm to fill back"
            time.sleep(5)

            # convert this amount to ml
            # 1 cm3 = 1 ml
            ml_to_refill = heap1.get_required_volume(trough_level, max_level, "trough_"+str(trough))  # pass values in inches/ feet...conversion is done in he function

            print ml_to_refill, " - ml to fill back"
            time.sleep(5)

            # get ratios of required  
            n = heap1.get_heapdata("trough_"+str(trough),"n")
            p = heap1.get_heapdata("trough_"+str(trough),"p")
            k = heap1.get_heapdata("trough_"+str(trough),"k")
            mn = heap1.get_heapdata("trough_"+str(trough),"mn")
            sman = heap1.get_heapdata("trough_"+str(trough),"sman") #secondary macro nutrients
            water = heap1.get_heapdata("trough_"+str(trough),"water")

            # total_ratios = n + p + k + mn + water

            # determine amount of each needed in ml based on ratio and amt_to_refill
            # convert that amount to a level based on the size of the container

            water_req = ml_to_refill

            n_req = (float(water_req) / float(water)) * n  # ml value
            p_req = (float(water_req) / float(water)) * p  # ml value
            k_req = (float(water_req) / float(water)) * k  # ml value
            mn_req = (float(water_req) / float(water)) * mn  # ml value
            sman_req = (float(water_req) / float(water)) * sman  # ml value

            # get ml of fluid in the tank
            # if it less than required: raise alarm and go to the next trough
            
            n_available = heap1.get_level('tank_6')[1] #ml values
            p_available = heap1.get_level('tank_7')[1]
            k_available = heap1.get_level('tank_8')[1]
            mn_available = heap1.get_level('tank_9')[1]
            sman_available = heap1.get_level('tank_10')[1]
            water_available = heap1.get_level('tank_water')[1]

            
            if n_available is False and n_req != 0:
                continue
            if p_available is False and p_req != 0:
                continue
            if k_available is False and k_req != 0:
                continue
            if mn_available is False and mn_req != 0:
                continue
            if sman_available is False and sman_req != 0:
                continue
            if water_available is False and water_req != 0:
                continue


            if (n_req > n_available) or (p_req > p_available) or (k_req > k_available) or (mn_req > mn_available) or (sman_req > sman_available) or (water_req > water_available):

                if n_req > n_available:

                    defficiency = n_req - n_available
                    defficiency = round(defficiency, 1)
                    alarm_description = "Please add at least "+str(defficiency)+"ml of Nitrogen solution into Tank 6 so that Trough "+str(trough)+" can be replenished."
                    alarm_priority = "Medium"
                    alarm_type = "2, 4"
                    affected_equipment = "trough_"+str(trough)+",tank_6"
                    email = heap1.get_heapdata('alarm_settings', 'email')
                    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                    
                    # raise alarm

                if p_req > p_available:
                    defficiency = p_req - p_available
                    defficiency = round(defficiency, 1)
                    alarm_description = "Please add at least "+str(defficiency)+"ml of Phosphorus solution into Tank 7 so that Trough "+str(trough)+" can be replenished."
                    alarm_priority = "Medium"
                    alarm_type = "2, 4"
                    affected_equipment = "trough_"+str(trough)+",tank_7"
                    email = heap1.get_heapdata('alarm_settings', 'email')
                    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                    
                    # raise alarm

                if k_req > k_available:

                    defficiency = k_req - k_available
                    defficiency = round(defficiency, 1)
                    alarm_description = "Please add at least "+str(defficiency)+"ml of Potassium solution into Tank 8 so that Trough "+str(trough)+" can be replenished."
                    alarm_priority = "Medium"
                    alarm_type = "2, 4"
                    affected_equipment = "trough_"+str(trough)+",tank_8"
                    email = heap1.get_heapdata('alarm_settings', 'email')
                    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                    
                    # raise alarm

                if mn_req > mn_available:
                    defficiency = mn_req - mn_available
                    defficiency = round(defficiency, 1)
                    alarm_description = "Please add at least "+str(defficiency)+"ml of Micro Nutrients solution into Tank 9 so that Trough "+str(trough)+" can be replenished."
                    alarm_priority = "Medium"
                    alarm_type = "2"
                    affected_equipment = "trough_"+str(trough)+",tank_9"
                    email = heap1.get_heapdata('alarm_settings', 'email')
                    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                    
                    # raise alarm

                if sman_req > sman_available:
                    defficiency = sman_req - sman_available
                    defficiency = round(defficiency, 1)
                    alarm_description = "Please add at least "+str(defficiency)+"ml of Secondary Macro Nutrients solution into Tank 10 so that Trough "+str(trough)+" can be replenished."
                    alarm_priority = "Medium"
                    alarm_type = "2"
                    affected_equipment = "trough_"+str(trough)+",tank_10"
                    email = heap1.get_heapdata('alarm_settings', 'email')
                    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                    
                    # raise alarm

                if water_req > water_available:
                    defficiency = water_req - water_available
                    defficiency = round(defficiency, 1)
                    alarm_description = "Please add at least "+str(defficiency)+"ml of Water into Water Tank so that Trough "+str(trough)+" can be replenished."
                    alarm_priority = "Medium"
                    alarm_type = "2"
                    affected_equipment = "trough_"+str(trough)+",tank_water"
                    email = heap1.get_heapdata('alarm_settings', 'email')
                    alarm1.log_alarm(alarm_description, alarm_priority, alarm_type, affected_equipment, email)
                    
                    # rasie alarm 

                continue # once any of these occur, go on to next trough


            mixing_tank_height = heap1.get_heapdata("tank_mixing","sensor_height")  # cm
            mixing_tank_height = mixing_tank_height - 10 # leaves space for sensor reading
            mixing_tank_base_area = heap1.get_heapdata("tank_mixing","base_area")

            mixing_tank_capacity = mixing_tank_base_area*mixing_tank_height  #cm3 == ml

            if ml_to_refill > mixing_tank_capacity: 

                # split dosing into multiple times
                number_of_times_to_dose = int(nm.ceil(float(ml_to_refill)/float((mixing_tank_capacity)))) # number of times to dose 
                amount_to_dose = ml_to_refill/number_of_times_to_dose

            else:
                number_of_times_to_dose = 1
                amount_to_dose = ml_to_refill

            water_req = amount_to_dose

            mani = 200

            n_req = (float(water_req+mani) / float(water)) * n  # ml values
            p_req = (float(water_req+mani) / float(water)) * p  # ml values
            k_req = (float(water_req+mani) / float(water)) * k  # ml values
            mn_req = (float(water_req+mani) / float(water)) * mn  # ml values
            sman_req = (float(water_req+mani) / float(water)) * sman  # ml values

            water_height = float(water_req) / float(mixing_tank_base_area)

            # ------------------------------
            # refill trough in portions
            # ------------------------------
            refill_trough = dose_in_sections(number_of_times_to_dose, water_height, n_req, p_req, k_req, mn_req, sman_req, trough)
            if refill_trough is False:
                continue
            else:
                # send stuff in db cause the trough get stuff
                db_connection = DBConnect()
                db, cursor = db_connection.connect()

                now = datetime.datetime.now()
                dt = now.strftime('%Y-%m-%d')

                sql = "insert into doselogs (trough, volume, date) values (%s, %s, %s)"

                # print sql, ('trough_1', '1000', dt)

                cursor.execute(sql, ("trough_"+str(trough), str(int(ml_to_refill)), dt))

                db.commit()
                cursor.close()
                db.close()


    time.sleep(3600) # check troughs every 1hr



