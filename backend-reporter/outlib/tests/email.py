import pytest
import mock

from outlib.email import Email
import datetime



@pytest.fixture
def preconfigured_sender():
    sender = Email()
    sender.conf = {
        'From': 'Test sender',
        'User': 'login@example.com',
        'Host': 'mail.example.com',
        'Port': '587',
        'Pass': 'example',
        'QueueWaitingDir': '/email/waiting',
        'QueueSentDir': '/email/sent'
    }
    sender.conf_loaded = True
    sender.created_at = datetime.datetime(2019, 12, 13, 14, 15, 16, 17)
    return sender

class PatchedIO:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


    def __enter__(self):
        self.omd = mock.patch('os.makedirs').__enter__()
        self.omd.return_value = True
        self.fo = mock.patch('outlib.email.open').__enter__()
        self.fo.__enter__.return_value = 'xx'
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fo.__exit__(exc_type, exc_val, exc_tb)
        self.omd.__exit__(exc_type, exc_val, exc_tb)

def test_waiting_dir_path(preconfigured_sender):
    with PatchedIO() as pio:
        assert preconfigured_sender.queue_waiting_dir() == '/email/waiting'


def test_sent_dir_path(preconfigured_sender):
    with PatchedIO() as pio:
        assert preconfigured_sender.queue_sent_dir() == '/email/sent/201912/13'


def test_send_enqueue(preconfigured_sender):
    with PatchedIO() as pio:
        preconfigured_sender.send('recipient@example.com', 'topic', 'content', enqueue=True)
        print('AAA', pio.fo.__enter__.write)

