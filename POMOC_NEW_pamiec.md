# Jak ustawić `NEW` przed instalatorem SEROUT/SERIN (v6.x)

Instalator (`pc1500_uart_installer-v6.1.txt`, także v6.0) zajmuje **pierwszy 1 KB pamięci RAM**,
licząc od jej początku. Gdzie ten początek jest, zależy od modelu i od modułu pamięci.
Zanim wczytasz instalator, ustaw w trybie PRO `NEW` tak, żeby BASIC zaczynał się
**za tym kilobajtem**.

## Zasada (działa w każdej konfiguracji)

1. Sprawdź początek pamięci RAM (w trybie RUN):
   ```
   PRINT PEEK &7863
   ```
   Wynik to starszy bajt adresu początku RAM, np. `64` = &40, czyli RAM od &4000.
2. Oblicz: **`NEW` = wynik × 256 + &400** i wpisz to w trybie PRO.

| `PEEK &7863` | Początek RAM | Wpisz w trybie PRO |
|---|---|---|
| 64 (&40) | &4000 | `NEW &4400` |
| 56 (&38) | &3800 | `NEW &3C00` |
| 32 (&20) | &2000 | `NEW &2400` |
| 0 (&00) | &0000 | `NEW &400` |

Co leży w tym kilobajcie (A0 = początek RAM):

| Adres | Zawartość |
|---|---|
| A0 … A0+&C4 | obszar systemowy (RESERVE); tu zaczyna się też zwykłe `NEW 0` |
| A0+&C5 | SEROUT (wywołanie TX) |
| A0+&130 | SERIN (wywołanie RX) |
| A0+&1FF | RC: liczba odebranych znaków |
| A0+&200 … A0+&2FE | bufor RX (255 znaków) |
| A0+&300 … A0+&3FE | bufor TX (255 znaków) |
| od A0+&400 | program w BASIC-u |

Instalator sam liczy wszystkie adresy z `PEEK &7863` i sprawdza, czy BASIC zaczyna się
co najmniej od A0+&400. **Uwaga:** komunikaty v6.0/v6.1 zawsze podpowiadają „NEW &4400”
(wartość dla PC-1500A bez modułu). Przy modułach kieruj się tabelą poniżej.

## Tabela konfiguracji

Oznaczenia pewności: ✅ potwierdzone (pomiar lub dokumentacja Sharp), 🔶 wywnioskowane z budowy
podobnego modułu (sprawdź `PEEK &7863`), ❓ niepewne.

| Konfiguracja | Moduł | Początek RAM | Koniec RAM | **`NEW`** | TX: `CALL` (SO) | RX: `CALL` (SI) | Wolne na BASIC po `NEW` | Pewność / uwagi |
|---|---|---|---|---|---|---|---|---|
| **PC-1500** (2 KB) | – | &4000 | &47FF | **`NEW &4400`** | &40C5 | &4130 | ok. 1 KB | ✅ Instalator (ok. 4,1 KB) się nie zmieści, patrz „PC-1500 z 2 KB” niżej |
| **PC-1500A** (6 KB) | – | &4000 | &57FF | **`NEW &4400`** | &40C5 | &4130 | ok. 5 KB | ✅ konfiguracja sprawdzona na sprzęcie |
| PC-1500 + **CE-151** | 4 KB RAM | &3800 | &4FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 5 KB | 🔶 jak CE-155, tylko mniejszy |
| PC-1500A + **CE-151** | 4 KB RAM | &3800 | &5FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 9 KB | 🔶 |
| PC-1500 + **CE-155** | 8 KB RAM | &3800 | &5FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 9 KB | ✅ (bez instalatora `MEM` = 10042) |
| PC-1500A + **CE-155** | 8 KB RAM | &3800 | &6FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 13 KB | ✅ (bez instalatora `MEM` = 14138) |
| PC-1500 + **CE-157** | 4 KB RAM + ROM Katakana | &3800 | &4FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 5 KB | 🔶 moduł japoński; RAM prawdopodobnie jak CE-151 |
| PC-1500A + **CE-157** | 4 KB RAM + ROM Katakana | &3800 | &5FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 9 KB | 🔶 |
| PC-1500 + **CE-159** | 8 KB RAM z baterią | &3800 | &5FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 9 KB | ✅ elektrycznie jak CE-155 (instrukcja serwisowa: „10K bytes including reserve area”). Na czas instalacji wyłącz zabezpieczenie przed zapisem. Jedno ze źródeł podaje początek &2000: jeśli `PEEK &7863` = 32, użyj `NEW &2400`. |
| PC-1500A + **CE-159** | 8 KB RAM z baterią | &3800 | &6FFF | **`NEW &3C00`** | &38C5 | &3930 | ok. 13 KB | ✅ jak wyżej |
| PC-1500(A) + **CE-160** | ok. 7,6–7,8 KB, tylko do odczytu | ? | ? | **nie instaluj w CE-160** | – | – | – | ❓ Moduł z gotowymi programami, zapisywany programatorem CE-165. Kodu nie da się w nim zapisać; blok musi być w zapisywalnym RAM. Sprawdź `PEEK &7863`: jeśli pokazuje adres wewnątrz CE-160, instalacja nie zadziała. |
| PC-1500 + **CE-161** | 16 KB RAM z baterią | &0000 | &47FF | **`NEW &400`** | &00C5 | &0130 | ok. 17 KB | ✅ (`PEEK &7863` = 0 sprawdzone na sprzęcie). Uwaga: `NEW &4400` z komunikatu instalatora zmarnowałby cały moduł. Zabezpieczenie przed zapisem wyłączone. |
| PC-1500A + **CE-161** | 16 KB RAM z baterią | &0000 | &57FF | **`NEW &400`** | &00C5 | &0130 | ok. 21 KB | ✅ jak wyżej |
| PC-1500(A) + **CE-162E** | interfejs magnetofonu i drukarki (nie pamięć) | jak bez modułu | | jak bez modułu (`NEW &4400`) | &40C5 | &4130 | jak bez modułu | ❓ To nie jest pamięć, więc `NEW` się nie zmienia. Moduł przypuszczalnie zajmuje złącze 60-pin i linię CMT-IN (PB2), więc przewody UART trzeba podłączyć inaczej. |
| PC-1500 + **CE-163** | 2 × 16 KB RAM (banki) | &0000 | &47FF | **`NEW &400` w każdym używanym banku** | &00C5 | &0130 | ok. 17 KB na bank | 🔶 Patrz „Moduły z bankami” niżej. Bank przełącza zapis pod &5800/&5801. |
| PC-1500A + **CE-163** | 2 × 16 KB RAM (banki) | &0000 | &57FF | **`NEW &400` w każdym używanym banku** | &00C5 | &0130 | ok. 21 KB na bank | 🔶 jak wyżej; bank przełącza zapis pod &6800/&6801 |

„Wolne na BASIC” to przybliżenie (koniec RAM minus początek programu). Po `NEW` polecenie `MEM`
pokaże dokładną wartość; zmienne zabierają z tego trochę miejsca.

## Kolejność instalacji

1. Tryb PRO: `NEW` z tabeli (np. `NEW &3C00`).
2. `CLOAD` instalatora (albo wpisanie go) i `RUN`.
3. Odpowiedzi na pytania o szybkość, port i inwersję.
4. Po instalacji program testowy (`RUN 530`) sam znajdzie kod pod właściwymi adresami.

Nie dokładaj ani nie wyjmuj modułu po instalacji. Zmienia się wtedy początek RAM, a kod
i program w BASIC-u znikają lub leżą pod innymi adresami.

## Adresy we własnych programach

Nie wpisuj na sztywno `CALL &40C5`. Licz adresy tak jak program testowy, a program zadziała
w każdej konfiguracji:
```
A0 = PEEK &7863 * 256 : SO = A0 + &C5 : SI = A0 + &130
RC = A0 + &1FF : RX = A0 + &200 : TX = A0 + &300
```

## PC-1500 z 2 KB

Na PC-1500 bez modułu po `NEW &4400` zostaje tylko ok. 1 KB na BASIC, a instalator v6.1
zajmuje po tokenizacji ok. 4,1 KB (ok. 2,8 KB część instalacyjna i ok. 1,3 KB program
testowy), więc się nie zmieści. Najprościej:

1. Zainstaluj na PC-1500A (albo na PC-1500 z modułem, ale **z tym samym początkiem RAM
   &4000**, czyli bez modułu pamięci).
2. Zapisz sam kod i bufory na taśmę: `CSAVE M "UART"; &40C5, &43FF`.
3. Na PC-1500: `NEW &4400` w trybie PRO, potem `CLOAD M "UART"`.

Kod działa tylko pod tymi adresami, pod którymi został zainstalowany, bo ma wpisane numery
stron buforów. Obraz z `CSAVE M` przenoś więc tylko między konfiguracjami z tym samym
początkiem RAM. Szybkość, port i inwersja zostają takie, jak wybrano przy instalacji.
Potrzebny jest CE-150 (magnetofon).

## Moduły z bankami (CE-163 i nowoczesne moduły 64–128 KB)

- **Okno banku.** Okno &0000–&3FFF zmienia zawartość przy każdym przełączeniu banku. Blok
  SEROUT/SERIN i bufory (&0000–&03FF) istnieją tylko w tym banku, w którym je zainstalowano.
  Po przełączeniu na inny bank `CALL &C5` skoczyłoby w przypadkowe bajty. Zainstaluj więc
  kod w każdym banku, w którym chcesz go używać (przełącz bank, `NEW &400`, `CLOAD`, `RUN`),
  albo używaj tylko jednego banku.
- **Oprogramowanie modułu.** Moduły z programem obsługi banków na początku każdego banku
  wymagają własnego przesunięcia `NEW` (np. TRAMsoft: `NEW &100`). Ten program leży za
  obszarem systemowym, czyli tam, gdzie instalator v6.x kładzie SEROUT (A0+&C5).
  **v6.1 nadpisałby go.** Z takim modułem potrzebna jest wersja instalatora z przesuniętym
  blokiem (jeszcze jej nie ma).

## Skąd te dane

- Mapa pamięci, wartości `MEM`, zasada `NEW 0` = początek RAM + &C5 i sposób przełączania
  banków: opracowania pamięci PC-1500 oparte na TRM Sharp, instrukcjach serwisowych
  i pomiarach (`PEEK &7863` = &40 na PC-1500A, &00 z modułem 16 KB).
- CE-159: instrukcja serwisowa Sharp („10K bytes including the reserve area”).
- CE-157, CE-160, CE-162E: opisy modułów na
  [pc-1500.info](http://www.pc-1500.info/category/cat_family/cat_3modules/) i w
  [Wikipedii](https://en.wikipedia.org/wiki/Sharp_PC-1500). Adresy CE-151 i CE-157 są
  wywnioskowane z budowy CE-155, a nie zmierzone.
- Rozmiar instalatora: obliczony z tokenizacji linii v6.1 (przybliżenie ±5%).

W razie wątpliwości zawsze rozstrzyga `PRINT PEEK &7863` na Twoim komputerze.
