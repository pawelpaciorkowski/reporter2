import os
import glob
import shutil
import base64
from helpers import ZIP, random_path
from outlib.xlsx import ReportXlsx
from outlib.email import Email


def result_to_file(dir_name, result):
    if result.get("type") == "download":
        rep_fn = os.path.join(dir_name, result["filename"])
        with open(rep_fn, "wb") as f:
            f.write(base64.b64decode(result["content"]))
    else:
        filename = result.get('filename')
        if filename is None:
            cnt = len(list(glob.glob(os.path.join(dir_name, '*.xlsx'))))
            filename = ('raport_%03d.xlsx' % (cnt + 1))
        rep = ReportXlsx({'results': [result]})
        rep_fn = os.path.join(dir_name, filename)
        rep.render_to_file(rep_fn)
    return rep_fn


def encrypt_and_send(emails, password, results, attachment_filename=None, subject=None, content=None):
    if attachment_filename is None:
        attachment_filename = results[0]['filename'].split('.')[0] + '.zip'
    if subject is None:
        subject = results[0].get('title') or 'Raport'
    if content is None:
        content = "Raport w załączniku, plik zabezpieczony hasłem.\n\nWiadomość wysłana automatycznie - prosimy nie odpowiadać."
    tmp_dir = random_path('encrypt_and_send')
    os.makedirs(tmp_dir, 0o755)
    zip_file = ZIP()
    zip_file.set_password(password)
    for i, result in enumerate(results):
        rep_fn = result_to_file(tmp_dir, result)
        zip_file.add_file(rep_fn)
    att_fn = os.path.join(tmp_dir, attachment_filename)
    zip_file.save_to_file(att_fn)
    sender = Email()
    for email in emails:
        sender.send(email, subject, content, [att_fn], enqueue=True)
    shutil.rmtree(tmp_dir)
    sender.send_all_from_queue()  # TODO: przenieść do crona


def simple_send(emails, results, subject=None, content=None):
    if subject is None:
        subject = results[0].get('title') or 'Raport'
    if content is None:
        content = "Raport w załączniku.\n\nWiadomość wysłana automatycznie - prosimy nie odpowiadać."
    tmp_dir = random_path('simple_send')
    os.makedirs(tmp_dir, 0o755)
    attachments = []
    for i, result in enumerate(results):
        rep_fn = result_to_file(tmp_dir, result)
        attachments.append(rep_fn)
    sender = Email()
    for email in emails:
        sender.send(email, subject, content, attachments, enqueue=True)
    shutil.rmtree(tmp_dir)
    sender.send_all_from_queue()  # TODO: przenieść do crona
