# Sharp PC-1500(A) – programowy UART 1200–9600 bps

Nadawanie (`SEROUT`) i odbiór (`SERIN`) metodą bit-banging, 8N1:
wejście **PB0** (pin 9 złącza 60-pin) lub **PB2** (CMT-IN, pin 27), wyjście **PC7**,
polaryzacja TTL albo odwrócona.

| Plik | Opis |
|---|---|
| `pc1500_uart_installer-v6.1.txt` | **aktualny** instalator v6.1 + program testowy (TX, RX, echo) |
| `serout_v61.asm`, `serin_v61.asm` (+ `.lst`) | źródła v6.1 i listingi |
| `pc1500_uart_installer-v6.0.txt`, `serout_v60.asm`, `serin_v60.asm` (+ `.lst`) | v6.0: to samo bez wyboru polaryzacji (sprawdzone na PC-1500A) |
| `HELP_NEW_memory.md` | how to set `NEW` for PC-1500 / PC-1500A with CE-151…CE-163 modules (English) |
| `tools/` | asembler, symulator LH5801, budowanie linii POKE, testy (patrz niżej) |

## Instalacja

`NEW &4400` w trybie PRO (PC-1500A bez modułu pamięci; dla innych konfiguracji patrz
[HELP_NEW_memory.md](HELP_NEW_memory.md)), `CLOAD` (albo wpisanie programu), `RUN`. Instalator
zadaje pytania; samo ENTER wybiera wartość domyślną:

| Pytanie | Odpowiedź |
|---|---|
| `BAUDRATE (DEFAULT 4800)` | `1` = 1200, `2` = 2400, `4` = 4800, `9` = 9600, ENTER = 4800 |
| `RX PORT (DEFAULT PB0)` | `0` lub ENTER = PB0 (pin 9), `2` = PB2 (CMT-IN, pin 27) |
| `INVERSION (0=NO, 1=YES)` | `0` lub ENTER = normalnie (TTL), `1` = sygnał odwrócony (tylko v6.1) |

Przy innej odpowiedzi instalator piszczy i pyta ponownie. Samo ENTER działa,
bo ROM PC-1500 przy pustym INPUT nie zmienia zmiennej i pomija resztę linii,
a wartość domyślna jest wpisana tuż przed pytaniem. Ustawienia zmienisz,
uruchamiając instalator jeszcze raz (`RUN`).

## Użycie

Adresy dla RAM od &4000 (instalator wyświetla je po instalacji):

| Wywołanie | Działanie |
|---|---|
| `CALL &40C5` | wysyła 1 znak (pierwszy z bufora TX, &4300) |
| `CALL &40C5,N` | wysyła N znaków z TX (1…255; 0 → 1 znak, > 255 → 255); N się nie zmienia |
| `CALL &4130` | odbiera do 255 znaków do RX (&4200); długość w RC: `PEEK &41FF` |
| `CALL &4130,M` | odbiera najwyżej M znaków (0 lub > 255 → 255); długość w RC i w M |

| Adres | Zawartość |
|---|---|
| &40C5..&4118 | SEROUT (84 B) |
| &4130..&41A5 | SERIN (118 B) |
| &41FF | RC: liczba odebranych znaków (1 bajt, 0–255) |
| &4200..&42FE | RX: odebrane znaki (255 B) |
| &4300..&43FE | TX: znaki do wysłania (255 B) |
| od &4400 | program w BASIC-u (`NEW &4400`) |

Znaki odczytasz przez `PEEK (&4200 + I)` dla I = 0…D−1, gdzie `D = PEEK &41FF`.
Pierwszy znak musi przyjść w ciągu ok. 30 s, kolejne w odstępach < 0,5 s; po
M-tym (lub 255.) znaku SERIN wraca od razu. Oba czasy nie zależą od szybkości.

## Program testowy

Po instalacji instalator przechodzi do testów (terminal w PC ustaw na tę samą
szybkość, 8N1, i tę samą polaryzację):

* Test TX wysyła `H` (`CALL SO`), a potem `_HELLO` (`CALL SO,N`, N = 6);
  w terminalu widać `H_HELLO`.
* Test RX (`RUN 530`) odczytuje z kodu zainstalowaną szybkość, port i polaryzację
  i pokazuje je w linii `WAITING 4800 PB0...` (`... PB0 INV...` przy inwersji).
  Gdy w pamięci nie ma kodu v6.1, wyświetla `NO v6.1 CODE! RUN 10`.
* Pytanie `MAX (0=255)?` ustala M, a `ECHO (0=NO, 1=YES)` (ENTER = 0) włącza
  odsyłanie odebranego tekstu do PC przez SEROUT.
* Odebrany tekst jest wyświetlany po 26 znaków w linii.

## Polaryzacja (v6.1)

| INVERSION | spoczynek i bit „1” | bit startu i bit „0” |
|---|---|---|
| 0 (normalnie, TTL-UART, np. adapter USB–TTL) | stan wysoki | stan niski |
| 1 (odwrócona) | stan niski | stan wysoki |

Ustawienie dotyczy jednocześnie wyjścia TX (PC7) i wejścia RX (PB0/PB2).
Odwrócona polaryzacja to ta sama kolejność stanów co w RS-232, ale **przy
poziomach 0/5 V**. Prawdziwego RS-232 (±12 V) nie wolno podłączać bezpośrednio;
układ MAX232 sam odwraca sygnał, więc z nim wybierz INVERSION = 0.

Przy inwersji instalator od razu ustawia PC7 w stan spoczynku (niski). ROM
ustawia PC7 = 1 tylko przy starcie komputera (inicjalizacja portów), więc po
włączeniu PC-1500 linia TX jest w stanie „0” (break) aż do pierwszego `CALL SO`.
Jeśli to przeszkadza urządzeniu po drugiej stronie, wykonaj po włączeniu:
`POKE# &F008, (PEEK# &F008) AND &7F`.

Przy niezgodnej polaryzacji SERIN odbiera przypadkowe znaki (odwrócona linia
wygląda jak ciąg bitów startu), a terminal w PC pokazuje śmieci zamiast tekstu.
Wtedy najpierw sprawdź ustawienie INVERSION.

W kodzie inwersja zamienia rozkazy tej samej długości: przy nadawaniu
`ORI #(Y),&80` ↔ `ANI #(Y),&7F` (po 17 cykli), przy odbiorze `BZR` ↔ `BZS`.
Czasy są więc identyczne jak bez inwersji, a przy INVERSION = 0 kod v6.1 jest
bajt w bajt taki sam jak v6.0.

## Podłączenie

| Sygnał | Pin złącza 60-pin | Nóżka LH5811 |
|---|---|---|
| RX: PB0 | 9 | 9 |
| RX: PB2 (CMT-IN) | 27 | 11 |
| TX: PC7 | 10 | – |
| GND | 52–55 | |
| VCC (ok. 4,8 V) | 11, 12, 41, 42 | |

* Na PB0 daj **rezystor podciągający 10 kΩ do VCC**: to wejście CMOS bez
  podciągania, a bez adaptera linia „pływa”. Bezpieczniej podawać sygnał przez
  diodę Schottky'ego (katoda od strony adaptera) z tym rezystorem albo przez
  rezystor szeregowy 1–2,2 kΩ; wejścia znoszą najwyżej VCC + 0,3 V.
* Według TRM pin 9 (PB0) w części egzemplarzy może być niepodłączony
  (zależnie od miesiąca produkcji).
* Progi wejścia (TRM): „0” ≤ 0,8 V, „1” ≥ 2,4 V, więc adapter 3,3 V też działa.
* Szybki test pinu bez SERIN (adapter podłączony, w spoczynku):
  `PRINT (PEEK# &F00F) AND 1` daje 1 dla PB0 (`AND 4` daje 4 dla PB2); po
  zwarciu pinu do GND wynik ma być 0.
* ROM PC-1500 wpisuje do rejestru kierunku portu B (&F00D) wyłącznie &00, więc
  port B jest zawsze wejściem; SERIN dodatkowo zeruje bit swojego wejścia.

## Stałe czasowe

Kod jest ten sam dla wszystkich szybkości. Instalator wpisuje w linie POKE
tylko zmienne BASIC-a:

| bps | KB (bit) | KH (pół bitu) | KT (stop) | KS = KB+2 (start) | KI = KB+7 (spoczynek) |
|---|---|---|---|---|---|
| 1200 | 91 | 47 | 106 | 93 | 98 |
| 2400 | 42 | 21 | 50 | 44 | 49 |
| 4800 | 17 | 12 | 26 | 19 | 24 |
| 9600 | 5 | 3 | 10 | 7 | 12 |

Bit trwa 79 + 11·KB cykli (SEROUT) i 79,5 + 11·KB (SERIN) według tablicy MAME;
według instrukcji LH5801 o 3 cykle więcej. Port: PB0 → `DB` = &FE, `BM` = 1;
PB2 → `DB` = &FB, `BM` = 4. KH dobrałem w symulatorze tak, żeby tolerancja odbioru
była wyśrodkowana dla obu tablic cykli, a KT tak, żeby ramka nadawana miała co
najmniej 10,1 bitu. Przy 9600 stałe są takie same jak w wersji sprawdzonej
wcześniej na PC-1500A; przy 4800 średni bit nadawany jest taki sam jak w
oryginalnym SEROUT.

Wyniki symulatora (tolerancja szybkości nadawcy przy odbiorze; tablica MAME / instrukcja):

| bps | odbiór | bit stopu przy nadawaniu |
|---|---|---|
| 1200 | −5,5…+5,5% / −5,5…+5,5% | 1,10 / 1,13 bitu |
| 2400 | −5,0…+5,5% / −5,5…+5,0% | 1,11 / 1,16 bitu |
| 4800 | −4,5…+5,5% / −5,5…+4,5% | 1,11 / 1,21 bitu |
| 9600 | −3,5…+5,5% / −5,0…+3,5% | 1,14 / 1,34 bitu |

Timeouty SERIN można zmienić po instalacji: `POKE &4130+32, n` (1. znak,
n × ok. 1,67 s, domyślnie 18 ≈ 30 s) i `POKE &4130+105, n` (między znakami,
n × ok. 6,5 ms, domyślnie 77 ≈ 0,5 s).

## Jak to działa

* **SEROUT** wysyła bity z przesuwanego akumulatora (znacznik w bicie 7 liczy
  bity), licznik znaków jest w UH. Gałęzie dla bitu 0 i 1 mają tę samą długość,
  a zapis do PC7 odbywa się w obu w tym samym cyklu (±1). Na starcie PC7 jest
  ustawiane w spoczynek na ok. 1 bit przed pierwszym bitem startu. Zmienna N
  nie jest zmieniana (powrót z C = 0).
* **SERIN** czeka na spoczynek, potem na zbocze bitu startu (pętla 33 cykli),
  sprawdza środek bitu startu (krótkie zakłócenia są ignorowane) i próbkuje
  8 bitów w środku. Bufor RX zaczyna się od początku strony pamięci, więc
  liczba znaków to młodszy bajt adresu końca; trafia do RC i do X, a powrót
  z C = 1 każe ROM-owi wpisać X do zmiennej z `CALL SI,M`.
* Obie procedury wyłączają przerwania na czas pracy (`RIE`).

## Narzędzia (Python 3, bez dodatkowych bibliotek)

| Plik | Opis |
|---|---|
| `tools/build_v61.py`, `tools/build_v60.py` | asemblują źródła, tworzą `.lst` i podmieniają linie POKE w instalatorze |
| `tools/test_v61.py`, `tools/test_v60.py` | pełne testy w symulatorze, np. `python3 tools/test_v61.py 4800:0:1` (szybkość:port:inwersja) |
| `tools/test_serin.py` | zestaw testów: `test_serin.py <instalator> <baud> <bit portu B> <inwersja>` |
| `tools/lh5801sim.py` | symulator LH5801 z portami LH5811 i wykonywaniem instalatora (POKE, INPUT, IF) |
| `tools/asm.py` | mały asembler LH5801 (także pseudo-rozkazy MARK/SPACE/BMK/BSP dla polaryzacji) |
| `tools/build_common.py` | wspólne funkcje skryptów budujących |

Symulator liczy cykle według rdzenia MAME i, w drugim przebiegu, według tabeli
z instrukcji LH5801. Port B zachowuje się jak w LH5811 (bit ustawiony jako
wyjście zwraca zatrzask), a pozostałe nóżki czytają się jako 1, więc test
przechodzi tylko wtedy, gdy SERIN ustawi i czyta właściwy bit. Testy obejmują
m.in. wszystkie 256 wartości bajtu, 255 znaków jeden za drugim, `CALL SI,M` dla
wielu M, timeouty 30 s i 0,5 s, zakłócenia, 1–2 bity stopu, nadajnik ±2% i
dekodowanie SEROUT przez odbiornik PC z odchyłką ±2%.

## Ograniczenia

* Podczas oczekiwania (do 30 s) przerwania są wyłączone i klawisz BREAK nie
  działa. ROM włącza przerwania ponownie przy obsłudze klawiatury.
* Między `CALL SO` a `CALL SI` BASIC potrzebuje kilku ms. Jeśli urządzenie
  odpowiada natychmiast, początek odpowiedzi może zostać zgubiony; urządzenie
  powinno odczekać ok. 50 ms przed odpowiedzią.
* 9600 bps to górna granica tej metody (sam narzut pętli bitu to ok. 80 cykli
  z 135).
