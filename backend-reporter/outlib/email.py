import smtplib
import base64
import os
import shutil
import json
import datetime

import sentry_sdk
import time
from glob import glob
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
import unicodedata

class Email():
    def __init__(self):
        self.conf_loaded = False
        self.conf = {}
        self.smtp = None
        self.queue_idx = 0
        self.created_at = datetime.datetime.now()

    def load_config_from_file(self, fn=None):
        if fn is None:
            fn = './email.cfg'
        with open(fn, 'r') as f:
            for line in f.read().split("\n"):
                line = [x.strip() for x in line.split('=', 2)]
                if len(line) > 1:
                    self.conf[line[0]] = line[1]
        self.conf_loaded = True

    def unpolish(self, s):
        slug = unicodedata.normalize('NFKD', s)
        slug = slug.replace('ł', 'l').replace('Ł', 'L')
        slug = slug.encode('ascii', 'ignore').decode()
        return slug

    def internal_send(self, to, subject, content_attachments, attachments=None, enqueue=False):
        if not self.conf_loaded:
            self.load_config_from_file()
        if attachments is None:
            attachments = []
        if not isinstance(to, list):
            to = [to]
        msg = MIMEMultipart()
        msg['From'] = "%s <%s>" % (self.conf.get('From', 'No-reply'), self.conf['User'])
        msg['To'] = COMMASPACE.join('<%s>' % x for x in to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
        for ca in content_attachments:
            msg.attach(ca)
        if isinstance(attachments, list):
            n_attachments = {}
            for att in attachments:
                n_attachments[att] = os.path.basename(att)
            attachments = n_attachments
        for att, dest_filename in attachments.items():
            with open(att, 'rb') as f:
                part = MIMEApplication(
                    f.read(),
                    Name=self.unpolish(dest_filename)
                )
            part.add_header('Content-Disposition', 'attachment', filename=dest_filename)
            msg.attach(part)
        msg_string = msg.as_string()
        if enqueue:
            self.enqueue_message(to, msg_string)
        else:
            self.smtp_login()
            self.smtp.sendmail(self.conf['User'], to, msg_string)

    def send(self, to, subject, content, attachments=None, enqueue=False):
        self.internal_send(to, subject, [MIMEText(content)], attachments, enqueue)

    def send_html(self, to, subject, html_content, attachments=None, enqueue=False):
        text = "To jest wiadomosc w formacie HTML. Skonfiguruj swoj program pocztowy tak, aby wyswietlal tego typu wiadomosci."
        # TODO: nie wiem jak zrobić żeby załącznik MIMEText(text, 'plain') był widoczny tylko przy nieobsługiwanym htmlu
        self.internal_send(to, subject, [MIMEText(html_content, 'html')], attachments, enqueue)

    def enqueue_message(self, to, msg_string):
        with open(self.queue_waiting_fn(), 'w') as f:
            f.write(json.dumps({
                'to': to,
                'msg': msg_string
            }))

    def send_all_from_queue(self):
        if not self.conf_loaded:
            self.load_config_from_file()
        for fn in self.queue_waiting_message_files():
            ok = False
            try:
                if self.send_from_queue_file(fn):
                    self.queue_move_to_sent(fn)
                    ok = True
            except smtplib.SMTPServerDisconnected:
                self.smtp_login()
                try:
                    if self.send_from_queue_file(fn):
                        self.queue_move_to_sent(fn)
                        ok = True
                except:
                    sentry_sdk.capture_exception()
            except:
                sentry_sdk.capture_exception()
            if not ok:
                retry_cnt = self.get_retry_count(fn)
                if retry_cnt == 5:
                    self.queue_move_to_errors(fn)
                else:
                    self.save_retry_count(fn, retry_cnt + 1)

    def queue_age_of_oldest_waiting_message(self):
        res = None
        for fn in self.queue_waiting_message_files():
            mtime = os.path.getmtime(fn)
            if res is None or mtime < res:
                res = mtime
        if res is not None:
            return int(time.time() - res)
        else:
            return -1

    def smtp_login(self):
        if self.smtp is None:
            try:
                self.smtp = smtplib.SMTP(self.conf['Host'], int(self.conf['Port']))
                self.smtp.ehlo()
                self.smtp.starttls()
                self.smtp.ehlo()
                self.smtp.login(self.conf['User'], self.conf['Pass'])
            except Exception as e:
                self.smtp = None
                raise e

    def queue_waiting_dir(self):
        default = os.path.join(os.path.dirname(__file__), 'email_queue')
        res = self.conf.get('QueueWaitingDir', default)
        if not os.path.isdir(res):
            os.makedirs(res, exist_ok=True)
        return res

    def queue_sent_dir(self):
        default = os.path.join(os.path.dirname(__file__), 'email_sent')
        res = self.conf.get('QueueSentDir', default)
        res = os.path.join(res, self.created_at.strftime('%Y%m'), self.created_at.strftime('%d'))
        if not os.path.isdir(res):
            os.makedirs(res, exist_ok=True)
        return res

    def queue_error_dir(self):
        default = os.path.join(os.path.dirname(__file__), 'email_error')
        res = self.conf.get('QueueErrorDir', default)
        res = os.path.join(res, self.created_at.strftime('%Y%m'), self.created_at.strftime('%d'))
        if not os.path.isdir(res):
            os.makedirs(res, exist_ok=True)
        return res

    def queue_waiting_fn(self):
        self.queue_idx += 1
        fn = '%s_%05d.email' % (self.created_at.strftime("%Y%m%d_%H%M%S_%f"), self.queue_idx)
        return os.path.join(self.queue_waiting_dir(), fn)

    def queue_waiting_message_files(self):
        return glob(os.path.join(self.queue_waiting_dir(), '*.email'))

    def send_from_queue_file(self, fn):
        with open(fn, 'r') as f:
            msg = json.loads(f.read())
        self.smtp_login()
        res = self.smtp.sendmail(self.conf['User'], msg['to'], msg['msg'])
        if len(res.keys()) > 0:
            # tu obsługujemy sytuację, w której wiadomość udało się wysłać tylko do części adresatów
            self.enqueue_message(res.keys(), msg['msg'])
        return True

    def queue_move_to_sent(self, fn):
        dest_fn = os.path.join(self.queue_sent_dir(), os.path.basename(fn))
        shutil.move(fn, dest_fn)

    def queue_move_to_errors(self, fn):
        dest_fn = os.path.join(self.queue_error_dir(), os.path.basename(fn))
        shutil.move(fn, dest_fn)

    def get_retry_count(self, fn):
        if '.retry-' in fn:
            fn_part = fn.split('.retry-')[1].split('.')[0]
            return int(fn_part)
        else:
            return 0

    def save_retry_count(self, fn, cnt):
        if '.retry-' in fn:
            fn_tab = fn.split('.')
            fn_res_tab = []
            for part in fn_tab:
                if part.startswith('retry-'):
                    fn_res_tab.append('retry-%d' % cnt)
                else:
                    fn_res_tab.append(part)
            shutil.move(fn, '.'.join(fn_res_tab))
        else:
            fn_tab = fn.split('.')
            fn_tab.insert(-1, 'retry-%d' % cnt)
            shutil.move(fn, '.'.join(fn_tab))
