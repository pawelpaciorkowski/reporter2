#### Generator plików dat do metodyk wysyłkowych.

Wybierz plik XLSX z nowym rozdzielnikiem metod.

Arkusz powinien mieć 1 zakładkę, 1 linię nagłówka, w niej obowiązkowo kolumnę Badanie (wypełnioną symbolami badań)  
oraz kolumny z rozdzielnikiem metod (symbolami) według poniższego opisu. Inne kolumny będą ignorowane. Symbole metod
muszą odpowiadać pracowniom wysyłkowym (z grupą ALAB lub ZEWN) założonych w SNR.

Nagłówek kolumny z rozdzielnikiem może składać się z oddzielonych spacją warunków na lab, płatnika, zleceniodawcę
lub dni tygodnia.

W przypadku podania warunku na płatnika warunek na lab nie jest konieczny - lab będzie wybrany wg symbolu płatnika.

| Przykładowe warunki: |
|:--------------------:|
|     lab:ZAWODZI      |
|      pł:F-SZPIT      |
|      zl:FALAZAW      |
|  lab:OTWOCK dni:678  |
|    zl:F-ODDZ tz:C    |

__UWAGA! Generator działa na wszystkich wierszach i kolumnach, także ukrytych. Przesyłany dokument nie powinien
mieć ukrytych wierszy/kolumn, ale nie jest to weryfikowane.__ 