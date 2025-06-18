import datetime

import subprocess

from io import BytesIO

import PyPDF2
import xml.etree.ElementTree as etree

from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
from cryptography.x509.oid import NameOID, ObjectIdentifier


class MarcelPdf:
    def __init__(self, filename=None, content=None):
        if content is not None:
            self.pdf_content = content
        elif filename is not None:
            self.filename = filename
            with open(filename, 'rb') as f:
                self.pdf_content = f.read()
        else:
            raise RuntimeError("Nie ma treści")
        self.pkcs_certificates = None
        self.pkcs_certificates_error = False
        self.openssl_out = None

    def _load_cert_data(self):
        if self.pkcs_certificates is not None or self.openssl_out is not None:
            return
        if self.pkcs_certificates_error:
            raise RuntimeError("Nie udało się załadować certyfikatów")
        sig_content = self.get_sig_content()
        try:
            self.pkcs_certificates = load_der_pkcs7_certificates(sig_content)
            for cert in self.pkcs_certificates:
                if cert.subject is not None:
                    pass
        except ValueError:
            self.pkcs_certificates = None
            self.pkcs_certificates_error = True
            proc = subprocess.Popen(["openssl", "pkcs7", "-inform", "der", "-noout", "-print"], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE)
            proc_out, proc_err = proc.communicate(sig_content)
            if proc.returncode == 0:
                self.openssl_out = [line.strip() for line in proc_out.decode().split('\n')]

    def is_signed(self):
        if b'R/Subtype/Widget/T(Signature' in self.pdf_content:
            return True
        if b'/Type/Sig/Filter/Adobe.PPKLite/SubFilter/ETSI.CAdES.detached' in self.pdf_content:
            return True
        return False

    def has_xml_attachment(self):
        return b'..//..//Dane.xml' in self.pdf_content

    def get_xml_content(self):
        if not self.has_xml_attachment():
            return None
        pdf_bytes_io = BytesIO(self.pdf_content)
        pdf = PyPDF2.PdfFileReader(pdf_bytes_io)
        for page in pdf.pages:
            annots = page.get('/Annots')
            if annots:
                for annot in annots:
                    annot = annot.getObject()
                    if annot['/Type'] == '/Annot' and annot['/Subtype'] == '/FileAttachment':
                        fs = annot['/FS'].getObject()
                        if fs['/F'] == '..//..//Dane.xml':
                            ef = fs['/EF'].getObject()
                            f = ef['/F'].getObject()
                            xml_content = f.getData()
                            # with open('/tmp/last.xml', 'wb') as f:
                            #     f.write(xml_content)
                            return xml_content

    def get_xml_as_dict(self):
        xml = self.get_xml_content()
        if xml is None:
            return None

        def walk(elem):
            tag = elem.tag
            if elem.tag in ('Oczekujące',):
                return None

            if elem.tag in ('Przesyłka', 'Formularze'):
                for cld in list(elem):
                    res = walk(cld)
                    if res is not None:
                        return res

            if elem.tag in ('Sekcje', 'Próbki', 'Wykonania', 'Wyniki'):
                return [walk(cld) for cld in list(elem)]

            if elem.tag in (
            'Formularz', 'Zlecenie', 'Pacjent', 'Zleceniodawca', 'Płatnik', 'Lekarz', 'PunktRejestracji', 'Sekcja',
            'Próbka', 'Wykonanie', 'Wynik', 'Pobranie', 'Zatwierdzenie', 'Generacja', 'Przyjęcie',
            'Pracownik', 'Poborca', 'Norma', 'Stopka', 'Metoda'):
                res = {}
                for k, v in elem.attrib.items():
                    res['@' + k] = v
                for cld in list(elem):
                    cld_res = walk(cld)
                    if cld_res is not None:
                        res[cld.tag] = cld_res
                return res

            if elem.tag in ('TypZlecenia','Badanie', 'Procedura', 'Aparat', 'Parametr', 'Styl','Materiał','Pracownia', 'Rejestracja', 'Wystawca', 'Błąd'):
                res = {}
                for k, v in elem.attrib.items():
                    res['@' + k] = v
                for cld in list(elem):
                    if cld.text is not None:
                        res[cld.tag] = cld.text.strip()
                return res


            res = {}
            for k, v in elem.attrib.items():
                res[k] = v
            for cld in list(elem):
                raise RuntimeError("Element %s ma dzieci (%s), których nie umiem obsłużyć" % (elem.tag, cld.tag))

            return elem.text

        return walk(etree.fromstring(xml))

    def get_sig_content(self):
        if self.is_signed():
            pdf_bytes_io = BytesIO(self.pdf_content)
            pdf = PyPDF2.PdfFileReader(pdf_bytes_io)
            for page in pdf.pages:
                annots = page.get('/Annots')
                if annots:
                    for annot in annots:
                        annot = annot.getObject()
                        if annot['/Subtype'] == '/Widget' and annot['/T'].startswith('Signature'):
                            return bytes(annot['/V']['/Contents'])
        return None

    def get_cert_info(self):
        self._load_cert_data()
        if self.pkcs_certificates:
            for cert in self.pkcs_certificates:
                if cert.subject is not None:
                    return str(cert.subject)
        else:
            for line in self.openssl_out:
                if line.startswith('subject:'):
                    return line[8:]

    # def get_cert_info_cn(self):
    #     for cert in load_der_pkcs7_certificates(self.get_sig_content()):
    #         if cert.subject is not None:
    #             return str(cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value)

    def get_cert_valid_to(self):
        self._load_cert_data()
        if self.pkcs_certificates:
            for cert in self.pkcs_certificates:
                if cert.subject is not None:
                    return cert.not_valid_after
        else:
            for line in self.openssl_out:
                if line.startswith('notAfter:'):
                    return datetime.datetime.strptime(line[10:], "%b %d %H:%M:%S %Y %Z")

    def get_cert_issuer(self):
        self._load_cert_data()
        if self.pkcs_certificates:
            for cert in self.pkcs_certificates:
                if cert.issuer is not None:
                    return str(cert.issuer.get_attributes_for_oid(ObjectIdentifier("2.5.4.3"))[0].value)
        else:
            for line in self.openssl_out:
                if line.startswith('issuer:'):
                    return line[7:]


class MarcelSig:
    def __init__(self, filename=None, content=None):
        if content is not None:
            self.content = content
        elif filename is not None:
            self.filename = filename
            with open(filename, 'rb') as f:
                self.content = f.read()
        else:
            raise RuntimeError("Nie ma treści")
        try:
            self.certificates = load_der_pkcs7_certificates(self.content)
        except:
            self.certificates = []

    def is_signed(self):
        return len(self.certificates) > 0

    def get_cert_info(self):
        for cert in self.certificates:
            if cert.subject is not None:
                return str(cert.subject)

    def get_cert_valid_to(self):
        for cert in self.certificates:
            if cert.subject is not None:
                return cert.not_valid_after

    def get_cert_issuer(self):
        for cert in self.certificates:
            if cert.issuer is not None:
                return str(cert.issuer.get_attributes_for_oid(ObjectIdentifier("2.5.4.3"))[0].value)


XML_REFERENCJE = {
    "Pracownik": "Pracownicy;IdPracownika",
    "Poborca": "Poborcy;IdPoborcy",
    "Pacjent": "Pacjenci;IdPacjenta",
    "StatusPacjenta": "StatusyPacjentów;IdStatusuPacjenta",
    "Lekarz": "Lekarze;IdLekarza",
    "Styl": "Style;IdStylu",
    "Badanie": "Badania;IdBadania",
    "Metoda": "Metody;IdMetody",
    "Pracownia": "Pracownie;IdPracowni",
    "Procedura": "Procedury;IdProcedury",
    "Materiał": "Materiały;IdMateriału",
    "Parametr": "Parametry;IdParametru",
    "Norma": "Normy;IdNormy",
    "Zleceniodawca": "Zleceniodawcy;IdZleceniodawcy",
    "PunktRejestracji": "PunktyRejestracji;IdPunktuRejestracji",
    "PunktPobrań": "PunktyPobrań;IdPunktuPobrań",
    "Płatnik": "Płatnicy;IdPłatnika",
    "TypZlecenia": "TypyZleceń;IdTypuZlecenia",
    "TypNormy": "TypyNorm;IdTypuNormy",
    "Aparat": "Aparaty;IdAparatu",
    "Grupa": "GrupyBadań;IdGrupy",
    "Błąd": "BłędyWykonania;IdBłędu"
}


class MarcelXmlNode:
    def __init__(self, node, doc):
        self.doc = doc
        self.node = node

    def load_children(self):
        pass

    def get_child_node(self, path):
        if isinstance(path, str):
            return self.get_child_node(path.split('.'))


class MarcelXmlFormularz(MarcelXmlNode):
    pass


class MarcelXmlSlownik(MarcelXmlNode):
    pass


class MarcelXml(MarcelXmlNode):
    def __init__(self, node):
        super().__init__(node, None)
        self.node = node
        self.formularze: list[MarcelXmlFormularz] = []
        self.slowniki: dict[str, dict[str, MarcelXmlSlownik]] = {}
        for elem in list(node):
            if elem.tag == 'Formularze':
                for form_elem in list(elem):
                    self.formularze.append(MarcelXmlFormularz(form_elem, self))
            else:
                self.slowniki[elem.tag] = {}
                for slow_elem in list(elem):
                    self.slowniki[elem.tag][slow_elem.attrib['id']] = MarcelXmlSlownik(slow_elem, self)
