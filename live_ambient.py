from heap import Heap
import time

live_ambient_heap = Heap()

while True:
    time.sleep(1)
    try:
        live_ambient_heap.get_data()
    except Exception as e:
        print e
        pass
