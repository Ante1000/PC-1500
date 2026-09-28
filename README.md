# Sharp PC-1500(A) – programowy UART 4800 / 9600 bps (TTL-232)

Nadawanie (`SEROUT`) i odbiór (`SERIN`) metodą bit-banging:
wejście **PB2** (CMT-IN, pin 27 złącza 60-pin), wyjście **PC7**, 8N1,
polaryzacja TTL (spoczynek = 1).

## Wersja 9600 bps (v53, gałąź `9600bps`)

| Plik | Opis |
|---|---|
| `pc1500_uart_installer-v54-9600.txt` | **aktualny** instalator 9600 bps + program testowy (TX, RX, echo) |
| `pc1500_uart_installer-v53-9600.txt` | pierwsza wersja 9600, **sprawdzona na PC-1500A** (ten sam kod maszynowy co v54) |
| `serout_v53_9600.asm`, `.lst` | nowy SEROUT 9600 (84 B, &41C5..&4218) |
| `serin_v53_9600.asm`, `.lst` | SERIN 9600 (123 B, &422A..&42A4) |
| `tools/build_9600.py` | asembluje oba źródła i wstawia linie POKE do instalatora |
| `tools/test_9600.py` | testy SEROUT i SERIN przy 9600 w symulatorze |

Instalacja tak jak dla v52: `NEW &42B0` w trybie PRO, `CLOAD`, `RUN`.
Terminal w PC ustaw na **9600 8N1**. Test odbioru uruchamia `RUN 530`. Program
pyta o M (0 = do 127 znaków) i o echo. Przy echo=1 odebrany tekst jest od razu
odsyłany do PC przez SEROUT, więc sprawdzasz oba kierunki naraz.

v54 różni się od v53 tylko programem w BASIC-u:

* Teksty PRINT mają najwyżej 22 znaki, a pytania INPUT 13–18. Wpisywana
  odpowiedź mieści się w tej samej linii wyświetlacza.
* Odebrany tekst jest wyświetlany po 26 znaków w linii (`DIM B$(0)*26`,
  linia 535; zwykła zmienna napisowa mieści tylko 16 znaków).
* Informacje po instalacji są widoczne ok. 2 s (`WAIT 128`).

**Użycie** jest takie samo jak w v52:

* `CALL SO` wysyła 1 znak z TX, `CALL SO,N` wysyła N znaków (1..128). N=0
  daje 1 znak, N=129..255 daje 128. N≥256 działa jak `CALL SO` bez zmiennej
  (1 znak), bo tych przypadków nie da się odróżnić. Zmienna N się nie zmienia.
* `CALL SI` / `CALL SI,M` zwraca długość w `RX+0` i w M (jak w v52). Timeouty
  30 s i 0,5 s są bez zmian.

**SEROUT v53** jest napisany od nowa (v51/v52 przy 9600 miał za mały zapas):

* Gałęzie dla bitu 0 i 1 mają tę samą długość, a zapis do PC7 odbywa się
  w obu w tym samym cyklu (±1). W starym kodzie gałąź „0” była o 5 cykli
  dłuższa, co przy 9600 to już ok. 4% bitu.
* Bit trwa 134 / 137 cykli (tablica MAME / instrukcja LH5801), idealnie 135,4.
  Bit stopu trwa 1,1–1,3 bitu.
* Bity są liczone znacznikiem (sentinel) w akumulatorze, a znaki w UH, więc nie
  ma zmiennych w pamięci. Poprawia to też błąd starego kodu, w którym
  `CALL SO,0` wysyłało 65536 znaków.
* Na starcie PC7 jest ustawiane w stan spoczynku (1) na ok. 1 bit przed
  pierwszym bitem startu.
* Zakończenie bajtu jest sprawdzane przez `BII A,&FF`, a nie flagą Z po `SHR`.
  Według instrukcji LH5801 przesunięcia nie ustawiają Z (MAME je ustawia),
  a symulator w trybie „instrukcja” to odwzorowuje.

**SERIN v53** to kod v52 z pętlą bitu dostrojoną do 9600 (`LDI UL,5` + 2×NOP
= 134,5 / 137,5 cyklu) i krótszym opóźnieniem do połowy bitu startu (`LDI UL,3`).

**Wyniki symulacji przy 9600** (`python3 tools/test_9600.py`): wszystkie
scenariusze z v52 przechodzą w obu tablicach cykli. Dodatkowo SEROUT: wszystkie
256 wartości bajtu, 128 znaków, N=0/200/300, stan spoczynku przed startem,
zbocza w granicach 0,11 bitu od idealnej siatki.

| | tablica MAME | instrukcja LH5801 |
|---|---|---|
| SERIN: dopuszczalna odchyłka nadajnika | −3,5…+5,5% | −5,0…+3,5% |
| SEROUT: dopuszczalna odchyłka odbiornika w PC | −4,5…+6,5% | −6,5…+4,0% |

Przy 9600 zapas jest mniejszy niż przy 4800, a wersja v53 **nie była jeszcze
sprawdzana na prawdziwym PC-1500A**. Jeśli pojawią się błędy, stałe można
zmienić przez POKE (każda jednostka LOP = 11 cykli ≈ 8% bitu):

| Adres | Domyślnie | Znaczenie |
|---|---|---|
| SO+41 | 7 | długość bitu startu (SEROUT) |
| SO+59 | 5 | długość bitu danych (SEROUT) |
| SO+75 | 10 | długość bitu stopu (SEROUT) |
| SI+67 | 3 | opóźnienie do połowy bitu startu (SERIN) |
| SI+78 | 5 | długość bitu (SERIN) |
| SI+33 / SI+106 | 18 / 77 | timeout 30 s / 0,5 s (SERIN) |

Między `CALL SO` a `CALL SI` BASIC potrzebuje kilku ms, co przy 9600 to kilka
znaków. Urządzenie powinno odczekać ok. 50 ms przed odpowiedzią. 9600 bps to
praktyczny limit tej metody: przy 19200 bit trwa ok. 68 cykli, czyli tyle, ile
sama najkrótsza pętla bitu.

---

## Wersja 4800 bps (v52)

| Plik | Opis |
|---|---|
| `pc1500_uart_installer-v52.txt` | instalator 4800 bps + program testowy w BASIC-u |
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
