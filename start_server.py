import os

os.chdir('/home/pi/heap/heap/')
os.system('/home/pi/heap/venv/bin/gunicorn -b 0.0.0.0:5000 -k gevent app:app')
