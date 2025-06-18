# Użytkownicy i uprawnienia w systemie

## Opis systemu uprawnień

W systemie Alab Reporter funkcjonuje rozbudowany mechanizm zarządzania uprawnieniami do raportów i grupowania uprawnień
w role użytkowników. Zarządzanie dostępami odbywa się na dwóch płaszczyznach:

* dostęp do poszczególnych raportów / narzędzi
* dostęp terytorialny, do raportów gdzie jest to adekwatne. Zarządzanie odbywa się na poziomie laboratoriów, użytkownik
  może mieć dostęp do wybranych lub wszystkich laboratoriów

Dostępy do poszczególnych raportów są zebrane w role. Użytkownikom można nadawać jedną lub wiele ról, a także 
uprawnienia do poszczególnych raportów. To ostatnie powinno być stosowane tylko w ostateczności, w pojedynczych i
nietypowych sytuacjach. Jeśli te same pojedyncze raporty są przypisywane większej ilości osób, to powinno to zostać
zgłoszone jako modyfikacja istniejącej / utworzenie nowej roli. Dzięki temu nowe raporty pasujące do tej roli będą
mogły być do niej dodawane i stawać się dostępne dla użytkowników bez modyfikacji ich indywidualnych uprawnień. 

__Uwaga__: w chwili obecnej nie ma możliwości nadania jednemu użytkownikowi różnych uprawnień terytorialnych do różnych
ról/raportów, nawet jeśli da się taką konfigurację ustawić w panelu administracyjnym. Użytkownik zawsze będzie miał
maksymalny zakres terytorialny ze wszystkich swoich uprawnień.

## Role użytkowników w systemie

Poniżej przedstawione są aktualne role użytkowników w systemie i zawieranie się mniejszych ról w większych. Kolejna 
tabela przedstawia dostępy do poszczególnych raportów / narzędzi dla wszystkich ról.