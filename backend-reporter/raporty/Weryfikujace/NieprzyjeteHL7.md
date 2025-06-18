#### W raporcie widoczne sa zlecenia i badania, które zostały przesłane przez Klientów po HL-7, a nie zostały automatycznie zarejestrowane w laboratorium.

Należy wybrać:
* laboratorium, z którego pobierane zostanie zestawienie;
* zakres dat do sprawdzenia;

Opcjonalnie można wybrać system klienta do sprawdzenia. 

Na start zestawienie ignoruje zdublowane badania w zleceniu oraz pomija badania z nieprzyjętych w całości zleceń.


Zwrotnie dostajemy dwie tabele:

1. Zlecenia nieprzyjęte w całości
 
      W tabeli zawarte są informacje o zleceniach, które zostały przesłane do ALAB z systemu Klienta i żadna z usług nie została
   zarejestrowana w systemie Centrum.

   |                           Źródło                           |                   Dane zlecenia                   |     Pacjent     |            ZLecone usługi             |
   |:----------------------------------------------------------:|:-------------------------------------------------:|:---------------:|:-------------------------------------:|
   | *dane systemu klienta,<br/> z którego zostało wysłane zlecenie* | *dane infomacyjne zlecenia<br/> z systemu klienckiego* | *dane pacjenta* | *zlecone w systemie klienckim usługi* |


2. Nieprzyjęte pojedyncze badania ze zleceń

      W tabeli zawarte są informacje o zleceniach przesłanych przez Klienta, z których pojedyncze usługi nie zostały zarejestrowane 
   w systemie Centrum. W zestawieniu podany jest najbardziej prawdopodobny powód niezarejestrowania badania.

   |    Zlecenie w Centrum     |             Zlecenie HL7              |                                      Usługa                                       |                                          Problem                                          |
   |:-------------------------:|:-------------------------------------:|:---------------------------------------------------------------------------------:|:-----------------------------------------------------------------------------------------:|
   | *dane zlecenia w Centrum* | *dane zlecenia z<br/> systemu klienckiego* | *zlecona w systemie klienckim<br/> usługa, która nie została <br/>zarejestrowana w Centrum* | *wstępna identyfikacja problemu,<br/> przez który usługa nie została <br/>zarejestrowana w Centrum* |

   