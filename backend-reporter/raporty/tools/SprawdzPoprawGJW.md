#### Sprawdzenie/poprawa danych w GJW.

Aby znaleźć wynik należy wpisać kod kreskowy zlecenia.

Wykonanie wpisu jedynie w polu PESEL zwróci podstawowe informacje z GJP, takie jak:

* kod kreskowy zlecenia;
* PESEL i data urodzenia pacjenta;
* laboratorium;
* datę i numer zlecenia;
* id zlecenia;
* datę pojawienia się zlecenia w GJW;
* daty ostatnich zapytań o pliki do GJW;
* nazwy plików.

Pole PESEL/data urodzenia można wypełnić dla dodatkowej weryfikacji i odpytania serwisu GJW.

Zwrotnie uzyskamy wtedy:

* status wyników
* status plików do pobrania
* możliwość podejrzenia plików PDF

Przykładowe efekty odpytania GPJ o wynik:

|                         Status usług                          |                                                                                                                                                   Interpretacja                                                                                                                                                    |
|:-------------------------------------------------------------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
|  Results - OK; <br/>File -OK;<br/>widoczne pliki do pobrania  |                                                                                                                             wyniki badań są możliwe do pobrania ze strony internetowej                                                                                                                             |
| Results - OK; <br/>File - ERROR;<br/> brak plików do pobrania | Jeżeli  w odpowiedzi statusu pliku pojawi się wpis "The result contains sensitive data" <br/>i w wierszu z wynikami pojawi się przy którymkolwiek z badań wpis<br/> ""isSensitive": true" <br/>- wyniku nie da się poprać poprzez GJW z uwagi na zarejestrowanie badania, którego wyniki należy odebrać osobiście. |
|                                                               |                                                                                                                                                                                                                                                                                                                    |

__Żeby pobrać / odświeżyć dane z Centrum, należy wybrać laboratorium, z którego mają zostać pobrane wyniki oraz
zaznaczyć
zahaczkę "Pobierz zlecenie z Centrum".__

