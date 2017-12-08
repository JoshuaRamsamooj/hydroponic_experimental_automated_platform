# valve_1
# valve_2
# valve_3
# valve_4
# valve_5
# valve_drain
# pump_mixing
# pump_water


import sys
import time
from heap import *

troubleshoot_heap = Heap()

def test(x):
    if x == 'valve_1':
        troubleshoot_heap.turn_on_relays([5])
        time.sleep(1)
        troubleshoot_heap.turn_off_relays([5])

    elif x == 'valve_2':
        troubleshoot_heap.turn_on_relays([6])
        time.sleep(1)
        troubleshoot_heap.turn_off_relays([6])

    elif x == 'valve_3':
        troubleshoot_heap.turn_on_relays([13])
        time.sleep(1)
        troubleshoot_heap.turn_off_relays([13])

    elif x == 'valve_4':
        troubleshoot_heap.turn_on_relays([19])
        time.sleep(1)
        troubleshoot_heap.turn_off_relays([19])

    elif x == 'valve_5':
        troubleshoot_heap.turn_on_relays([26])
        time.sleep(1)
        troubleshoot_heap.turn_off_relays([26])

    elif x == 'valve_drain':
        troubleshoot_heap.turn_on_relays([12])
        time.sleep(1)
        troubleshoot_heap.turn_off_relays([12])

    elif x == 'pump_mixing':
        troubleshoot_heap.turn_on_relays([16])
        time.sleep(2)
        troubleshoot_heap.turn_off_relays([16])

    elif x == 'pump_water':
        troubleshoot_heap.start_pump(int(troubleshoot_heap.get_heapdata("tank_water","pump_pin")), 100)
        time.sleep(2)
        troubleshoot_heap.stop_pump()


    elif x == 'pump_6' or x == 'pump_7' or x == 'pump_8' or x == 'pump_9' or x == 'pump_10':

        if x=='pump_10':
            x = "tank_"+x[-2:]
        else:
            x = "tank_"+x[-1:]

        troubleshoot_heap.turn_on_gpio(int(troubleshoot_heap.get_heapdata(x,"pump_pin")))
        time.sleep(2)
        troubleshoot_heap.turn_off_gpio(int(troubleshoot_heap.get_heapdata(x,"pump_pin")))

    else: 
        print 'nothing'
        


if __name__ == "__main__":
    test(sys.argv[1])