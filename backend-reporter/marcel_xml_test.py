import xml.etree.ElementTree as etree

from helpers.marcel_pdf_xml import MarcelXml

if __name__ == '__main__':
    with open('/home/adamek/Pobrane/dane.xml', 'rb') as f:
        xml_content = f.read()
    xml_content = xml_content.decode('cp1250')
    xml = etree.fromstring(xml_content)
    marcel_xml = MarcelXml(xml)
    print(marcel_xml)
