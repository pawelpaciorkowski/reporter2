import re
from datasources.snrkonf import SNRKonf


def get_province(postal_code):
    if not re.match(r'^[0-9]{2}\-[0-9]{3}$', postal_code):
        raise Exception('Nieprawidłowy format kodu pocztowego')

    snr = SNRKonf()
    province_rows = snr.dict_select(
        """
        select p.nazwa as powiat, p.wojewodztwo 
        from kodypocztowe k 
        left join powiaty p on k.wojewodztwoipowiat = p.symbol 
        where k.kod = %s 
        limit 1""", [postal_code])
    if len(province_rows) == 0:
        print('Brak wojewodztwa dla podanego kodu pocztowego')
        return 1

    return province_rows
