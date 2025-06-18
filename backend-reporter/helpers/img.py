import io
from base64 import b64encode

import code128


def generate_barcode_img_tag(barcode):
    barcode_image = code128.image(barcode)
    buff = io.BytesIO()
    barcode_image.save(buff, format='PNG')
    return '<img src="data:image/png;base64,%s">' % b64encode(buff.getvalue()).decode()
