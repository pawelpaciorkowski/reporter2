import csv
import os
import datetime
from helpers import random_path, generate_barcode_img_tag

class ReportCsv:

    def __init__(self, data, **settings):
        self.data = data
        self.settings = {
            'title': 'Raport',
            'timestamp': datetime.datetime.now(),
        }
        for k, v in settings.items():
            self.settings[k] = v

    def render_to_file(self, fn):
        with open(fn, 'w') as f:
            write = csv.writer(f)
            for result in self.data['results']:
                write.writerow(result['header'])
                write.writerows(result['data'])
                write.writerow([])

    def render_as_bytes(self):
        fn = random_path('reporter', 'csv')
        self.render_to_file(fn)
        with open(fn, 'rb') as f:
            result = f.read()
        os.unlink(fn)
        return result
