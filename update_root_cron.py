from crontab import CronTab
from heap import Heap
import os

cron_heap = Heap()
cron = CronTab('root')

level_schedule = cron_heap.get_heapdata('schedules', 'level_schedule')
ambient_schedule = cron_heap.get_heapdata('schedules', 'ambient_schedule')
camera_schedule = cron_heap.get_heapdata('schedules', 'camera_schedule')
camera_schedule_no_ndvi = cron_heap.get_heapdata('schedules', 'camera_schedule_no_ndvi')
additional0 = cron_heap.get_heapdata('schedules', 'analog0')
additional1 = cron_heap.get_heapdata('schedules', 'analog1')
additional2 = cron_heap.get_heapdata('schedules', 'analog2')
additional3 = cron_heap.get_heapdata('schedules', 'analog3')
additional4 = cron_heap.get_heapdata('schedules', 'analog4')
additional5 = cron_heap.get_heapdata('schedules', 'analog5')
additional6 = cron_heap.get_heapdata('schedules', 'analog6')
additional7 = cron_heap.get_heapdata('schedules', 'analog7')

for job in cron:
	if job.comment == 'level':
		if level_schedule == 'disabled':
			job.enable(False)
		else:
			job.enable()
			job.setall(level_schedule)
			
	if job.comment == 'ambient':
		if ambient_schedule == 'disabled':
			job.enable(False)
		else:
			job.enable()
			job.setall(ambient_schedule)

	if job.comment == 'camera':
		if camera_schedule == 'disabled':
			job.enable(False)
		else:
			job.enable()
			job.setall(camera_schedule)

	if job.comment == 'camera_no_ndvi':
		if camera_schedule_no_ndvi == 'disabled':
			job.enable(False)
		else:
			job.enable()
			job.setall(camera_schedule_no_ndvi)

	if job.comment == 'camera_no_ndvi':
		if camera_schedule_no_ndvi == 'disabled':
			job.enable(False)
		else:
			job.enable()
			job.setall(camera_schedule_no_ndvi)

	if job.comment == 'additional0':
		if additional0 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor0.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor0.csv')
		else:
			job.enable()
			job.setall(additional0)

	if job.comment == 'additional1':
		if additional1 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor1.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor1.csv')
		else:
			job.enable()
			job.setall(additional1)

	if job.comment == 'additional2':
		if additional2 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor2.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor2.csv')
		else:
			job.enable()
			job.setall(additional2)

	if job.comment == 'additional3':
		if additional3 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor3.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor3.csv')
		else:
			job.enable()
			job.setall(additional3)

	if job.comment == 'additional4':
		if additional4 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor4.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor4.csv')
		else:
			job.enable()
			job.setall(additional4)

	if job.comment == 'additional5':
		if additional5 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor5.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor5.csv')
		else:
			job.enable()
			job.setall(additional5)

	if job.comment == 'additional6':
		if additional6 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor6.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor6.csv')
		else:
			job.enable()
			job.setall(additional6)

	if job.comment == 'additional7':
		if additional7 == 'disabled':
			job.enable(False)
			os.system('rm -rf /home/pi/heap/heap/static/additionalsensors/additionalsensor7.csv')
			os.system('touch /home/pi/heap/heap/static/additionalsensors/additionalsensor7.csv')
		else:
			job.enable()
			job.setall(additional7)

	else: 
		pass

cron.write()