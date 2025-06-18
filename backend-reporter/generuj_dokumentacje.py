import os
from base64 import b64encode

import sys
import markdown
import weasyprint
import yaml

from helpers.strings import slugify
from plugins import PluginManager
from datasources.reporter import ReporterDatasource
from meta.admin.roles import get_content as get_content_roles
from meta.admin.rights import get_content as get_content_rights
from api.restplus import api

HTML_HEADER = """
<html>
<head>
<style type="text/css">
    @media print {
        @page { 
            size 210mm 297mm; 
            magin 10mm 10mm;
            @top-left {
                content: '';
                width: 32.6mm;
                height: 7.4mm;
                margin-bottom: 5mm;
                background-image: url('data:image/png;base64,$LOGO$');
                background-size: 100% 100%;
                background-repeat: no-repeat;
                background-position: center center;  
            }
            @top-right {
                content: "$TITLE$";
                text-align: right;
                font-size: 8pt;
                float: right
            } 
            @bottom-center {
                content: "Strona " counter(page) " / " counter(pages);
                text-align: center;
                font-size: 8pt;
            } 
        }
    }
    html {
        font-family: Helvetica, sans-serif;
    }
    p, li {
        text-align: justify;
        text-justify: inter-word;
    }
    img {
        width: 100%;
    }
    table, th, td {
        border: 0.5pt solid black;
        border-collapse: collapse;
    }
    th, td {
        padding: 1pt;
        font-size: 0.95em;
    }
    table.uprawnienia {
        font-size: 8pt;
        width: 100%;
        table-layout: fixed;
    }
    .bt {
        transform: rotate(-90deg);
        white-space: nowrap;
        
    }
    table.uprawnienia th.bt {
        width: 10pt;
        height: 60pt;
    }
    table.uprawnienia .narrow {
        width: 10pt;
    }    
    table.uprawnienia th.narrow {
        text-align: left;
        margin-left: -20pt;
    }
    table.uprawnienia td.narrow {
        text-align: center;
    }
    .break-before {
        page-break-before: always;
    }
    div#front_page {
        page-break-after: always;
    }
    div#front_page h1 {
        text-align: center;
        margin-top: 5cm;
        margin-bottom: 5cm;
    }
    div#change_log {
        margin-bottom: 2cm;
    }
    div#author {
        position: absolute;
        bottom: 0;
        right: 0;
    }

    article {
        break-before: always;
    }

    article p {
        line-height: 1.2em;
    }
    article li {
        line-height: 1.2em;
    }

    /* spis treści początek */

    #contents {
      page: no-chapter;
    }
    #contents ul li {
        list-style-type: none;
        padding: 1pt;
    }
    #contents ul li a {
      color: inherit;
      text-decoration-line: inherit;
    }
    /* #contents ul li a::before {
      content: target-text(attr(href));
    } */
    #contents ul li a::after {
      content: target-counter(attr(href), page);
      float: right;
    }

    /* spis treści koniec */

    blockquote {
        background-color: #e0e0ff;
        margin: 5pt;
        padding: 5pt;
        border-radius: 4pt;
        font-size: 10pt;
    }
    blockquote h4 {
        margin: 0;
        padding: 0;
    }
    blockquote p {
        margin: 0;
        padding: 0;
        line-height: 1.1em;
    }
    div.breadcrumbs {
        position: relative;
        top: -20pt;
        margin-bottom: -15pt;
        font-size: 9pt;
        font-style: italic;
        margin-left: 20pt;
        text-align: right;
    }
    div.breadcrumbs a {
        text-decoration: none;
    }
    div.header-h1 {
        font-weight: bold;
        font-size: 1.5em;
    }
    div.header-h2 {
        font-weight: bold;
        font-size: 1.2em;
    }
    div.header-h3 {
        font-weight: bold;
        font-size: 1.1em;
    }
    div.header-h4 {
        font-weight: bold;
        font-size: 1.0em;
    }
    div.header-h5 {
        font-weight: bold;
        font-size: 0.8em;
    }
    div.header-h6 {
        font-weight: bold;
        font-size: 0.7em;
    }

</style>
<title>$TITLE$</title>
</head>
<body>
<div id="front_page">
    <h1>$TITLE$</h1>
    <div id="change_log">$CHANGE_LOG$</div>
    <div id="author">$AUTHOR$</div>
</div>
"""

HTML_FOOTER = """
    </body>
</html>
"""


def prepare():
    global HTML_HEADER, HTML_FOOTER
    with open('logo.png', 'rb') as f:
        logo = b64encode(f.read()).decode('utf-8')
    HTML_HEADER = HTML_HEADER.replace('$LOGO$', logo)


class Generator:
    def __init__(self, cfg, pm):
        self.cfg = cfg
        self.pm = pm
        self.html = None

    def generate_html(self):
        self.html = HTML_HEADER
        self.html = self.html.replace('$TITLE$', self.cfg['title'])
        self.html = self.html.replace('$AUTHOR$', self.cfg['author'])
        self.toc = []
        self.exisitng_sections = set()
        if 'changes' in self.cfg:
            change_log = '<table id="change_log"><tbody><tr><th>Data</th><th>Wersja</th><th>Opis</th></tr>'
            for line in self.cfg['changes']:
                [data, wersja, opis] = line.split('|')
                change_log += '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (data, wersja, opis)
            change_log += '</tbody></table>'
            self.html = self.html.replace('$CHANGE_LOG$', change_log)
        else:
            self.html = self.html.replace('$CHANGE_LOG$', '')
        content = self.generate_parts()
        self.generate_toc()
        self.html += content
        self.html += HTML_FOOTER

    def generate_toc(self):
        current_level = 0
        self.html += '<article id="contents"><h1>Spis treści</h1>'
        self.html += '<ul>'
        for [level, title, ident] in self.toc:
            self.html += f'<li><a href="#{ident}">{"&nbsp;&nbsp;" * level}{title}</a></li>'

        self.html += '</ul>'
        self.html += '</article>'

    def generate_file_part(self, fn):
        res = ''
        with open(fn, 'r') as f:
            article_html = self.read_markdown(f.read())
            res += f'<article id="{slugify(os.path.basename(fn).replace(".md", ""))}">\n'
            res += self.posprocess_html(article_html)
            res += '</article>'
        return res

    def reduce_headers(self, html):
        res = []
        for line in html.split('\n'):
            for level in range(7):
                if line.startswith(f"<h{level}>"):
                    title = line[4:-5]
                    line = '<div class="header-h%s">%s</div>' % (level, title)
            res.append(line)
        return '\n'.join(res)

    def generate_raporty(self):
        res = '<article id="raporty">\n<h1>Opisy wybranych raportów i narzędzi</h1>'

        def generuj_opisy(target, menu=None):
            subres = ''
            if menu is None:
                menu = []
            if isinstance(target, list):
                for item in target:
                    subres += generuj_opisy(item, menu)
            if isinstance(target, dict):
                if 'menu_entry' not in target:
                    return ''
                menu_entry = target['menu_entry']
                menu_path = menu+[menu_entry]
                module = target['module']
                if 'children' in target:
                    children_subres = generuj_opisy(target['children'], menu_path)
                else:
                    children_subres = ''
                if len(menu) == 0 and children_subres.strip() != '':
                    subres += '\n<h2>%s</h2>\n' % menu_entry
                    subres += children_subres
                elif hasattr(module, 'DOC') and module.DOC is not None:
                    subres += '\n<h3>%s</h3>\n' % menu_entry
                    menu_link = (target['path'], ' » '.join(menu_path))
                    subres += '<div class="breadcrumbs"><a href="http://reporter.alab.lab/%s">%s</a></div>' % menu_link
                    subres += self.reduce_headers(module.DOC)
                    subres += children_subres
                else:
                    subres += children_subres
            return subres

        wszystko = self.pm.get_menu_for_user([('C-ADM', '*')])
        res += generuj_opisy(wszystko)

        res += '</article>'
        return res

    def generate_uprawnienia(self):
        res = self.generate_file_part('uprawnienia.md').replace('</article>', '')

        content_roles = get_content_roles('ADMIN')[0]
        res += '\n<h3>Role użytkowników</h3>\n'
        res += '<table><thead>'
        res += '<tr>%s</tr>' % (''.join(['<th>'+h+'</th>' for h in content_roles['header']]))
        res += '</thead><tbody>'
        for row in content_roles['data']:
            res += '<tr>%s</tr>' % (''.join(['<td>' + v + '</td>' for v in row]))
        res += '</tbody></table>\n'

        content_rights = get_content_rights('ADMIN')[0]
        res += '\n<h3 class="break-before">Uprawnienia w funkcjach</h3>\n'
        res += '<table class="uprawnienia"><thead>'
        res += '<tr><th>Pozycja w menu</th>%s</tr>' % (''.join(['<th class="bt narrow">'+h['hint']+'</th>' for h in content_rights['header'][3:]]))
        res += '</thead><tbody>'
        for row in content_rights['data']:
            plugin = row[0]
            title = row[1]['value']
            res += '<tr><td>%s</td>%s</tr>' % (title, ''.join(['<td class="narrow">' + v['value'] + '</td>' for v in row[3:]]))
        res += '</tbody></table>\n'
        res += '</article>'
        return res


    def generate_parts(self):
        res = ''
        for fn in self.cfg['parts']:
            if fn.startswith('$'):
                fun_name = 'generate_' + fn[1:]
                fun = getattr(self, fun_name, None)
                if fun is not None:
                    res += self.posprocess_html(fun())
                else:
                    raise RuntimeError("Nie można wygenerować", fn)
            else:
                res += self.generate_file_part(fn)
        return res

    def generate_pdf(self):
        fn = self.cfg['target']
        weasyprint.HTML(string=self.html, base_url=os.getcwd()).write_pdf(fn)

    def read_markdown(self, content):
        res = markdown.markdown(content, extensions=['markdown.extensions.tables',
                                                'markdown.extensions.wikilinks'])
        return res

    def posprocess_html(self, html):
        res = ''
        entering_blockquote = False
        for line in html.split('\n'):
            add_line = True
            for level in range(4):
                if line.startswith(f"<h{level}>"):
                    title = line[4:-5]
                    ident = f"section-{slugify(title)}"
                    while ident in self.exisitng_sections:
                        ident += '-'
                    self.exisitng_sections.add(ident)
                    line = line[:3] + f" id={ident}" + line[3:]
                    res += line + '\n'
                    add_line = False
                    self.toc.append([level, title, ident])
            if line.startswith('<h4') and entering_blockquote:
                title = line[4:-5]
                class_name = f"title-{slugify(title)}"
                res += f'<blockquote class="{class_name}">\n'
            elif entering_blockquote:
                res += '<blockquote>\n'
            if line == '<blockquote>':
                entering_blockquote = True
                add_line = False
            else:
                entering_blockquote = False
            if add_line:
                res += line + '\n'
        return res


if __name__ == '__main__':
    cfg_fn = './doc/docs.yml'
    base_dir = os.path.dirname(cfg_fn)
    cfg = yaml.load(open(cfg_fn, 'r'), yaml.FullLoader)
    # print(cfg)
    pm = PluginManager()
    api.plugin_manager = pm
    current_dir = os.getcwd()
    os.chdir(base_dir)
    prepare()

    generator = Generator(cfg, pm)
    generator.generate_html()
    generator.generate_pdf()

    os.chdir(current_dir)
