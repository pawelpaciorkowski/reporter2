import os
import base64
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
from helpers import random_path

class ReportDiagram:
    def __init__(self, data):
        self.data = data


    def _render_plot_bars(self):
        l1, l2 = zip(*self.data['data'])
        plt.bar(l1, l2)
        if 'x_axis_title' in self.data:
            plt.xlabel(self.data['x_axis_title'])
        if 'y_axis_title' in self.data:
            plt.ylabel(self.data['y_axis_title'])
        plt.savefig(self.filename)
        plt.close()

    def _render_plot(self):
        self.filename = random_path('reporter_diagram', 'png')
        if self.data['subtype'] == 'bars':
            self._render_plot_bars()
        else:
            raise Exception('Unknown diagram subtype', self.data['subtype'])


    def render_to_data_uri(self):
        self._render_plot()
        if os.path.exists(self.filename):
            with open(self.filename, 'rb') as f:
                res = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
            os.unlink(self.filename)
            return res

    def render_to_html(self):
        return '<img src="%s" />' % self.render_to_data_uri()

    def render_to_temp_file(self):
        self._render_plot()
        return self.filename