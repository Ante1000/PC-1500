# Sharp PC-1500(A) – programowy UART 4800 bps (TTL-232)

Nadawanie (`SEROUT`) i odbiór (`SERIN`) metodą bit-banging:
wejście **PB2** (CMT-IN, pin 27 złącza 60-pin), wyjście **PC7**, 8N1, 4800 bps,
polaryzacja TTL (spoczynek = 1).

| Plik | Opis |
|---|---|
| `pc1500_uart_installer-v52.txt` | **aktualny** instalator + program testowy w BASIC-u |
| `serin_v52.asm`, `serin_v52.lst` | źródło i listing nowego SERIN (LH5801) |
| `tools/` | asembler, symulator LH5801 i testy (Python 3) |
| `pc1500_uart_installer-v51.txt` | poprzednia wersja (SERIN nie działał) |
| `pc1500_uart_installer-v47 ...txt` | wersja odbierająca 1 znak (wzorzec czasów) |

SEROUT jest w v52 **bajt w bajt taki sam jak w v51**.

## Mapa pamięci (RAM od &4000)

| Adres | Zawartość |
|---|---|
| &40C5..&4144 | bufor TX (128 B) |
| &4145 | RX+0: liczba odebranych znaków |
| &4146..&41C4 | RX+1..RX+127: odebrane znaki |
| &41C5..&4229 | SEROUT |
| &422A..&42A2 | SERIN v52 (121 B) |
| od &42B0 | program BASIC (`NEW &42B0` w trybie PRO) |

## Użycie SERIN

```
CALL SI            odbierz do 127 znaków
N=10 : CALL SI,N   odbierz najwyżej N znaków (1..127; 0 lub >127 = 127)
```

* Po wywołaniu SERIN czeka na pierwszy znak **do ~30 s**. Jeśli nic nie
  przyjdzie, wraca z `PEEK RX = 0`.
* Każdy znak trafia do kolejnego bajtu od `RX+1`. Jeśli następny znak nie
  pojawi się w ciągu **~0,5 s**, SERIN kończy odbiór.
* Po odebraniu 127 znaków (albo N przy `CALL SI,N`) SERIN wraca od razu. Resztę
  pakietu pomija.
* Wynik: `PEEK RX` = liczba znaków, a przy `CALL SI,N` również **N = liczba
  znaków**. Uwaga: N jest nadpisywane, więc przed kolejnym wywołaniem trzeba
  je ustawić ponownie.

```
10 N = 20 : CALL SI, N
20 IF N = 0 PRINT "BRAK DANYCH" : END
30 FOR I = 1 TO N : PRINT CHR$ (PEEK (RX + I)); : NEXT I
```

Test odbioru w instalatorze: `RUN 530`. Program pyta o M (0 = do 127 znaków),
wyświetla liczbę znaków i tekst po 16 znaków w linii (znaki sterujące jako `.`).
Sprawdza też, czy N z `CALL SI,N` zgadza się z `PEEK RX`.

## Co było źle w SERIN v51

1. **Złe skoki względne (główna przyczyna).** LH5801 ma osobne kody skoków
   w przód (`89`=BZR+, `8B`=BZS+) i w tył (`99`=BZR−, `9E`=BCH−). Przesunięcie
   jest liczbą **bez znaku** (0..255). W v51 wpisano przesunięcia w kodzie
   U2 (`&F6`, `&F2`, `&FC`, `&EF`, `&DC`, `&FB`, `&C1`), jak dla Z80 czy 6502.
   Przykład: pierwsze `99 F6` (SI+30) miało cofnąć o 10 bajtów, a cofało
   o 246, czyli do &4154, w środek bufora RX. Procesor wykonywał tam zera
   (`00` = SBC XL) aż do SEROUT pod &41C5. SEROUT **wysyłał 1 znak z bufora TX**
   i wracał do BASIC-a. Stąd objaw „nie odbiera, ale się nie zawiesza”.
   Symulator odtwarza to dokładnie: powrót po 3 ms, pusty RX, 10 zmian na PC7.
2. Pierwszy znak trafiał do `RX+0` (`SIN X` przy X = RX), czyli w miejsce długości.
3. Na końcu zapisywane było 0 (terminator), a nie liczba znaków. Test w BASIC-u
   liczył znaki do bajtu 0, więc nie działał dla danych zawierających 0.
4. Pętla bitu (`DEC UH` zamiast `LOP`) miała inne czasy niż sprawdzona v47.
5. Timeout wynosił ~1 s dla każdego znaku zamiast 30 s i 0,5 s.
6. Test BASIC, linia 680: `IF ... THEN I = 127` wymaga na PC-1500 `LET`
   (inaczej ERROR 19).

## Jak działa SERIN v52

1. `RIE`, ustalenie limitu m (z X), `RX+0 := m` (licznik pozostałych znaków),
   X := RX+1, PB2 jako wejście (`&F00D` bit 2 = 0), Y := &F00F (port B).
2. **WH**: czekaj, aż linia będzie w stanie spoczynku (1). **WL**: czekaj na
   zbocze 1→0 (bit startu). Obie pętle mają ten sam licznik czasu
   (UL×UH×A, 33 cykle/obieg): 18·256·256 obiegów ≈ 30 s dla pierwszego znaku,
   77·256 obiegów ≈ 0,5 s między znakami. Pętla WH chroni przed fałszywym
   startem, gdy bit 7 znaku jest 0 (każdy znak ASCII), i przed linią stale w 0.
3. Pół bitu dalej SERIN sprawdza, czy linia nadal jest w 0. Jeśli nie, to było
   zakłócenie i SERIN wraca do WL.
4. Odczyt 8 bitów pętlą **identyczną bajt w bajt z v47**
   (`6A 13 88 02 FD 5D 04 FB 89 01 F9 D1 FD 62 99 10`). Czas od zbocza do
   pierwszej próbki jest też taki sam jak w v47 (±1 cykl).
5. `SIN X` zapisuje znak, a licznik w `RX+0` maleje o 1. Przy 0 następuje koniec.
   W przeciwnym razie wraca do WH z timeoutem 0,5 s. Obsługa znaku trwa ok.
   0,4 bitu, więc znaki nadawane jeden za drugim (1 bit stopu) są odbierane
   bez strat.
6. Koniec: `A = XL − (RL+1)` = liczba znaków → `RX+0`, X := liczba, `SEC`, `RTN`.

## Pkt 9: zwracanie długości

Bajt długości na początku bufora (jak w „stringu Pascala”) to standardowe
i dobre rozwiązanie. Jest lepsze od terminatora 0, bo działa też dla danych
binarnych. Zostało, zgodnie ze specyfikacją.

Dodatkowo v52 zwraca długość **w zmiennej z CALL**. Sprawdziłem to
w deasemblacji ROM (BCMD_CALL, &C863..&C8B3):

* `CALL adr,N`: ROM ładuje wartość N do rejestru X.
* Po `RTN` z **C=1** ROM zapisuje X z powrotem do N (`STX U`,
  `SJP ARUINT2ARX`, `VMJ $08`). Przy C=0 zmienna się nie zmienia (dlatego
  SEROUT i stary SERIN kończyły się `REC`).
* `CALL adr` bez zmiennej: ROM ustawia znacznik „brak zmiennej” i ignoruje C,
  więc `SEC` jest wtedy nieszkodliwe. X zawiera wtedy adres powrotu w ROM
  (XH ≠ 0) i na tym opiera się też rozpoznawanie „brak N” w SEROUT.

Wystarczy więc `N=M : CALL SI,N` i N od razu zawiera liczbę znaków, bez `PEEK`.

Inna możliwość: `CALL adr,A$`. ROM przekazuje wtedy adres bufora napisu, a po
C=1 kopiuje A bajtów do A$. Ma to jednak dwie wady: napisy na PC-1500 mają
najwyżej 80 znaków, a z tego samego wejścia nie da się odróżnić zmiennej
liczbowej od napisowej. Dlatego tego nie wprowadzałem.

## Weryfikacja (symulator)

`python3 tools/test_serin.py` wykonuje linie POKE instalatora i wywołuje
SERIN w symulatorze LH5801 (semantyka i cykle według rdzenia MAME oraz,
w drugim przebiegu, według tabeli z instrukcji LH5801). Na PB2 podawany jest
przebieg UART 4800 8N1. Wszystkie scenariusze przechodzą w obu tablicach:

* wszystkie 256 wartości bajtu, ciągi wysyłane jeden za drugim, 127 i 200 bajtów
  (po 127. znaku natychmiastowe wyjście), `CALL SI,M` dla M = 1, 3, 5, 0, 127,
  128, 255, 300, 65535
* timeout 30 s (znak w 29. s odebrany, w 31. s nie), przerwy 400 ms (odbiór
  trwa) i 600 ms (koniec)
* linia stale w 0, krótkie zakłócenie 20 µs, 1 lub 2 bity stopu, nadajnik ±2%
* poza `RX..RX+127` nic w pamięci nie jest zmieniane
* SEROUT (bez zmian) nadaje „HELLO”

Okno tolerancji prędkości nadajnika wynosi ok. −6,5%…+2,5–3,5% (zależnie od
tablicy cykli) i jest **identyczne jak w v47**, także przy ciągłym strumieniu
znaków. v52 działa więc wszędzie tam, gdzie działała v47.
`python3 tools/demo_v51_bug.py` odtwarza w symulatorze błąd v51 opisany wyżej.

Zmiany w `serin_v52.asm` wprowadza się poleceniem `python3 tools/build_serin.py`.
Asembluje ono kod, tworzy listing i podmienia linie 280–355 instalatora.

## Strojenie (POKE po instalacji, SI = &422A)

| Adres | Domyślnie | Znaczenie |
|---|---|---|
| SI+33 | 18 | timeout 1. znaku, 1 jednostka ≈ 1,67 s (18 ≈ 30 s) |
| SI+104 | 77 | timeout między znakami, 1 jednostka ≈ 6,5 ms (77 ≈ 0,5 s) |
| SI+78 | &13 | opóźnienie w pętli bitu (jak v47) |
| SI+67 | 7 | opóźnienie do połowy bitu startu (jak v47) |

Pętla bitu z v47 jest ok. 3% wolniejsza niż 4800 bps (według tablic cykli),
a pierwsza próbka jest przesunięta tak, żeby to skompensować. Jeśli z jakimś
adapterem pojawią się przekłamane znaki (zwłaszcza w bitach 6–7), można
wypróbować `POKE SI+78,&12 : POKE SI+67,10`. W symulatorze daje to okno
symetryczne, ok. ±5%.

## Ograniczenia

* Podczas oczekiwania (do 30 s) przerwania są wyłączone i klawisz BREAK nie
  działa. To samo dotyczy SEROUT. ROM włącza przerwania ponownie przy
  obsłudze klawiatury.
* Między `CALL SO` a `CALL SI` BASIC potrzebuje kilku ms. Jeśli urządzenie
  odpowiada natychmiast, początek odpowiedzi może zostać zgubiony. Urządzenie
  powinno odczekać ok. 50 ms przed odpowiedzią.
