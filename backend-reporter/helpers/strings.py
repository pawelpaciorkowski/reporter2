import re
import datetime
import hashlib
import unicodedata
import string
import random
from docutils import core
from docutils.writers.html4css1 import Writer, HTMLTranslator


def clear_to_ascii(s):
    if s is None:
        return None
    s = str(s)
    s = s.replace('ł', 'l').replace('Ł', 'L')
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ascii', 'ignore').decode()
    return s


def slugify(s):
    if s is None:
        return 'none'
    slug = clear_to_ascii(s).lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug).strip('-')
    slug = re.sub(r'[-]+', '-', slug)
    return slug


def odpiotrkuj(wartosc):
    res = {}
    if wartosc is not None:
        for line in wartosc.split('\r\n'):
            line = line.split('=', 2)
            if len(line) > 1:
                res[line[0]] = line[1]
    return res


def simple_password(letters_count=8, digits_count=2):
    vowels = 'aeiouy'
    res = ''

    while len(res) < letters_count:
        candidate = None
        while candidate is None:
            candidate = random.choice(string.ascii_lowercase)
            if len(res) % 2 == 0 and candidate.lower() in vowels:
                candidate = None
            if len(res) % 2 == 1 and candidate.lower() not in vowels:
                candidate = None
            if candidate is not None and candidate in 'lvqx':
                candidate = None
        res += candidate
    while len(res) < letters_count + digits_count:
        res += random.choice(string.digits)
    return res


def empty(val):
    return val is None or val == ''


def obejdz_slownik(slownik, sciezka):
    if slownik is None:
        return None
    elif len(sciezka) < 3:  # TODO: może lepsze sprawdzenie po literach itp?
        print('AAA')
        return sciezka
    elif ' ' in sciezka:
        wartosci = [obejdz_slownik(slownik, podsciezka) for podsciezka in sciezka.split(' ')]
        wartosci_niepuste = [wartosc for wartosc in wartosci if wartosc is not None]
        return ' '.join(wartosci_niepuste)
    elif '.' in sciezka:
        [h, t] = sciezka.split('.', 1)
        if h in slownik:
            return obejdz_slownik(slownik[h], t)
    elif sciezka in slownik:
        return str(slownik[sciezka])


class HTMLFragmentTranslator(HTMLTranslator):
    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        self.head_prefix = ['', '', '', '', '']
        self.body_prefix = []
        self.body_suffix = []
        self.stylesheet = []

    def astext(self):
        return ''.join(self.body)


html_fragment_writer = Writer()
html_fragment_writer.translator_class = HTMLFragmentTranslator


def format_rst(s):
    return core.publish_string(s, writer=html_fragment_writer).decode()


RE_HSTORE = re.compile(r"""
    # hstore key:
    # a string of normal or escaped chars
    "((?: [^"\\] | \\. )*)"
    \s*=>\s* # hstore value
    (?:
        NULL # the value can be null - not catched
        # or a quoted string like the key
        | "((?: [^"\\] | \\. )*)"
    )
    (?:\s*,\s*|$) # pairs separated by comma or end of string.
""", re.VERBOSE)


def parse_hstore(s):
    _bsdec = re.compile(r"\\(.)")
    if s is None:
        return None
    rv = {}
    start = 0
    for m in RE_HSTORE.finditer(s):
        if m is None or m.start() != start:
            raise ValueError(
                "error parsing hstore pair at char %d" % start)
        k = _bsdec.sub(r'\1', m.group(1))
        v = m.group(2)
        if v is not None:
            v = _bsdec.sub(r'\1', v)

        rv[k] = v
        start = m.end()

    if start < len(s):
        raise ValueError(
            "error parsing hstore: unparsed data after char %d" % start)
    return rv


RE_PESEL = re.compile('^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$')
RE_DATAURODZENIA = re.compile('^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$')
RE_DATAURODZENIA_ODWR = re.compile('^[0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]$')


def globalny_hash_pacjenta(nazwisko, imiona, pesel, dataurodzenia):
    imnaz = ((imiona or '') + ' ' + (nazwisko or '')).replace('-', ' ').replace('.', ' ').replace(',', ' ')
    slowa = sorted([slugify(w) for w in imnaz.split(' ') if w.strip() != ''])
    if len(slowa) == 0:
        return None
    if pesel is not None:
        pesel = ''.join(list(re.findall('[0-9]+', pesel)))
    pesel_ok = pesel is not None and re.match(RE_PESEL, pesel)
    if isinstance(dataurodzenia, datetime.datetime) or isinstance(dataurodzenia, datetime.date):
        dataurodzenia = dataurodzenia.strftime('%Y-%m-%d')
    if dataurodzenia is not None and re.match(RE_DATAURODZENIA_ODWR, dataurodzenia):
        dataurodzenia = '%s-%s-%s' % (dataurodzenia[6:], dataurodzenia[3:5], dataurodzenia[:2])
    if pesel_ok:
        inicjaly = ''.join([s[0] for s in slowa if len(s) > 0])
        hash_src = 'Pacjent Alab z peselem %s %s' % (inicjaly, pesel)
    else:
        if dataurodzenia is None or not re.match(RE_DATAURODZENIA, dataurodzenia):
            return None
        hash_src = 'Pacjent Alab bez peselu %s urodzony %s' % (' '.join(slowa), dataurodzenia)
    return hashlib.sha256(hash_src.encode('utf-8')).hexdigest()


def ident_pacjenta_sw_gellert(nazwisko, imiona, pesel, dataurodzenia):
    pac = {
        'nazwisko': nazwisko, 'imiona': imiona,
        'pesel': pesel, 'dataurodzenia': dataurodzenia,
    }
    if pac['pesel'] is not None and len(pac['pesel']) == 11:
        slug = 'PACJENT_PESEL %s %s'
        inicjal = pac['imiona'].strip()[0] if pac['imiona'] is not None and len(pac['imiona'].strip()) > 0 else '-'
        slug %= (inicjal, pac['pesel'])
    elif pac['imiona'] is not None and pac['nazwisko'] is not None and pac['dataurodzenia'] is not None \
            and len(pac['imiona'] + pac['nazwisko']) > 3:
        slug = 'PACJENT_URODZONY %s %s %s'
        slug %= (pac['imiona'].strip(), pac['nazwisko'].strip(), str(pac['dataurodzenia']))
    else:
        raise ValueError("Brak danych")
    slug = slug.upper() + 'LxSE55F7Fy9RzyCUkDZ5FNEG2Vtrp2QM'
    hash = hashlib.sha256(slug.encode('utf-8')).hexdigest()
    return hash


def list_from_space_separated(text, upper=False, lower=False, also_newline=True, also_comma=False, also_semicolon=False,
                              unique=False):
    res = []
    if text is None:
        return res
    if upper:
        text = text.upper()
    elif lower:
        text = text.lower()
    if also_comma:
        text = text.replace(',', ' ')
    if also_semicolon:
        text = text.replace(';', ' ')
    if also_newline:
        text = text.replace('\r\n', '\n').replace('\n', ' ')
    for val in text.split(' '):
        if len(val) > 0:
            if unique and val in res:
                continue
            res.append(val)
    return res


def db_escape_string(s):
    if s is None:
        return 'null'
    s = str(s)
    res = s.replace("'", "''")
    return res


def get_filename(basename, extension, timestamp=None, fn_prefix=None):
    fn = slugify(basename)
    if timestamp is not None:
        fn += timestamp.strftime('_%Y%m%d_%H%M%S')
    else:
        fn += datetime.datetime.now().strftime('_%Y%m%d_%H%M%S')
    fn += '.' + extension
    if fn_prefix is not None:
        fn = fn_prefix + '_' + fn
    return fn

def comma_seq(start_from, length):
    res = []
    pos = start_from
    while pos <= length:
        res.append(str(pos))
        pos += 1
        if len(res) > 1000:
            raise ValueError(res)
    return ", ".join(res)

if __name__ == '__main__':
    print(simple_password())
