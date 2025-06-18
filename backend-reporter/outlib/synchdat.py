from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass


@dataclass()
class DatCol:
    col: str
    foreign_table: Optional[str] = None
    remote_reference: Optional['DatCol'] = None
    positive_cond: Optional[str] = None
    negative_cond: Optional[str] = None
    is_key: bool = False
    only_insert: bool = False
    default_value: Any = None
    hidden: bool = False

    def render_header(self, nested=None) -> Optional[str]:
        if self.hidden:
            return None
        res_line = []
        if nested is not None:
            res_line.append('%s.' % nested)
        res_line.append(self.col)
        if self.is_key:
            if nested is not None:
                raise RuntimeError("Nested")
            res_line.insert(0, '*')
        if self.foreign_table is not None:
            res_line.append('@%s' % self.foreign_table)
        if self.remote_reference is not None:
            res_line.append('&%s' % self.remote_reference.render_header(nested=self.foreign_table))
        if self.positive_cond is not None:
            res_line.append('+%s' % self.positive_cond)
        if self.negative_cond is not None:
            res_line.append('-%s' % self.negative_cond)
        return ''.join(res_line)

    def render_value(self, value: Any, only_flat_value=False) -> Any:
        if self.remote_reference is None or only_flat_value:
            if value is None:
                return ''
            return str(value).replace('\t', ' ').replace('\n', '\\\\')
        elif isinstance(value, tuple) and len(value) == 2 and self.remote_reference is not None:
            v1, v2 = value
            return (
                self.render_value(v1, only_flat_value=True),
                self.remote_reference.render_value(v2)
            )
        else:
            raise ValueError("Wartość", value, "nie pasuje do kolumny", self)

class DatColHeader:
    def __init__(self, cols: List[DatCol]):
        self.cols = cols

    def render(self) -> str:
        lines = [col.render_header() for col in self.cols]
        return '\n'.join([line for line in lines if line is not None])

class DatTable:
    def __init__(self, name: str, header: DatColHeader,
                 data: Optional[List[Dict[str, Any]]] = None, data_rows: Optional[List[Any]] = None):
        self.name = name
        self.header = header
        self.rows = []
        if data is not None:
            for row in data:
                self.add_row(row)
        elif data_rows is not None:
            for row in data_rows:
                self.add_row(row)

    def add_row(self, row: Union[List[Any], Dict[str, Any]]):
        if isinstance(row, dict):
            self.rows.append(
                [row.get(col.col, row.get(col.col.lower(), col.default_value)) for col in self.header.cols]
            )
        elif isinstance(row, list):
            if len(row) != len(self.header.cols):
                raise ValueError("Invalid row length", len(row), 'header cols length', len(self.header.cols))
            self.rows.append(row)
        else:
            raise ValueError("Invalid row type", row)

    def flatten_value(self, value):
        if isinstance(value, tuple):
            v1, v2 = value
            return [v1] + self.flatten_value(v2)
        else:
            return [value]
    def render_row(self, row: List[Any]):
        res_row = ['+']
        for col, value in zip(self.header.cols, row):
            res_row += self.flatten_value(col.render_value(value))
        return '\t'.join(res_row).rstrip('\t')


    def render(self):
        res = ['[%s]' % self.name]
        res.append(self.header.render())
        for row in self.rows:
            res.append(self.render_row(row))
        res.append('')
        return '\n'.join(res)

class SynchDat:
    def __init__(self):
        self.tables: List[DatTable] = []

    def add_table(self, table: DatTable):
        self.tables.append(table)

    def render_to_string(self) -> str:
        return '\n\n'.join([table.render() for table in self.tables])

    def render_encoded(self) -> bytes:
        return self.render_to_string().replace('\n', '\r\n').encode('cp1250')

    def render_to_file(self, fn):
        with open(fn, 'wb') as f:
            f.write(self.render_encoded())