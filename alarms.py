from db_connect import *
import smtplib
import time
import os

class Alarm():

    def __init__(self):
        pass

    def log_alarm(self, alarm_description, alarm_priority, alarm_type, affected_equipment, email):

        try:

            db_connection = DBConnect()
            db, cursor = db_connection.connect()

            sql = "select alarm_description from alarms where alarm_status = 1"

            cursor.execute(sql)
            data = cursor.fetchall()
            dis = []
            for d in data:
                dis += d

            cursor.close()
            db.close()

            if alarm_description not in dis:
                try:
                    
                    dt = time.strftime('%Y-%m-%d %H:%M:%S')

                    self.send_alarm_email(alarm_description, alarm_priority, email, str(dt))

                    db_connection = DBConnect()
                    db, cursor = db_connection.connect()

                    sql = "insert into alarms (alarm_description, alarm_status, alarm_date," \
                           "alarm_priority, affected_equipment, alarm_type) values (%s, 1, %s, %s, %s, %s)"

                    cursor.execute(sql, (alarm_description, dt, alarm_priority, affected_equipment, alarm_type))
                    db.commit()
                    cursor.close()
                    db.close()

                    alarm_audio = 'pico2wave -w alarm_audio.wav "Warning! '+str(alarm_description)+'" && aplay alarm_audio.wav'
                    os.chdir('/home/pi/heap/heap/')
                    os.system(alarm_audio)

                except Exception as e:
                    print e
                    pass

        except Exception as e:
            print e
            pass


    def send_alarm_email(self, alarm_description, alarm_priority, email, too):
        try:
            print 'emailing'

            # dome nice html formatting of the email here later on
            email = email.split(',')
            server = smtplib.SMTP('smtp.gmail.com', 587) # specifies mail server, port
            server.ehlo() # Identify yourself to an ESMTP server 
            server.starttls() # Put the SMTP connection in TLS (Transport Layer Security) mode
            # All SMTP commands that follow will be encrypted. You should then call ehlo() again.
            server.ehlo() #secores everything
            server.login('uwiheap@gmail.com', 'uwiheap1234')
            time_of_occurance = too

            subject = "HEAP: " + str(alarm_priority) + " Priority Alarm!"
            alarm_description = "Please monitor the HEAP System. " \
                                "The following alarm has been raised:\n\nAlarm: " \
                                + alarm_description + \
                                "\n\nPriority: " + str(alarm_priority)+ \
                                "\n\nTime: " + time_of_occurance

            message = 'Subject: %s\n\n%s' % (subject, alarm_description)
            server.sendmail('uwiheap@gmail.com', email, message)
            server.quit()


        except Exception as e: 
            print e

   