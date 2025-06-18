# •
#### raporty

# • » Eksporty - dane osob.
#### raporty/EksportyDO

# • » Eksporty - dane osob. » Covid - lista dla WSSE
#### raporty/EksportyDO/CovidListaWSSE
Eksport dla wsse - wg dat zatwierdzenia.



# • » Eksporty - dane osob. » Eksport wyników CDA
#### raporty/EksportyDO/EksportCDA
Eksport wyników z plikami CDA wg kodów zleceń i dat wygenerowania sprawozdań.
        Eksport szuka dokładnie pasujących kodów zleceń i wykonań. Jeśli podane są kody niepasujące ani do zleceń ani wykonań
        (np klient zbiera sobie inne kody z kartonika niż rejestruje) trzeba zaznaczyć opcję "Sprawdź inne kody z rodzin",
        ale wyszukiwanie będzie znacząco wolniejsze. Nie używaj tej opcji bez potrzeby.

# • » Eksporty - dane osob. » Kody zleceń pacjentów
#### raporty/EksportyDO/KodyPacjentow
Lista kodów zleceń dla pacjentów z podanymi numerami PESEL we wskazanym labie. Lista może być
        filtrowana po płatniku, zleceniodawcy lub dacie rejestracji.



--# • » Eksporty - dane osob. » Tłumaczenie wyników
--#### raporty/EksportyDO/TlumaczenieWynikow
Eksport sprawozdań wymagających tłumaczenia (dorejestrowane badanie TLU-EN), wg daty
        utworzenia oryginalnego sprawozdania.



--# • » Eksporty - dane osob. » Wyniki dla zleceniodawcy
--#### raporty/EksportyDO/WynikiZleceniodawcy
Eksport wyników jednego badania dla pojedynczego zleceniodawcy - wg dat zatwierdzenia.

# • » Narzędzia finansowe
#### raporty/Finansowe

# • » Narzędzia finansowe » Ile badań pracownie
#### raporty/Finansowe/IleBadanLaboratoriumPracownie
Raport z liczby wykonanych badań w laboratoriach z rozbiciem na pracownie, grupy badań i grupy płatników.
            W przypadku CZERNIA używana jest baza bieżąca, a nie raportowa. Dołączanie cen możliwe jest tylko przy wykonywaniu raportu
            z jednego dnia i z pojedynczego badania. Raport pokazuje oddzielnie ceny z bazy laboratoryjnej i ceny z bazy rozliczeniowej.
            Dla badań gotówkowych ceny tych samych badań mogą pojawić się w obu kolumnach. W przypadku baz nierozliczanych przez SNR - ceny wszystkich badań
            będą w kolumnie suma lab. Kolumna SNR braki oznacza dla ilu wykonań z danego wiersza nie znaleziono odpowiedników w SNR - taka sytuacja
            jest możliwa w przypadku problemów z połączeniem, bazy której nie rozliczamy centralnie lub gdy jest zatrzymana synchronizacja do SNR bieżących badań w okresie rozliczeń.
            Dla badań wykonywanych w innym laboratorium niż rejestracja ceny dla klientów pojawią się po stronie laboratorium rejestracji.
            Raport wg daty rozliczeniowej

# • » Narzędzia finansowe » Ile badań pracownie 2
#### raporty/Finansowe/IleBadanPracownie2
Raport z liczby wykonanych badań w laboratoriach z rozbiciem na pracownie, grupy badań i grupy płatników.
            Raport wykonywany z bazy raportowej, uzupełnianej w nocy danymi na poprzedni dzień. Ceny dla zleceń niegotówkowych
            podawane są w miarę możliwości z SNR, a jeśli nie ma to z cennika wzorcowego.
            Kolumna SNR braki oznacza dla ilu wykonań z danego wiersza nie znaleziono odpowiedników w SNR - taka sytuacja
            jest możliwa w przypadku problemów z połączeniem, bazy której nie rozliczamy centralnie lub gdy jest zatrzymana synchronizacja do SNR bieżących badań w okresie rozliczeń.
            Uwaga! Cena wg cennika wzorcowego jest podawana zawsze dla badań oznaczonych jako płatne, nawet jeśli jest to badanie zlecone między laboratoriami.
            W przypadku braku danych z danego laboratorium i dnia zostanie wyświetlone odpowiednie ostrzeżenie.

# • » Narzędzia finansowe » Ile zarejestrowanych / wykonanych
#### raporty/Finansowe/IleZarejestrowanychWykonanych
Raport z liczby zarejestrowanych w danym przedziale wykonań wybranego badania, oraz liczby badań już wykonanych (spośród liczby zarejestrowanych)
                Od dn. 2022-07-20 raport jest wykonywany wg pola GodzinaRejestracji w wykonaniach, a nie DataRejestracji, tzn rzeczywistego momentu rejestracji a nie daty ze zlecenia. Wartości te nie muszą się pokrywać.

# • » Narzędzia finansowe » Wykaz udzielonych rabatów
#### raporty/Finansowe/RaportZRabatow
Wykaz rabatów udzielonych w sprzedaży gotówkowej

# • » Narzędzia finansowe » Raport ze sprzedaży gotówkowej
#### raporty/Finansowe/RaportZeSprzedazyGotowkowej

# • » Narzędzia finansowe » Sprzedaż gotówkowa
#### raporty/Finansowe/SprzedazGotowkowa
Raport generowany jest wg dat rejestracji

# • » Narzędzia finansowe » Sprzedaż gotówkowa pakietów
#### raporty/Finansowe/SprzedazGotowkowaPracownik
Raport ze sprzedaży gotówkowej pakietów w podziale na pracowników Punktów Pobrań. Raport generowany jest wg dat rejestracji.

# • » Narzędzia finansowe » Weryfikacja faktur podwykonawcy
#### raporty/Finansowe/WeryfikacjaFakturPodwykonawcy
Wykaz pacjentów, których badania były wykonane przed podwykonawców zewnętrznych

# • » Narzędzia finansowe » Raport ze sprzedaży
#### raporty/Finansowe/raportZeSprzedazy
Raport Ze Sprzedaży
Wartości nie uwzględniają korekt oraz rabatów naliczanych indywidualnie
Raport wykonany z baz rozliczeniowych, zawiera płatne badania brane pod uwagę podczas wystawiania faktur
Nie uwzględnia pakietów, kontroli, badań wykonywanych dla grupy ALAB
prezentowane dane są wiarygodne jeżeli data końcowa jest przynajmnie dwa dni wstecz od dnia dzisiejszego.

Uwaga, ze względu na błędną konfigurację cenników w niektórych laboratoriach pojawia się niepusta wartość sprzedaży
dla sklepu internetowego w bazie SNR. Ponieważ wartość ta nie ma związku z prawdziwą sprzedażą w sklepie internetowym
od dnia 8.11.2024 raport pomija grupy płatników sklepu internetowego przy wyluczaniu wartości (ilości są uwzględnione,
ale dotyczą momentu zatwierdzenia badań, a nie właściwej sprzedaży w sklepie).

Prawidłowa wartość sprzedaży ze sklepu internetowego jest możliwa do uzyskania od działu ecommerce oraz z systemu Eureca.
        

# • » Konfiguracja badań
#### raporty/KonfiguracjaBadan

# • » Konfiguracja badań » Covid antygen - opisy metod
#### raporty/KonfiguracjaBadan/CovidkiAntygen
Sprawdzenie zgodności opisów metod badań COVID antygen (COV2ANT, COVANTA, COVANTN, CANPOCP, CANPOCA, CANPOCN) z listą testów udostępnianą przez CeZ.
Wyniki badań metodami, których nie da się zmapować na id testu nie są raportowane do EWP.

# • » Laboratorium
#### raporty/Laboratorium
Zestaw raportów używanych w bieżącej pracy laboratorium.



# • » Laboratorium » Brak podpisu - Zawodzie międzylab
#### raporty/Laboratorium/BrakPodpisuZawodzie
Raport z niepodpisanych badań na Zawodziu, analogiczny do raportu mailowego "Brak podpisu",
            z wysyłek międzylab ze wskazanych labów, wg płatnika międzylaboratoryjnego
#TODO...... raport do zmiany. jesli nie będzie zmieniony, to rozpisać ten jak jest        




# • » Laboratorium » Brak podpisu
#### raporty/Laboratorium/RaportDorotki
Raport z niepodpisanych badań analogiczny do mailowego, z możliwością ustawienia jak stare mają być zatwierdzone wykonania brane pod uwagę.
        
TODO        



# • » Laboratorium » Ważność certyfikatów podpisu
#### raporty/Laboratorium/WaznoscCertyfikatow

            Raport sprawdza ważność certyfikatów podpisu elektronicznego dla diagnostów podpisujących wyniki badań laboratoryjnych w ostatnim tygodniu w wybranym laboratorium.
            Informacje odczytywane z jednego sprawozdania dla każdego z pracowników.
              
TODO do poprawki raport!


# • » Pomocnik
#### raporty/Pomocnik



# • » Pomocnik » Dopasuj punkty pobrań
#### raporty/Pomocnik/DopasujPunkty
Wybierz plik XLSX z danymi do dopasowania.
        Arkusz powinien mieć 1 zakładkę, bez ukrytych wierszy i kolumn i bez nadmiernego formatowania 
        (zostanie ono utracone)
        
Podaj oddzielone spacjami litery kolumn (od A) z danymi do wyszukiwania. Dane będą brane pod uwagę
        w podanej kolejności - np jeśli w wyszukiwanych danych jest ulica z numerem i kod pocztowy, to lepiej żeby
        kolumna ulicy wystąpiła przed kodem
Podaj litery kolumn do wpisania danych odnalezionych punktów. Kolumny nie mogą
        pokrywać się z kolumnami wyszukiwania.


# • » Narzędzia do rozliczeń
#### raporty/Rozliczeniowe

# • » Narzędzia do rozliczeń » Bank krwi
#### raporty/Rozliczeniowe/BankKrwi


# • » Narzędzia do rozliczeń » Bank krwi » Wydania skł/płeć/wiek
#### raporty/Rozliczeniowe/BankKrwi/SkladnikiPlecWiek

Raport pobiera informacje z aplikacji "Bank Krwi", jeśli jest używana przez laboratoria serologiczne ALAB. Raport działa tylko w laboratorium CZERNIA z uwagi na wypieranie aplikacji przez nowy system - eKrew.
Raport zwraca ilościowe zestawienie składników krwi wydawanych pacjentom w podziale na ich wiek i płeć.


# • » Narzędzia do rozliczeń » Bruss - raport na płatników z Centrum
#### raporty/Rozliczeniowe/BrussRAP-WSZ

# • » Narzędzia do rozliczeń » Cepelek
#### raporty/Rozliczeniowe/Cepelek
Cepelek

# • » Narzędzia do rozliczeń » Drukowanie naklejek na faktury
#### raporty/Rozliczeniowe/DrukujNaklejki

# • » Narzędzia do rozliczeń » Grupa Gotówka
#### raporty/Rozliczeniowe/GrupaGotowka
Zestawienie sprzedaży gotówkowej zleceniodawców z grupy GOTOWKA. Wg dat rejestracji.

# • » Narzędzia do rozliczeń » Paragony
#### raporty/Rozliczeniowe/Paragony

# • » Narzędzia do rozliczeń » Paragony » Paragony z Marcela
#### raporty/Rozliczeniowe/Paragony/ParagonyMarcel
Paragony wg rejestrów z baz marcelowych - wg dat wystawienia + informacja o prośbach o fakturę

# • » Narzędzia do rozliczeń » Paragony » Paragony offline
#### raporty/Rozliczeniowe/Paragony/ParagonyOffline
Paragony wystawione z aplikacji PPAlab Offline

# • » Narzędzia do rozliczeń » Paragony » Raporty dzienne
#### raporty/Rozliczeniowe/Paragony/RaportyDzienne
Raporty dzienne z drukarek fiskalnych - zbierane aplikacją PPAlab Offline

# • » Narzędzia do rozliczeń » Prośby o fakturę
#### raporty/Rozliczeniowe/ProsbyOFakture
Znajdź prośbę na podstawie 10-literowego identyfikatora prośby lub kodu kreskowego zlecenia.
                    Zostaną wyświetlone podstawowe informacje, aby pobrać treść prośby wejdź pod adres
                    http://2.0.1.101:8081/pof/pdf/IDENTYFIKATOR lub http://10.1.1.114:8081/pof/pdf/IDENTYFIKATOR
                    podstawiając w adresie identyfikator prośby.
Proszę wybrać zakres dat utworzenia prośby

# • » Narzędzia do rozliczeń » Raport Pusta Grupa Płatników
#### raporty/Rozliczeniowe/PustaGrupaPlatnikow
Wykaz imienny zleceń z wybranych laboratoriów prezentujący zlecenia zarejestrowane na płatników z pustą grupą płatników

# • » Narzędzia do rozliczeń » Płatnik Zablokowany Do Rejestracji
#### raporty/Rozliczeniowe/PustaGrupaPlatnikowBezrejestracji
Wykaz imienny zleceń z wybranych laboratoriów prezentujący zlecenia zarejestrowane na płatników z pustą grupą płatników

# • » Narzędzia do rozliczeń » Raport Niezgodny Płatnik
#### raporty/Rozliczeniowe/PustaGrupaPlatnikowNiezgodnyPlatnik
Wykaz zleceń z płatnikiem niezgodnym ze zleceniodawcą

# • » Narzędzia do rozliczeń » Raport Pusty Platnik, a nie gotówka
#### raporty/Rozliczeniowe/PustyPlatnikNieGotowka
Wykaz zleceń z wybranych laboratoriów prezentujący zlecenia zarejestrowane jako gotówka, a z konfiguracji zleceniodawcy powinien zapłacić kontrahent

# • » Narzędzia do rozliczeń » Raport Do Faktury Marcela
#### raporty/Rozliczeniowe/RaportDoFakturyMarcela
Liczba Zarejestrowanych badań, nie anulowanych, z pominięciem pakietów



# • » Narzędzia do rozliczeń » Szukaj pozycji faktury
#### raporty/Rozliczeniowe/SzukajPozycjiFaktury
Podaj numer faktury i nazwisko pacjenta lub lekarza żeby znaleźć odpowiadające im pozycje zestawień do faktury.
            W nazwiskach nie jest istotna wielkość liter, ale jest istotne podanie pełnego nazwiska i polskich znaków tak jak wystąpiły na zestawieniu.
            Uwaga - raport wykonywany jest z danych wykonań replikowanych z labów do SNR. Jeśli lekarz lub pacjent zostali zmienieni po wydaniu faktury i zestawienia i dane te zostały zgrane do SNR to wykonania nie zostaną znalezione.



# • » Narzędzia do rozliczeń » Zgrywanie miesiaca
#### raporty/Rozliczeniowe/ZgrywanieMiesiaca
Raport ze stanu ostatnich sesji zgrywania
Proszę wybrać laboratorium. Zgrywanie zostanie uruchomione tylko jeśli od zakończenia poprzedniego zgrywania minęły co najmniej 3h i nie trwa nowe zgrywanie. Zgrywany jest ostatni miesiąc.

# • » Narzędzia do rozliczeń » Eksporty dla klientów
#### raporty/Rozliczeniowe/dlaKlientow

# • » Narzędzia do rozliczeń » Eksporty dla klientów » CMP
#### raporty/Rozliczeniowe/dlaKlientow/CMP
Proszę datę wygenerowania rozliczenia, aby pobrać zestawienie dla płatnika.

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Ceny lab + HL7
#### raporty/Rozliczeniowe/dlaKlientow/CenyLabHl7
Raport dla klientów rozliczanych przez Centrum, a nie SNR (np z BCAM).
Raport może być albo na płatnika wg dat rozliczeniowych (jeśli zostanie podany symbol płatnika)lub dla faktury w Centrum (jeśli zostanie podany numer faktury, wtedy zakres dat nie ma znaczenia).

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Corten Medic
#### raporty/Rozliczeniowe/dlaKlientow/CortenMedic
Raport Corten Medic NFZ + komercyjne. Stały zestaw symboli zleceniodawców

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Koronawirus - Raport dla NFZ
#### raporty/Rozliczeniowe/dlaKlientow/NFZ_Korona
Raport NFZ Korona dla wybranego laboratorium i płatnika

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Siedlce
#### raporty/Rozliczeniowe/dlaKlientow/Siedlce
Proszę wybrać laboratorium oraz datę wygenerowania rozliczenia, aby pobrać zestawienie dla płatnika. Jeśli danego dnia było więcej niż jedno rozliczenie, należy podać jego identyfikator w formacie NNNNN/RRRR

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport ABBVie
#### raporty/Rozliczeniowe/dlaKlientow/raportABBVie
Raport z ilości wykonanych badań dla ABBVie

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Bychawa
#### raporty/Rozliczeniowe/dlaKlientow/raportBychawa
Raport Bychawa

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Compensa
#### raporty/Rozliczeniowe/dlaKlientow/raportCompensa
Raport z ilości wykonanych badań dla Compensy

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport DKMS
#### raporty/Rozliczeniowe/dlaKlientow/raportDKMS
Raport z wykonanych badań dla DKMS

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Diaverum
#### raporty/Rozliczeniowe/dlaKlientow/raportDiaverum
Raport z wykonanych badań dla Diaverum

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Dietetycy
#### raporty/Rozliczeniowe/dlaKlientow/raportDietetycy
Raport zarejestrowanych badań dla DOBRY DIETETYK/FIT DIETETYK

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Karta dużej rodziny
#### raporty/Rozliczeniowe/dlaKlientow/raportKDR
Raport z ilości zleceń i badań zarejestrowanych ze zniżką dla posiadaczy Karty dużej rodziny (15%KDR)

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport dla NFZ
#### raporty/Rozliczeniowe/dlaKlientow/raportNFZ
Raport dla NFZ, 
należy wskazać dla jakiego płatnika ma być wykonany oraz z jakiego laboratorium. Jeśli eksport ma nie być na wszystkich zleceniodawców to można podać symbole zleceniodawców oddzielone spacją.

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Imienny dla NFZ
#### raporty/Rozliczeniowe/dlaKlientow/raportNFZ_imienny
Raport Imienny dla NFZ, 
należy wskazać dla jakiego płatnika ma być wykonany oraz z jakiego laboratorium

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport po numerze rozliczenia
#### raporty/Rozliczeniowe/dlaKlientow/raportNrRozliczenia
Raport po numerze rozliczenia

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Otwock
#### raporty/Rozliczeniowe/dlaKlientow/raportOtwock
Raport Otwock

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Szaserów
#### raporty/Rozliczeniowe/dlaKlientow/raportSzaserow
Raport Szaserów

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Szpitale
#### raporty/Rozliczeniowe/dlaKlientow/raportSzpitale
Raport Szpitale

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Raport Wolski
#### raporty/Rozliczeniowe/dlaKlientow/raportWolski
Raport Wolski

# • » Narzędzia do rozliczeń » Eksporty dla klientów » Zestawienia gotówki
#### raporty/Rozliczeniowe/dlaKlientow/zestawieniaGot
Podaj identyfikator zestawień gotówkowych klienta i dowolną datę z miesiąca, dla którego chcesz pobrać zestawienie.
UWAGA! Wielkość liter ma znaczenie.

# • » Narzędzia do rozliczeń » Eksporty z SNR
#### raporty/Rozliczeniowe/eksportySNR

# • » Narzędzia do rozliczeń » Eksporty z SNR » Ceny obowiązujące
#### raporty/Rozliczeniowe/eksportySNR/CenyObowiazujace
W przypadku eksportu po symbolach można podać symbole w postaci PŁATNIK:ZLECENIODAWCA jeśli są potrzebne cenniki dla konkretnych zleceniodawców

# • » Narzędzia do rozliczeń » Eksporty z SNR » Płatnicy
#### raporty/Rozliczeniowe/eksportySNR/platnicy

# • » Narzędzia do rozliczeń » Eksporty z SNR » Umowy
#### raporty/Rozliczeniowe/eksportySNR/umowy

# • » Narzędzia do rozliczeń » Poprawnosc replikacji
#### raporty/Rozliczeniowe/poprawnoscReplikacji
Poprawnosc replikacji

# • » Narzędzia do rozliczeń » Poprawnosc replikacji - dokładne
#### raporty/Rozliczeniowe/poprawnoscReplikacjiDokladne
Poprawnosc replikacji - dokładne

# • » Narzędzia do rozliczeń » Poprawnosc replikacji - dokładne TEST
#### raporty/Rozliczeniowe/poprawnoscReplikacjiDokladneTest
Poprawnosc replikacji - dokładne BAZA TESTOWA

# • » Narzędzia do rozliczeń » Poprawnosc replikacji - konkretne badanie
#### raporty/Rozliczeniowe/poprawnoscReplikacjiKonkretneBadanie
Poprawnosc replikacji - konkretne badanie

# • » Narzędzia do rozliczeń » Poprawność replikacji - płatnikami
#### raporty/Rozliczeniowe/poprawnoscReplikacjiPlatnikami
Poprawnosc replikacji płatnikami - pokazuje symbole i grupy płatników, dla których istnieją różnice w ilości wykonanych badań między bazą laboratoryjną i rozliczeniową

# • » Narzędzia do rozliczeń » Poprawność replikacji - płatnikami
#### raporty/Rozliczeniowe/poprawnoscReplikacjiWyjasnijPlatnika
Poprawnosc replikacji płatnikami - pokazuje symbole i grupy płatników, dla których istnieją różnice w ilości wykonanych badań między bazą laboratoryjną i rozliczeniową

# • » Narzędzia do rozliczeń » Zestawienia z SNR
#### raporty/Rozliczeniowe/zestawieniaSNR

# • » Narzędzia do rozliczeń » Zestawienia z SNR » Klienci D, E
#### raporty/Rozliczeniowe/zestawieniaSNR/KlienciDE
Raport wykonywany dla stałej listy NIP, z wystawionych faktur

# • » Narzędzia do rozliczeń » Zestawienia z SNR » Niezgodni płatnicy
#### raporty/Rozliczeniowe/zestawieniaSNR/NiezgodniPlatnicy
Raport przedstawia wykonania z bazy SNR, z płatnikiem niezgodnym ze zleceniodawcą,
        z pominięciem grup płatników ALAB i SZAL. Przy wykonaniach wymienione są rozliczenia i faktury, w których występują.
        Raport wg dat rozliczeniowych. Zwraca max 1000 wykonań.

# • » Narzędzia do rozliczeń » Zestawienia z SNR » Rozliczenia i faktury do badań
#### raporty/Rozliczeniowe/zestawieniaSNR/RozliczeniaIFakturyDoBadan
Raport przedstawia rozliczenia zawierające wskazane badania, ilości i zakres cen badań
        na rozliczeniu i wartość całej faktury, jeśli została wystawiona do rozliczenia.
        Raport wg dat wygenerowania rozliczeń

# • » Narzędzia do rozliczeń » Zestawienia z SNR » Stan przeliczeń
#### raporty/Rozliczeniowe/zestawieniaSNR/StanPrzeliczen
Raport przedstawia ilości wykonań oczekujących na przeliczenie cen, w podziale na laboratoria,
        płatników i miesiące rejestracji. Tych wykonań nie da się w tej chwili rozliczyć ale nie wystąpią
        one również w raportach z błędów przeliczeń.

# • » Narzędzia do rozliczeń » Zestawienia z SNR » Stan wczytywania
#### raporty/Rozliczeniowe/zestawieniaSNR/StanWczytywania
Informacja o tym czy aktualnie trwa wczytywanie przesyłek / kiedy ostatnio się zakończyło.

# • » Narzędzia do rozliczeń » Zestawienia z SNR » Statusy wykonań
#### raporty/Rozliczeniowe/zestawieniaSNR/StatusyWykonan

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu
#### raporty/Rozliczeniowe/zestawieniaSklep

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Kody rabatowe
#### raporty/Rozliczeniowe/zestawieniaSklep/KodyRabatowe
Lista kodów rabatowych 
    Filtrowanie danych po zakresie dat jest jedyni wykorzystywane 
    przy zaznaczonej opcji 'Tylko kody wykorzystane' 

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Zestawienie dzienne - PDF, HTML
#### raporty/Rozliczeniowe/zestawieniaSklep/ZestawienieDzienne
Zestawienie zawiera listę zamówień wraz z ich szczegółami.
    Zestawienie w formacie HTML oraz PDF uwzględnia zamówienia opłacone oraz
nieopłacone.

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Zestawienie dzienne - CSV
#### raporty/Rozliczeniowe/zestawieniaSklep/ZestawienieDzienneNoMergeCSV
Zestawienie zawiera listę zamówień wraz z ich szczegółami.
    Zestawienie w formacie CSV oraz XLSX uwzględnia wyłącznie zamówienia
opłacone.

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Zestawienie dzienne - XLSX
#### raporty/Rozliczeniowe/zestawieniaSklep/ZestawienieDzienneNoMergeXLSX
Zestawienie zawiera listę zamówień wraz z ich szczegółami.
    Zestawienie w formacie CSV oraz XLSX uwzględnia wyłącznie zamówienia
opłacone.

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Zestawienie po punktach pobrań
#### raporty/Rozliczeniowe/zestawieniaSklep/ZestawienieMiesieczne
Zestawienie zawiera listę punktów pobrań wraz z informacją o wartości zamówionych wnich badań.
        Pod uwagę brane są tylko zamówienia opłacone.

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Zestawienie po badaniach i pakietach
#### raporty/Rozliczeniowe/zestawieniaSklep/ZestawieniePoBadaniachIPakietach

    Zestawienie zawiera listę badań i pakietów wraz z informacją na jaką wartość złożono na nie zamówienia.
    Pod uwagę brane są tylko zamówienia opłacone.
    

# • » Narzędzia do rozliczeń » Zestawienia ze sklepu » Zestawienie po klientach
#### raporty/Rozliczeniowe/zestawieniaSklep/ZestawieniePoKlientach
Zestawienie zawiera listę pacjentów którzy złożyli zamówienie we wskazanym okresie
wraz ze szczegółami zamówień.
Pod uwagę brane są tylko zamówienia opłacone.



# • » Narzędzia techniczne
#### raporty/Techniczne



# • » Narzędzia techniczne » Eksporty
#### raporty/Techniczne/Eksporty

# • » Narzędzia techniczne » Eksporty » Kody zleceń płatnika
#### raporty/Techniczne/Eksporty/KodyZlecenPlatnika
Eksport wg dat rejestracji, po symbolu płatnika w bazie laboratoryjnej. Raport zwraca kody kreskowe zleceń oraz ilość wykonań w zleceniu w podziale na zakończone z oraz bez błędu.

# • » Narzędzia techniczne » Eksporty » Kody zleceń zleceniodawcy
#### raporty/Techniczne/Eksporty/KodyZlecenZleceniodawcy
Eksport wg dat rejestracji, po symbolu zleceniodawcy w bazie laboratoryjnej. Raport zwraca kody kreskowe zleceń oraz ilość wykonań w zleceniu w podziale na zakończone z oraz bez błędu.



# • » Narzędzia techniczne » Normy Tekstowe
#### raporty/Techniczne/NormyTekstowe
Normy tekstowe i opisowe dla aktywnych metod. Wpisz symbole badań oddzielone spacjami, dla których mają być pobrane dane.
TODO



# • » Narzędzia techniczne » Siemens
#### raporty/Techniczne/Siemens
Raport z badań wykonywanych jednego dnia, wymagany do analizy przez Siemensa. W przypadku
        raportu po datach przyjęcia (domyślnie) zwracane są wszystkie wykonania nieanulowane.



# • » Narzędzia weryfikujące
#### raporty/Weryfikujace

# • » Narzędzia weryfikujące » Badania przeterminowane
#### raporty/Weryfikujace/BadaniaPrzeterminowane
Raport z badań przeterminowanych i tych, którym data przeterminowania się zbliża.


# • » Narzędzia weryfikujące » Historia wykonania
#### raporty/Weryfikujace/HistoriaWykonania
Pobieranie historii pojedynczego wykonania z bazy laboratoryjnej.

# • » Narzędzia weryfikujące » Zlecenia internetowe spoza PP
#### raporty/Weryfikujace/InternetoweNiePP
Raport przedstawia internetowe kanały dostępu, z których były zlecenia, a nie ma ich w bazie punktów pobrań.


# • » Narzędzia weryfikujące » PPAlab Offline
#### raporty/Weryfikujace/PPalabOffline

# • » Narzędzia weryfikujące » PPAlab Offline » Zalogowane punkty
#### raporty/Weryfikujace/PPalabOffline/ZalogowanePunkty
Informacja o ostatnich logowaniach/uruchomieniach aplikacji PPAlab Offline

# • » Narzędzia weryfikujące » PPAlab Offline » Zlecenia i paragony
#### raporty/Weryfikujace/PPalabOffline/ZleceniaIParagony
Liczba zleceń i paragonów z aplikacji PPAlab Offline. Uwaga - raport wykonywany wg dat otrzymania komunikatów, a nie wystawienia zleceń/paragonów!

# • » Narzędzia weryfikujące » Poprawność kodowania znaków
#### raporty/Weryfikujace/PoprawnoscKodowaniaZnakow
Sprawdzenie poprawności kodowania znaków pod kątem raportów generowanych z SNR. Raport z bazy SNR, wg dat rozliczeniowych.

# • » Narzędzia weryfikujące » Powtórzone kody zleceń
#### raporty/Weryfikujace/PowtorzoneKodyZlecen
Raport zwraca zlecenia z powtarzającymi się kodami kreskowymi zarejestrowane we wskazanym okresie.
        Brane pod uwagę jest 9 pierwszych cyfr kodu, podane kody są uzupełnione o 0 na końcu.
        Raport nie bierze pod uwagę kodów kreskowych wykonań.


# • » Narzędzia weryfikujące » Walidacja cennika
#### raporty/Weryfikujace/WalidacjaCennika
Wybierz plik XLSX z cennikiem do weryfikacji.
        Arkusz powinien mieć 1 zakładkę, w niej obowiązkowe kolumny (z nagłówkiem) badanie lub symbol i cena. Inne kolumny mogą być dowolne i będą ignorowane.
        W kolumnie badanie/symbol powinien znajdować się pojedynczy symbol badania. Możliwe jest rozróżnienie na materiał i typ zlecenia (w tej chwili nie sprawdzane) 
        Arkusz nie powinien mieć poukrywanych wierszy, będą one także sprawdzane.
        Jeśli cennik przejdzie sprawdzenie - może być od razu wysłany do Działu Rozliczeń - w tym celu wprowadź w pole poniżej
        dane jednoznacznie identyfikujące klienta / umowę / aneks i zaznacz pole Wyślij. 
        



# • » Narzędzia weryfikujące » Wysyłka do EWP
#### raporty/Weryfikujace/WysylkaDoEWP
Raport sprawdzający fakt wysyłki wyniku do EWP i ślady tego wydarzenia w różnych miejscach

# • » Narzędzia weryfikujące » Zlecenia niepodpisane
#### raporty/Weryfikujace/ZleceniaNiepodpisane
Wykaz zleceń nie podpisanych (wyniki zatwierdzone w dniu dzisiejszym nie są uwzględniane), filtr wg dat rejestracji.

# • » Narzędzia weryfikujące » Zlecenie w Centrum i SNR
#### raporty/Weryfikujace/ZlecenieCentrumSnr
Proszę wybrać laboratorium, numer i datę rejestracji zlecenia, aby sprawdzić informacje o tym zleceniu w systemie Centrum oraz SNR. 
                Jeśli nie znasz numeru zlecenia, a znasz kod kreskowy - numer i datę możesz sprawdzić w raporcie "Przebieg pracy".

# • » Narzędzia weryfikujące » Zlecenie z EWP
#### raporty/Weryfikujace/ZlecenieEWP
Raport sprawdzający czy konkretne zlecenie spłynęło do nas z EWP i czy zostało zarejestrowane w zlecaczce.
                Wyszukiwanie po dowolnych polach z EWP lub kodzie kreskowym i peselu z zarejestrowanego zlecenia. Zwracane max 20 wierszy.



# • » Weryfikacja IT
#### raporty/WeryfikujaceIT


# • » Weryfikacja IT » Integracje
#### raporty/WeryfikujaceIT/Integracje

# • » Weryfikacja IT » Integracje » ErLab
#### raporty/WeryfikujaceIT/Integracje/ErLab



# • » CS
#### raporty/cs



# • » CS » Eksport kart klienta
#### raporty/cs/EksportKartKlienta
Eksport danych z Kart Klienta.

# • » CS » Płatnicy bez kart
#### raporty/cs/PlatnicyBezKart

# • » CS » Płatnicy bez kart, niezarchiwizowani
#### raporty/cs/PlatnicyBezKartNiezarchiwizowani

# • » CS » Profilaktyka 40+ - NFZ
#### raporty/cs/Profilaktyka40
  

# • » CS » Rabaty jednorazowe
#### raporty/cs/RabatyJednorazowe
Wybierz rabat dla pacjenta, a w pole uwagi wpisz powód wystawienia kodu rabatowego. Powody będą widoczne tylko w zestawieniu wystawionych kodów.
Zestawienie kodów rabatowych można wykonać wg daty wygenerowania kodów (wtedy będą widoczne również kody niewykorzystane) albo wg daty użycia kodów w punktach. Aby uzyskać szczegóły zlecenia, do którego użyto danego kodu, należy go sprawdzić w zakładce "Sprawdź kod".



# • » CS » Sanepid - anuluj zgłoszenie
#### raporty/cs/SanepidAnuluj
Wprowadź kod kreskowy i datę urodzenia aby odszukać zgłoszenie.
        Po upewnieniu się że to właściwe zgłoszenie, wprowadź także jego ID żeby anulować.
        Można anulować tylko niepotwierdzone, niewysłane i nieanulowane zgłoszenia.

# • » CS » Sanepid - anuluj niezaakceptowane
#### raporty/cs/SanepidAnulujStare
Usuwa niezaakceptowane zgłoszenia starsze niż 3-msc


# • » CS » Zleceniodawcy gotówkowi bez kart, niezarchiwizowani
#### raporty/cs/ZleceniodawcyBezKartGotowkowiNiezarchiwizowani

# • » Histopatologia
#### raporty/hist

# • » Histopatologia » Histopatologia wg daty wykonania
#### raporty/hist/Eksport_HIS_ROZ

# • » Histopatologia » Zliczanie ilości na zatwierdzających - wg d. rozl.
#### raporty/hist/Eksport_IL_KALR

# • » Histopatologia » Historia druku
#### raporty/hist/HistoriaDruku
Raport statystyczy wydrukowanych szkiełek/kasetek
Brak wyboru użytkowników generuje raport - Badania ilości
Wybór użytkowników bez zaznaczonych opcji generuje raport - Badania ilości z podziałem na użytkowników
Wybór użytkowników z zaznaczoną opcją "Zbiorowe" generuje raport - Pracownik zbiorcze
Wybór użytkowników z zaznaczoną opcją "Podział na badania" generuje raport - Badania pracownik

# • » Histopatologia » Raport ze sprzedaży
#### raporty/hist/RaportSprzedazy

# • » Histopatologia » Wyniki z dnia
#### raporty/hist/WynikiZDnia

# • » Histopatologia » Zestawienie rozpoznań
#### raporty/hist/ZestawienieRozpoznan

        Zestawienie rozpoznań z baz histopatologicznych wykonywane jest na podstawie opisów wyników.
        Nowe rozpoznania należy zgłaszać przez dział administracyjny Alab Plus, powinno być przy tym wzięte
        pod uwagę, że rozpoznania mogą być wpisywane w różnych językach, formie gramatycznej i szyku zdań.
        Obecnie wyszukiwane rozpoznania:
      Rak piersi: ...rak...piersi... lub ...carcinoma...mammae...
  Rak jelita grubego: ...rak...jelita grubego...

# • » Wszystko o ...
#### raporty/info

# • » Wszystko o ... » Laboratoriach
#### raporty/info/0laboratoria
Informacje o laboratorium z różnych systemów

# • » Wszystko o ... » Płatnikach
#### raporty/info/1platnicy
Informacje o płatnikach z różnych systemów

# • » Wszystko o ... » Zleceniodawcach
#### raporty/info/2zleceniodawcy
Informacje o zleceniodawcy z różnych systemów

# • » Wszystko o ... » Punktach Pobrań
#### raporty/info/3punkty
Informacje o punkcie pobrań z różnych systemów

# • » Wszystko o ... » Badaniach
#### raporty/info/4badania

# • » Wewnętrzne
#### raporty/internal_use

# • » Wewnętrzne » Dane z Centrum
#### raporty/internal_use/DaneZCentrum

# • » Wewnętrzne » Pracownie domyślne
#### raporty/internal_use/ZrobionePracownieDomyslne

# • » Mailingi
#### raporty/mailing

# • » Mailingi » Dorejestrowane ręcznie
#### raporty/mailing/DorejestrowaneRecznie
Wykaz badań zarejestrowanych ręcznie (nie przez HL7)

-- zrobione# • » Mailingi » Wyniki dla zleceniodawcy
-- #### raporty/mailing/WynikiDlaZleceniodawcy
Eksport wyników wybranych badań dla zleceniodawców - wg dat zatwierdzenia.
        Możliwa wysyłka mailem. Raport do podpięcia pod crona.

# • » Punkty pobrań
#### raporty/punkty

# • » Punkty pobrań » Czynne punkty pobrań
#### raporty/punkty/Czynne
Raport przedstawia pierwsze godziny logowania w danym punkcie pobrań danego dnia oraz osoby, które się w tym dniu logowały

# • » Punkty pobrań » Czynne punkty w dniach
#### raporty/punkty/CzynneWDniach
Raport przedstawia pierwsze godziny logowania w punktach we wskazanych dniach

# • » Punkty pobrań » Ile Zleceń Punkty pobrań
#### raporty/punkty/IleZlecenPP

# • » Punkty pobrań » Ile Zleceń Punkty pobrań » Ile zleceń dla płatnika - HL7
#### raporty/punkty/IleZlecenPP/IleZlecenPP_HL7
Raport ile zleceń dla danego płatnika zarejestrowały punkty pobra rejestrujące się samodzielnie przez HL7

# • » Punkty pobrań » Ile Zleceń Punkty pobrań » Ile zleceń dla płatnika - iCentrum
#### raporty/punkty/IleZlecenPP/IleZlecenPP_Platnik
Raport ile zleceń dla danego płatnika zarejestrowały punkty pobra rejestrujące się samodzielnie przez iCentrum

# • » Punkty pobrań » Ile Zleceń Punkty pobrań » Ile pakietów dla płatnika
#### raporty/punkty/IleZlecenPP/IleZlecenPP_pakiet
Raport ile pakietów gotówkowych zarejestrowano przez iCentrum w punkcie pobrań

# • » Punkty pobrań » Ile Zleceń Punkty pobrań » Ile zleceń dla płatnika - iCentrum - NOCKA
#### raporty/punkty/IleZlecenPP/ileZlecenPP_platnik_nocka
Raport ile zleceń dla danego płatnika zarejestrowały punkty pobra rejestrujące się samodzielnie przez iCentrum

# • » Punkty pobrań » Ile zleceń - Punkty Pobrań
#### raporty/punkty/IleZlecenPunktyPobran
Raport ilu pacjentów obsłużyły Punkty Pobrań w danym zakresie dni

# • » Punkty pobrań » Ile zleceń z HL7
#### raporty/punkty/IleZlecenZHL7
Ile zleceń w podanym zakresie dat przyjął punkt pobrań przez system dystrybucji zleceń HL7?

# • » Punkty pobrań » Obrót na osobę w punkcie
#### raporty/punkty/ObrotPunktOsoba

        Raport przedstwia obrót wygenerowany przez osobę, w danym punkcie pobrań
        oraz w podanym zakresie czasu

# • » Punkty pobrań » Sprzedaż gotówkowa Punkty Pobrań
#### raporty/punkty/RaportZeSprzedazyGotowkowejPracownik
Raport Ze Sprzedaży Gotówkowej Pakietów w podziale na Pracowników Punkty Pobrań wykonany z baz laboratoryjnych, zawiera tylko płatne gotówką badania/pakiety.
Uwaga, w przypadku pakietów nie posiadających cen (sumujących ceny składowych) wartość sprzedaży będzie sumowana po stronie badań, a nie pakietów.
Pakiety wyłączone z systemu premiowego dla PP: PKLIPID, PKELEKN, PKMOROZ, PKTKRCU, PKTKCIN, PKDIACR, MOCZ+OS, PKTKRCP, LIPID, PKWBAD, WBKZKB

# • » Punkty pobrań » Analiza struktury Klientów gotówkowych
#### raporty/punkty/StatystykaPacjentGotowkowy
Analiza struktury Klientów płacących gotówką lub za pomocą Sklepu Internetowego

# • » Punkty pobrań » Wymazy po punktach pobrań - TESTS
#### raporty/punkty/WymazyCOVID
Raport zawiera informacje o wykonanwych wymazach covidowych w poszególnych punktach pobrań.
    Źródła danych: Wymazy - nocka, Informacje o punktach pobrań - BIC

# • » Punkty pobrań » Dodatkowa sprzedaż gotówkowa - punkty pobrań 3
#### raporty/punkty/dzienna_sprzedaz_kanal_3
Raport przedstawiający dzienną dodatkową sprzedaż gotówkową na poziomie laboratorium

# • » Punkty pobrań » Dodatkowa sprzedaż gotówkowa - laboratoria 3
#### raporty/punkty/dzienna_sprzedaz_lab_3
Raport przedstawiający dzienną dodatkową sprzedaż gotówkową na poziomie laboratorium

# • » Punkty pobrań » Dodatkowa sprzedaż gotówkowa - laboratoria z podziałem TEST
#### raporty/punkty/dzienna_sprzedaz_lab_z_podzialem
Raport przedstawiający dzienną dodatkową sprzedaż gotówkową na poziomie laboratorium

# • » Punkty pobrań » Dodatkowa sprzedaż gotówkowa - laboratoria z podziałem multi TEST
#### raporty/punkty/dzienna_sprzedaz_lab_z_podzialem_multi
Raport przedstawiający dzienną dodatkową sprzedaż gotówkową na poziomie laboratorium

# • » Narzędzia
#### raporty/tools

# • » Narzędzia » Alert SMS
#### raporty/tools/AlertSMS
Wysyłka informacyjnego sms od Grupy Alab do zdefiniowanej grupy odbiorców.
Max długość wiadomości to 160 znaków, polskie litery zostaną zamienione na odpowiedniki ASCII.
Raport domyślnie pokazuje tylko podgląd wiadomości i listę odbiorców, aby wysłać alert zaznacz
pole "Wyślij na prawdę".
Definicje grup odbiorców w pliku /var/www/reporter/config_files/alert_sms_grupy_odbiorcow.xlsx
- jedna zakładka to jedna grupa odbiorców, nazwiska odbiorców z kolumny A, nr tel z B.

BŁĘDY KONFIGURACJI:
Błąd importu: [Errno 2] No such file or directory: '/home/adamek/alab/reporter/backend-reporter/raporty/tools/../../../config_files/alert_sms_grupy_odbiorcow.xlsx'

jeśli wystąpiły błędy, wczytana konfiguracja może być nieaktualna!

# • » Narzędzia » Import cen do SNR
#### raporty/tools/ImportCen

Import cen z arkusza XLSX. Plik musi zawierać dokładnie 1 arkusz. W arkuszu muszą się znajdować co najmniej kolumny Badanie i Cena.
Na właściwy cennik wskazują pola:
 - Laboratorium i Cennik (symbole) - dla cenników gotówkowych
 - Numer K lub NIP i Umowa (identyfikator umowy/aneksu/PU) - dla cenników klientów
Pola te mogą być albo wypełnione poniżej (import wszystkich cen w jedno miejsce) albo jako kolumny w arkuszu (jednorazowy import do wielu cenników).
Jest też możliwość importu cen do wszystkich cenników gotówkowych (aktywnych).

Uruchomienie raportu bez wpisania kodu potwierdzenia wyświetli tylko jakie zmiany zostałyby naniesione i poda kod potwierdzenia.
Aby faktycznie nanieść zmiany na cenniki należy przekleić podany kod potwierdzenia.
    


# • » Narzędzia » Prezlecenia - przedłuż prezlecenie
#### raporty/tools/PrzedluzPrezlecenie
Wprowadź kod vouchera, który ma zostać przedłużony

# • » Narzędzia » Prezlecenia - przedłuż generacje prezleceń
#### raporty/tools/PrzedluzPrezlecenieGeneracje
Wprowadź id generacji, który ma zostać przedłużony

# • » Narzędzia » Przenoszenie klientów między bazami
#### raporty/tools/PrzenoszenieKlientow

Wybierz laboratorium źródłowe i docelowe. Podaj symbole całych płatników do przeniesienia i/lub pojedynczych zleceniodawców.
Zleceniodawców gotówkowych można przenosić tylko posługując się symbolami zleceniodawców.
Po pierwszym uruchomieniu dane zostaną zweryfikowane, podana zostanie lista zmian do naniesienia w SNR i kod potwierdzenia.
Podanie kodu potwierdzenia przy kolejnym uruchomieniu jest niezbędne do właściwego naniesienia zmian.
    

# • » Narzędzia » Słowniki WCF
#### raporty/tools/SlownikiWCF
Wybierz słownik aby go pobrać. Żeby zaktualizować - wybierz plik.


# • » Narzędzia » Prezlecenia - unieważnij prezlecenie
#### raporty/tools/UniewaznijPrezlecenie
Wprowadź kody voucherów, które mają zostać anulowane oddzielone przecinkiem

# • » Narzędzia » Vouchery - unieważnij generacje voucherów oreaz prezlecenia
#### raporty/tools/UniewaznijPrezlecenieGeneracje
Wprowadź kody generacji voucherów

# • » Narzędzia » Zablokuj odbiór wyników
#### raporty/tools/ZablokujOdbiorWynikow
Blokada odbioru wyników wg kodu kreskowego na stronie internetowej i w nowych wynikomatach
Blokada odbioru wyników na stronie internetowej i w nowych wynikomatach. UWAGA, obecnie blokada działa na podstawie kodów kreskowych. Uruchomienie raportu zbierze aktualnie istniejące kody z wybranych laboratoriów dla podanego nru PESEL i je zablokuje. PESEL zostanie również zapisany jako zablokowany, ale obecnie taka blokada nie działa.

# • » Narzędzia » Zarezerwuj numer faktury
#### raporty/tools/ZarezerwujNumerFaktury
Zarezerwój numer faktury dla danego typu, mpk oraz roku

