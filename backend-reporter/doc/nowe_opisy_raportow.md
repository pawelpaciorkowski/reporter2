# • » Mailingi » Wyniki dla zleceniodawcy

#### raporty/mailing/WynikiDlaZleceniodawcy

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

# • » Laboratorium » Badania niewykonane

#### raporty/Laboratorium/BadaniaNiewykonane

#### Zestawienie badań niewykonanych w laboratorium.

Raport swoją funkcjonalnością zastępuje "Księgę prac niewykonanych" w Centrum. Dodatkowo zawiera kolumnę z kodem
kreskowym zlecenia.

Domyślnie raport podaje informacje tylko o próbkach po dystrybucji - wg dat przyjęcia materiału bez ujawnienia danych
pacjetna.

Zestawienie można filtrować po badaniach, pracowniach, aparatach oraz klientach. W pola filtrów można wpisywać symbole,
oddzielone spacjami lub przecinkami.

Wybierając odpowiednie zahaczki można:

* wybrać badania wysyłkowe lub wykonywane lokalnie,
* odfiltrować tylko badania przeterminowane (czas wykonania liczony jest od przyjęcia próbki do zatwierdzenia wyniku,
  przeterminowane badania na podstawie maksymalnego czasu oczekiwania na wyniki badań),
* uwzględnić badania przed dystrybujcą
* pokazać dane pacjenta
* wybrać badania wg daty rejestracji, a nie dystrybucji.

Ze względów wydajnościowych zostanie zwróconych maksymalnie 5000 pozycji.
W przypadku dużej ilości badań należy zastosować filtry i zahaczki.

# • » Laboratorium » Listy robocze

#### raporty/Laboratorium/ListyRobocze

#### Zestawienie bieżących list roboczych w wybranej pracowni laboratorium.

Aby zobaczyć spis list istniejących w Centrum: wybierz laboratorium i wpisz symbol pracowni.
Aby zobaczyć szczegóły listy roboczej: wybierz datę wykonania listy i wpisz jej numer. Wskazaną listę można
wyeksportować do pliku excel.

W raporcie nie ma informacji o historycznych listach roboczych.

# • » Laboratorium » Materiały między zleceniami

#### raporty/Laboratorium/MaterialyMiedzyZleceniami

#### Raport ze zleceń zarejestrowanych w dniu dzisiejszym (na wywołanie: dziś i wczoraj) w wybranym laboratorium.

Zwracane są informacje o parach zleceń tego samego pacjenta: zlecenie z materiałami przyjętymi + zlecenia z materiałami
nieprzyjętymi, jeśli istnieją te same materiały w obu zleceniach.
Ten sam pacjent, zdefiniowany jest jako osoby o tych samych numerach PESEL.

__UWAGA:Raport działa tylko z baz Postgres__

# • » Laboratorium » Statystyka osad-rozmaz

#### raporty/Laboratorium/StatystykaOsadRozmaz

Ilościowe zestawienie badań MORF, ROZMAZ, MOCZ, OSAD wykonanych we wskazanym laboratorium w określonym czasie.

Zestawienie w podziale na badania wykonane oraz zakończone błędem wykonania. Rodzaje błędów są rozróżniane.

# • » Laboratorium » Kody przyjęte w dniu

#### raporty/Laboratorium/KodyPrzyjeteWDniu

#### Zestawienie wszystkich kodów kreskowych próbek, które były rozdystrybuowane wskazanego dnia w wybranym laboratorium.

W raporcie przedstawione są kolumny zawierające:

* kody kreskowe próbek,
* datę rejestracji zlecenia,
* symbol i nazwę zleceniodawcy,
* badania przypisane do próbki,
* materiał próbki
* datę i godzinę przyjęcia materiału w laboratorium.

# • » Laboratorium » Wydrukowane bez plików

#### raporty/Laboratorium/WydrukowaneBezPlikow

#### Raport ze zleceń zawierających wykonania oznaczone jako wydrukowane, ale bez podpiętych żadnych dokumentów sprawozdań.

Taka sytuacja może oznaczać zlecenia które ktoś omyłkowo "uznał za wydrukowane" nie podpisując sprawozdań.

Raport wg dat rejestracji.

__UWAGA: Raport nie uwzględnia znaczników wykonania świeższych niż 1 godzina, bo są one nadawane także "tymczasowo" w
trakcie procesu podpisu.__

# • » Laboratorium » Wyniki krytyczne

#### raporty/Laboratorium/WynikiKrytyczne

#### Raport przedstawia wyniki krytyczne zatwierdzone w podanym przedziale dat, z notatkami wewnętrznymi.

Domyślnie raport obejmuje tylko wyniki badań zagrażające życiu - badania UREA, TROPIHS, GLU, NA, K, CL, P, CA, GLUKO-M,
KREA, AMYL, ALT, AST, LIPAZA, CK, BIL-T, MORF (tylko parametry WBC, RBC, HGB, HCT, PLT), FIBR, APTT, PT, D-DIMER,
WIT-DTO, DIGOKS, LIT, WALPRO, TSH.

Aby dostać listę wszystkich wyników krytycznych należy zaznaczyć "wszystkie parametry".

Domyślnie w raporcie brane są pod uwagę badania zatwierdzone, można zmienić widok na badania wykonane (niezatwierdzone).

W pole "Symbole VIP" można wpisać symbole płatników lub zleceniodawców, którzy mają być traktowani priorytetowo (na
górze tabelki).

# • » Narzędzia techniczne » Badania w pakietach

#### raporty/Techniczne/BadaniaWPakietach

##### Zestawienie pakietów badań z bazy wzorcowej.

Raport zestawia wszystkie pakiety występujące w ALAB określa:

* badania z materiałem, które zawierają się w pakiecie,
* ustawienia pakietu (zerowanie cen składowych).

# • » Narzędzia techniczne » Badanie w laboratorium

#### raporty/Techniczne/BadanieWLaboratorium

#### Raport przedstawia metryczkę badania w laboratorium.

Po wybraniu laboratorium oraz symbolu badania wyświetlane są podstawowe informacje o badaniu z bazy laboratoryjnej.

Informacje w raporcie:

* symbol i nazwa badnia,
* kod ICD-9 badnia,
* aktywność badania w bazie laboratoryjnej  (określona na podstawie ustawień pozycji: do rozliczeń, bez rejestracji i
  ukryte),
* maksymalny czas wykonania badania,
* materiały w jakich możliwe jest wykonywane badanie w laboratorium,
* dodatkowe ustawienia badania w laboratorium.

# • » Narzędzia techniczne » Cenniki w kanałach

#### raporty/Techniczne/CennikiWKanalach

#### Zestawienie symboli cenników obowiązujących w punktach pobrań (kanałach rejestracji internetowej) w laboratoriach.

Zwracana jest tabela w formacie:

|     Laboratorium      |    Kanał    | Kanał nazwa |             Cennik              |
|:---------------------:|:-----------:|:-----------:|:-------------------------------:|
| *symbol laboratorium* | *symbol PP* | *nazwa PP*  | *symbol obowiązującego cennika* |

Raport można wygenerować dla jednego lub wszystkich dostępnych laboratoriów.

# • » Narzędzia techniczne » Ceny w cennikach gotówkowych

#### raporty/Techniczne/CenyGotowkowe

#### Ceny w cennikach gotówkowych w poszczególnych laboratoriach.

Zestawienie cen badań ze wszystkich cenników gotówkowych wybranego laboratorium.

Raport można wygenerować na dwa sposoby:

* dla jednego laboratorium ze wszystkich badań
* dla cenników ze wszystkich laboratoriów dla jednego badania.

Zwracana jest tabela w formacie:

|     Badanie      |      Grupa      |     CENG (domyślny)      |         CENG-(2)         |         CENG-...         | 
|:----------------:|:---------------:|:------------------------:|:------------------------:|:------------------------:|
| *symbol i nazwa* | *grupa badania* | *cena badania w cenniku* | *cena badania w cenniku* | *cena badania w cenniku* |          

__UWAGA: Aktualność danych: nie starsze niż 2 godziny, dla pojedynczego badania bieżące, dla Stępińskiej zawsze dane z
wczoraj.__

# • » Narzędzia techniczne » Średnie czasy Cito

#### raporty/Techniczne/CzasyCito

#### Raport ze średniego czasu wykonania 21 podstawowych badań w trybie Cito dla szpitali.

Jako szpital jest zdefiniowany płatnik, który w SNR jest przypisany do grupy płatników "Szpital"

Brane są pod uwagę następujące badania: DD-IL, D-DIMER, MORF, PT, APTT, FIBR, GLU, KREA, NA, K, CL, AMYL, CRP-IL, CK-MB,
TROP-I, TROP-T, RKZ, RKZ-PAK, TSH, ETYL, GRUPA, PR-ZGOD, B-HCG, NARKOT, PMR, MOCZ.

Raport wg dat rejestracji.

Zwracana są:

1. tabela w formacie:

| Laboratorium |              Razem cito               |                         21 parametrów                         |                              %21 w cito                              |    do 60 min <br/>60-90 min<br/>90-120 min<br/>pow 120 min    | 
|:------------:|:-------------------------------------:|:-------------------------------------------------------------:|:--------------------------------------------------------------------:|:-------------------------------------------------------------:|
|   *symbol*   | *ilość badań zleconych w trybie cito* | *ilość badań wymienionych w raporcie zleconych w trybie cito* | *jaki % wszystkich badań cito stanowią badania określone w raporcie* | *ilościowe i % zestawienie badań wykonanych w zakresach czas* |

2. wykres zawierający ilościowy rozkład badań wykonanch w przedziałach godzinowych.
3. tabela z wykazem badań, których czas wykonania przekroczył 120 minut.

# • » Narzędzia techniczne » Średnie czasy wykonania

#### raporty/Techniczne/CzasyWykonan

#### Raport ze średniego czasu wykonywania badań w trybie Cito i Rutyna (w minutach).

Raport wg dat rozliczeniowych.

Zestawienie można filtrować:

* wg symboli badań - zwracane będą informacje o czasie wykonania wszystkich wyników wybranego badania;
* po płatnikach - zwracane będą czasy wykonania wszystkich badań dla wybranego płanika.

Wygenerowana tabela zawiera kolmny z:

* symbolem i nazwą badania;
* pracownią na jakiej jest wykonywane badanie;
* średnim czas badania wykonanego w trybie cito;
* średnim czas badania wykonanego w trybie rutynowym;

Średnie czasy liczone są:

* od rejestracji do dystrybucji;
* od dystrybucji:
    * do akceptacji,
    * do zatwierdzenia,
    * do wydrukowania,

# • » Narzędzia techniczne » Czynne pracownie

#### raporty/Techniczne/CzynnePracownie

#### Lista pracowni z SNR

Zestawienie pracowni dostępnych w wybranym laboratorium z podziałem na lokalne i wysyłkowe.
Domyślnie raport jest pobierany z SNR, na żądanie zestawienie można wyciągnąć z bazy laboratoryjnej.

# • » Narzędzia techniczne » Normy Liczbowe

#### raporty/Techniczne/NormyLiczbowe

#### Wykaz norm liczbowych (zakresów referencyjnych) dla aktywnych metod badań w bazie laboratoryjnej.

Dane wyswietlane w zestawieniu można filtrować po badaniach, metodach i aparatach. Aby to zrobić należy wpisać w
odpowiednie miejsca symbole dla których mają być pobrane dane. Można wyciągnąć dane dla więcej niż jednego
badnia/metody/aparatu wymieniając symbole oddzielone spacjami.

Zwrotnie dostajemy tabelę z informacjami o:

* Laboratorium wykonującym badanie;
* Badaniu ;
* Metodzie;
* Aparacie;
* Parametrze;
* Wyrażeniu (wyświetlany jest sposób obliczenia wyniku badania lub kod transmisji z aparatem);
* Jednostce;
* Opisie;
* wartościach krytycznych (jeśli są zdefiniowane);
* zakresie referencyjnym
* Wieku i płci pacjenta (jeśli są zdefiniowane);
* Typie normy (jeśli jest zdefiniowany);
* Materiale którego dotyczy norma (jeśli jest zdefiniowany);

# • » Weryfikacja IT » Ile podpisanych

#### raporty/WeryfikujaceIT/IlePodpisanych

#### Ilościowe zestawienie plików powstałych z podpisanych sprawozdań z badań w określonym czasie, w wybranym laboratorium.

Zwrotnie otrzymujemy dwie tabele:
1. tabela z ilościowym podsumowaniem ilości wygenerowanych PDF-ów, ilość podpisanych PDF-ów oraz ilość plików CDA.
2. tabela z zestawieniem plików, w których odnotowana jest potencjalna niezgodność. 
   * Raportowane rodzaje niezgodności:
     * brak podpsu,
     * brak pliku CDA

     
