class Semplate:
    def __init__(self, comment_char=None, section_prefix=None, strip_whitespaces=True, encoding=None, line_delim='\n'):
        self.encoding = encoding
        self.comment_char = self._dec(comment_char)
        self.section_prefix = self._dec(section_prefix)
        self.strip_whitespaces = strip_whitespaces
        self.line_delim = self._dec(line_delim)
        self.content = None
        self.section_names = []
        self.sections = {}

    def _dec(self, value):
        if self.encoding is None and isinstance(value, str):
            value = value.encode('utf-8')
        elif self.encoding is not None and isinstance(value, bytes):
            value = value.decode(self.encoding)
        return value

    def load(self, filename):
        with open(filename, 'rb') as f:
            self.content = f.read()
            if self.encoding is not None:
                self.content = self.content.decode(self.encoding)
        current_section = self._dec('')
        self.section_names.append(current_section)
        self.sections[current_section] = []
        for line in self.content.split(self.line_delim):
            test_line = line.strip() if self.strip_whitespaces else line
            if test_line.startswith(self.section_prefix):
                current_section = test_line[len(self.section_prefix):].strip()
                if current_section in self.section_names:
                    raise Exception('Doubled section name', current_section)
                self.section_names.append(current_section)
                self.sections[current_section] = []
            self.sections[current_section].append(line)

    def get_section(self, name, with_title=True):
        name = self._dec(name)
        if name not in self.section_names:
            raise ValueError('Section not found', name)
        lines = self.sections[name]
        if not with_title:
            lines = lines[1:]
        return self.line_delim.join(lines)

    def uncomment(self, value):
        if not isinstance(value, list):
            value = self._dec(value).split(self.line_delim)
        res = []
        for line in value:
            test_line = line.strip() if self.strip_whitespaces else line
            if test_line.startswith(self.comment_char):
                line = test_line[len(self.comment_char):]
            res.append(line)
        return self.line_delim.join(res)

    def comment(self, value):
        if not isinstance(value, list):
            value = self._dec(value).split(self.line_delim)
        res = []
        for line in value:
            test_line = line.strip() if self.strip_whitespaces else line
            if not test_line.startswith(self.comment_char):
                line = self.comment_char + self._dec(' ') + line
            res.append(line)
        return self.line_delim.join(res)

    def clear_section(self, name):
        name = self._dec(name)
        if name not in self.section_names:
            raise ValueError('Section not found', name)
        self.sections[name] = [self.sections[name][0]]

    def add_to_section(self, name, value):
        name = self._dec(name)
        if name not in self.section_names:
            raise ValueError('Section not found', name)
        if not isinstance(value, list):
            value = self._dec(value).split(self.line_delim)
        for line in value:
            self.sections[name].append(line)

    def template(self, name, values=None, **kwvalues):
        if values is None:
            values = {}
        for k, v in kwvalues.items():
            values[k] = v
        res = self.uncomment(self.get_section(name, with_title=False))
        for k, v in values.items():
            pat = self._dec('$') + self._dec(k) + self._dec('$')
            res = res.replace(pat, self._dec(v))
        return res

    def save(self, filename):
        lines = []
        for name in self.section_names:
            for line in self.sections[name]:
                lines.append(line)
        content = self.line_delim.join(lines)
        if self.encoding is not None:
            content = content.encode(self.encoding)
        with open(filename, 'wb') as f:
            f.write(content)
