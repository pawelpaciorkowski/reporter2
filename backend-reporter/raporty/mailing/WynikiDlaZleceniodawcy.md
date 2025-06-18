#### Eksport wyników wybranych badań dla klienta. Raport wg dat zatwierdzenia.

Na podstawie zdefiniowanych ustawień generowany zostaje raport wyników badań pacjentów. Raport może otrzymać klient
e-mailem jednorazowo lub cyklicznie.

W rapocie należy podać dane klienta (symbol płatnika), którego dotyczy raport. Jeżeli raport ma być generowany dla
wybranych zleceniodawców klienta należy zdefiniować ich symbole.
Należy określić listę badań, które mają być zawarte w raporcie z dokładnością do symbolu badania sparowanego z symbolami
parametrów.
Tak określony raport można wygerenrować i ściągnąć w formie Excel.

Jeżeli raport ma być wysłany jednorazowo należy w pole emaile wpisać adresy, na które ma dotrzeć zestawienie oraz
określić hasło do szyfrowania dokumentu.
Na podany nr telefonu zostanie przysłany sms z hasłem. UWAGA - należy się upewnić czy sms z hasłem dotarł do klienta.
Raport jest wysyłany od razu po wygenerowaniu.

Jeżeli zestawienie ma być cyklicznie wysyłane do kontrahenta, należy zgłosić taką potrzebę do opiekuna aplikacji wraz ze
zdefiniowanymi parametrami raportu. Raport do podpięcia pod crona.

Przykład:

Z danych z laboratorium Warszawa Kopernika należy wysłać jednorazowo raport z wyników badania PT ze wszystkich oddziałów
Szpitala (WN-SZPI). Raport ma być wysłany na adres email test@alab.com.pl, hasło do raportu A123456!. Okres raportowania
to 2024-11-01 do 2024-11-05
ustawienia:

|     Laboratorium     |        *KOPERNI*        |
|:--------------------:|:-----------------------:|
|       Platnik        |        *WN-SZPI*        |
|    Zleceniodawca     |                         |
|       Badania        | *PT:PT, PT:INR, PT:WSK* |
|   Data poczatkowa    |      *2024-11-01*       |
|     Data końcowa     |      *2024-11-05*       |
|        Emaile        |   *test@alab.com.pl*    |
| hasło do szyfrowania |       *A123456!*        |
|      nr teleonu      |                         |
