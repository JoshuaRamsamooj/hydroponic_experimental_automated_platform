import csv
import time
from MCP3008 import mcp3008

adc = mcp3008()

dt = time.strftime('%m/%d/%Y %H:%M')
adc_value = str(adc.readadc(0))

with open('/home/pi/heap/heap/static/additionalsensors/additionalsensor0.csv', 'ab') as f:
    writer = csv.writer(f)
    writer.writerow([dt,adc_value])