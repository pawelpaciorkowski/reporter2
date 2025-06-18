import openpyxl


class XlsxDatasource:
    pass


if __name__ == '__main__':
    wb = openpyxl.load_workbook(filename='large_file.xlsx', read_only=True)
