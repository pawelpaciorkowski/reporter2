def wymuszony_cennik_domyslny(lab, inny_cennik_domyslny=None):
    if lab == 'PRZ-PLO':
        return 'CENG-G1'
    if lab == 'DARLOWO':
        return 'G0'
    if lab == 'BIO-KIE':
        return 'X-GOTOW'
    if lab == 'PRZ-OLS':
        return 'GOT'
    return inny_cennik_domyslny
