import ftplib
import io
import requests
import re


def send_email(email, subject, content):
    pass


SMS_FTP_HOST = '2.0.0.21'
SMS_FTP_USER = 'marcel_ftp'
SMS_FTP_PASSWORD = 'marcel_SMS'
SMS_NOTIFY_URL = 'https://sklep.alablaboratoria.pl/cron/notify-clients'

def send_sms_flush_queue():
    requests.get(SMS_NOTIFY_URL)


def send_sms(number, content, send_now=True):
    if not re.match(r'^\d\d\d\d\d\d\d\d\d$', number):
        raise Exception('Nieprawidłowy format numeru telefonu')
    session = ftplib.FTP(SMS_FTP_HOST, SMS_FTP_USER, SMS_FTP_PASSWORD)
    buffer = io.BytesIO(content.encode('utf-8'))
    session.storbinary('STOR 0_%s.force' % number, buffer)
    buffer.close()
    session.quit()
    if send_now:
        send_sms_flush_queue()
