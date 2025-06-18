import shutil

import os
import weasyprint
import PyPDF2
import datetime
from helpers import random_path, generate_barcode_img_tag
from .diagram import ReportDiagram

PAPER_SIZES = {
    'A0': [841, 1189],
    'A1': [594, 841],
    'A2': [420, 594],
    'A3': [297, 420],
    'A4': [210, 297],
    'A5': [148, 210]
}

HTML_HEAD = '''
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<style type="text/css">
    $PAPER_CSS$
    div#content {
        margin: 0 10pt;    
    }
    h1 {
        margin: 2pt 0;
    }
    h2.table_title {
        page-break-after: no;
    
    }
    div#geninfo {
        color: #555;
        font-weight: lighter;
        margin-bottom: 2pt;
    }
    .info {
        border: 1px solid navy;
        background: lightblue;
        color: navy;
        padding: 3pt;
    }
    .info_warning, .info_error {
        border-color: darkred;
        color: darkred;
        background-color: orange;
    }
    .info_error {
        background-color: red;
        color: #000;  
    }
    table.reportTable, table.reportTable th, table.reportTable td {
        border: 1px solid #000;
        border-collapse: collapse;
    }
    table.reportTable tr:nth-child(even) td {
        background: #eee;
    }
    h5 {
        margin: 0;
        padding: 0;
        padding-top: 10pt;
    }
    table.reportParams {
        font-size: 7pt;
    }
    table.reportParams th {
        font-weight: normal;
    }
    table.reportParams td {
        font-weight: bold;
    }
    table.barcode, table.barcode td {
        border: none !important;
        text-align: center;
        background: none !important;
    }
    table.barcode img {
        width: 2.5cm;
    }
</style>
</head>
<body>'''

HTML_FOOT = '''</body></html>'''


class ReportPdf:
    def __init__(self, data, **settings):
        self.data = data
        self.settings = {
            'title': 'Raport',
            'timestamp': datetime.datetime.now(),
            'size': 'A4',
            'landscape': False,
            'base_font_size': '8pt',
            'password': None,
        }
        for k, v in settings.items():
            self.settings[k] = v
        self.html = ''

    def render_as_bytes(self):
        fn = random_path('reporter', 'pdf')
        self.render_to_file(fn)
        with open(fn, 'rb') as f:
            result = f.read()
        os.unlink(fn)
        return result

    def render_to_file(self, fn):
        self.html = HTML_HEAD
        self.html = self.html.replace('$PAPER_CSS$', self._paper_css())
        self.html += '<div id="content">'
        self.html += '<h1>%s</h1>' % self.settings['title']
        self.html += '<div id="geninfo">Wygenerowano: %s</div>' % \
                     self.settings['timestamp'].strftime('%Y-%m-%d, %H:%M')
        for subres in self.data['results']:
            if subres['type'] in ('info', 'warning', 'error'):
                self._render_info(subres)
            elif subres['type'] == 'table':
                self._render_table(subres)
            elif subres['type'] == 'vertTable':
                self._render_vert_table(subres)
            elif subres['type'] == 'diagram':
                self._render_diagram(subres)
            elif subres['type'] == 'html':
                self._render_html(subres)
            else:
                raise Exception('Unknown result type', subres['type'])
        if 'errors' in self.data:
            for err in self.data['errors']:
                self._render_info({
                    'type': 'error',
                    'text': err
                })
        if 'params' in self.data:
            self._render_report_params(self.data['params'])
        self.html += '</div>'
        self.html += HTML_FOOT
        weasyprint.HTML(string=self.html).write_pdf(fn)
        if self.settings['password'] is not None:
            enc_fn = fn + '_encrypted'
            reader = PyPDF2.PdfFileReader(fn)
            writer = PyPDF2.PdfFileWriter()
            writer.appendPagesFromReader(reader)
            writer.encrypt(self.settings['password'])
            writer.write(enc_fn)
            os.unlink(fn)
            shutil.move(enc_fn, fn)

    def _paper_css(self):
        w, h = PAPER_SIZES[self.settings['size']]
        size = self.settings['size']
        if self.settings['landscape']:
            w, h = h, w
            size += ' landscape'
        css = """
        @page {
          size: %s;
          padding: 0;
          margin: 12pt 0;
          @bottom-left {
            content: "ALAB Reporter";
            padding-left: 19pt;
            padding-bottom: 5pt;
            font-style: italic;
            background-image: url('data:image/png;base64,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');
            background-repeat: no-repeat;
            background-position: 10pt 0;
            background-size: 8pt;
          }
          @bottom-right {
            content: "Strona " counter(page);
            padding-right: 10pt;
            padding-bottom: 5pt;
          }
          @bottom-center {
            content: "%s | wygenerowano %s";
            padding-bottom: 5pt;
          }
        }
        @media print {
          html, body {
            width: %dmm;
            height: %dmm;
            margin: 0;
            padding: 0;
            font-family: 'Arial', 'Helvetica', sans-serif;
            font-size: %s;
          }
        }""" % (size, self.settings['title'],
                self.settings['timestamp'].strftime('%Y-%m-%d, %H:%M'),
                w, h, self.settings['base_font_size'])
        return css

    # INFO
    def _render_info(self, info):
        classes = 'info info_' + info['type']
        res = '<div class="%s">' % classes
        res += info['text']
        res += '</div>'
        self.html += res

    # TABLE
    def _render_table(self, table):
        classes = 'reportTable'
        res = ''
        if 'title' in table:
            res += '<h2 class="table_title">%s</h2>' % table['title']
        res += '<table class="%s">' % classes
        if 'header' in table:
            res += '<thead>'
            res += self._render_table_header(table['header'])
            res += '</thead>'
        res += '<tbody>'
        for row in table['data']:
            res += self._render_row(row)
        res += '</tbody></table>'
        self.html += res

    def _render_table_header(self, header):
        res = ''
        if isinstance(header[0], list):
            for header_row in header:
                res += self._render_table_header(header_row)
        else:
            res += '<tr>'
            for col in header:
                cell = self._unify_cell(col)
                res += self._render_table_header_cell(cell)
            res += '</tr>'
        return res

    @staticmethod
    def _render_table_header_cell(cell):
        attr = {}
        for direct_attr in 'colspan rowspan'.split(' '):
            if direct_attr in cell:
                attr[direct_attr] = cell[direct_attr]
        res = '<th'
        if len(attr.keys()) > 0:
            res += ' ' + ' '.join('%s="%s"' % (k, v) for k, v in attr.items())
        res += '>%s</th>' % cell.get('value', cell.get('title', ''))
        return res

    def _render_row(self, row):
        def create_rows(max_rows):
            rows_representation = []
            for i in range(max_rows):
                row_representation = {'cells': [], 'tag': 'tr'}
                rows_representation.append(row_representation)
            return rows_representation

        def html(rows_to_display):
            res = ''
            for cell_to_display in rows_to_display[0]:
                cells = ''.join(cell_to_display['cells'])
                res += f'<tr>{cells}</tr>'
            return res

        max_depth = self._find_max_nested_rows(row)
        rows = create_rows(max_depth)
        created_rows = [self._render_cells(cell, max_depth, rows) for cell in row]
        return html(created_rows)

    def _render_cells(self, cells, max_depth, rows):
        if self._is_list(cells):
            for indx, cell in enumerate(cells):
                rows[indx]['cells'].append(self._render_cell(cell, max_depth, True))
            return rows
        else:
            rows[0]['cells'].append(self._render_cell(cells, max_depth, False))
            return rows

    def _render_cell(self, cell, max_depth, is_nested):
        cell = self._unify_cell(cell)
        styled_td = self._add_style(cell)
        rowspan_td = self._add_row_span(cell, max_depth, styled_td, is_nested)
        value_td = self._add_value(cell, rowspan_td, max_depth)
        return value_td

    def _unify_cell(self, cell):
        if isinstance(cell, list):
            return [self._unify_cell(c) for c in cell]
        if not isinstance(cell, dict) or cell is None:
            cell = {'value': cell}
        if 'value' in cell and cell['value'] is None:
            cell['value'] = ''
        return cell

    @staticmethod
    def _add_style(cell):
        style = ReportPdf._get_style(cell)
        return f'<td{style}%ROWSPAN%>%VALUE%</td>'

    @staticmethod
    def _get_style(cell):
        style = ''
        if 'background' in cell:
            style = 'background: %s' % cell['background']
            if len(style) > 0:
                style = ' style="%s" ' % '; '.join(style)
        return style

    @staticmethod
    def _add_row_span(cell, max_depth, td, is_nested):
        if not ReportPdf._is_nested_cell(cell, max_depth) and not is_nested:
            return td.replace('%ROWSPAN%', f' rowspan="{max_depth}" ')
        return td.replace('%ROWSPAN%', '')

    def _add_value(self, cell, td, max_depth):
        if ReportPdf._cell_depth(cell) != max_depth or isinstance(cell, dict):
            return td.replace('%VALUE%', str(cell['value']))
        else:
            return ''.join([self._get_cell_value(c) for c in cell])

    @staticmethod
    def _get_cell_value(cell):
        value = cell.get('value', '')
        if cell.get('variant') == 'barcode':
            res = '<table class="barcode"><tr><td>%s</td></tr><tr><td>%s</td></tr></table>'
            res %= (generate_barcode_img_tag(value), value)
            return res
        return value

    # VERT TABLE
    def _render_vert_table(self, data):
        if 'title' in data:
            self.html += '<h2 class="table_title">%s</h2>' % data['title']
        self.html += '<table class="reportTable"><tbody>'
        for row in data['data']:
            self.html += '<tr><td>%s</td><td>%s</td></tr>' % (row['title'], row['value'])
        self.html += '</tbody></table>'

    # DIAGRAM
    def _render_diagram(self, data):
        diagram = ReportDiagram(data)
        res = ''
        if 'title' in data:
            res += '<h2 class="table_title">%s</h2>' % data['title']
        res += '<div class="reportDiagram">'
        res += diagram.render_to_html()
        res += '</div>'
        self.html += res

    # HTML
    def _render_html(self, data):
        # TODO: jakieś wspólne style dla strony i pdf
        if 'title' in data:
            self.html += '<h2 class="table_title">%s</h2>' % data['title']
        self.html += data['html']

    # REPORT'S PARAMS
    def _render_report_params(self, params):
        if isinstance(params, dict):
            params = list(params.items())
        self.html += '<h5>Parametry raportu</h5>'
        self.html += '<table class="reportParams"><tbody>'
        for row in params:
            self.html += '<tr><th>%s</th><td>%s</td></tr>' % tuple(row)
        self.html += '</tbody></table>'

    @staticmethod
    def _is_list(cell):
        if isinstance(cell, list):
            return True
        return False

    @staticmethod
    def _cell_depth(cell):
        if ReportPdf._is_list(cell):
            return len(cell)
        else:
            return 1

    @staticmethod
    def _find_max_nested_rows(row):
        return max([ReportPdf._cell_depth(r) for r in row])

    @staticmethod
    def _is_nested_cell(cell, max_depth):
        if ReportPdf._cell_depth(cell) == max_depth:
            return True
        return False
