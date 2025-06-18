import base64
from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
import xml.etree.ElementTree as etree

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch, FileInput
from helpers.marcel_pdf_xml import MarcelPdf, MarcelXml
from tasks import TaskGroup, Task

MENU_ENTRY = 'Analizuj sprawozdanie z Centrum'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz plik XML, PDF lub CDA wygenerowany z Centrum"""),
    FileInput(field="plik", title="Plik"),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['plik'] is None:
        raise ValidationError("Nie wybrano pliku")
    report = TaskGroup(__PLUGIN__, params)
    lab_task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_analizuj',
    }
    report.create_task(lab_task)
    report.save()
    return report


def analizuj_marcel_xml(xml):
    try:
        xml = xml.decode('cp1250')
    except Exception as e:
        return [{
            'type': 'error',
            'text': 'Błąd dekodowania xml: %s' % str(e)
        }]
    res = []
    xml = etree.fromstring(xml)
    if xml.tag != 'Przesyłka':
        res.append({
            'type': 'warning',
            'text': 'Nieprawidłowy główny tag dokumentu (%s) - nie można przeanalizować.' % xml.tag,
        })
        return res
    marcel_xml = MarcelXml(xml)
    res.append({
        'type': 'info',
        'text': 'XML: %s..' % repr(xml[:50])
    })

    return res


def raport_analizuj(task_params):
    params = task_params['params']
    res = []
    filename = params['plik']['filename']
    extension = filename.split('.')[-1].lower()
    xml_content = None
    if extension == 'cda':
        return {
            'type': 'error',
            'text': 'Pliki CDA nie są na razie obsługiwane.'
        }
    if extension == 'pdf':
        mpdf = MarcelPdf(content=base64.b64decode(params['plik']['content']))
        try:
            if mpdf.is_signed():
                sig_content = mpdf.get_sig_content()
                if sig_content is None:
                    res.append({
                        'type': 'error',
                        'text': 'Nie udało się pobrać informacji o podpisie'
                    })
                else:
                    for cert in load_der_pkcs7_certificates(sig_content):
                        if cert.subject is not None:
                            res.append({
                                'type': 'info',
                                'text': 'Plik podpisany elektronicznie: %s' % str(cert.subject),
                            })
        except Exception as e:
            res.append({
                'type': 'error',
                'text': 'Nie udało się pobrać informacji o podpisie - %s' % str(e)
            })
        if mpdf.has_xml_attachment():
            xml_content = mpdf.get_xml_content()
        else:
            res.append({
                'type': 'error',
                'text': 'PDF nie zawiera załącznika XML.'
            })
    if xml_content is not None:
        res.append({
            'type': 'download',
            'content': base64.b64encode(xml_content).decode(),
            'content_type': 'application/xml',
            'filename': 'dane.xml'
        })
        res += analizuj_marcel_xml(xml_content)
    return res
