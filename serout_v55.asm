; =====================================================================
; SEROUT v55 - programowy nadajnik UART 9600 bps 8N1 dla Sharp PC-1500(A)
; CPU LH5801 @ 1,3 MHz, wyjscie PC7 (&F008 bit 7), polaryzacja TTL
; (spoczynek = 1, bit startu = 0).
;
; Wywolanie z BASIC-a:
;   CALL SO          wyslij 1 znak z TX+0
;   CALL SO,N        wyslij N znakow z TX+0.. (1..256; 0 = 1 znak, >256 = 256)
; Zmienna N NIE jest zmieniana (powrot z C=0).
; Bufor TX: 256 bajtow od poczatku strony pamieci (TX = RAM+&300 = &4300).
;
; 1 bit = 1/9600 s = 135,4 cyklu. Czasy (cykle, tablica MAME / instrukcja):
;   bit danych 134 / 137, bit startu 134-135 / 137-138, bit stopu ~1,2 bitu.
; Obie galezie (bit 0 i bit 1) maja te sama dlugosc, a zapis do portu
; nastepuje w nich w tym samym momencie (+-1 cykl).
; Licznik bitow: znacznik (sentinel) - SEC+ROR wklada 1 do bitu 7, po
; osmym SHR akumulator = 0. Z sprawdzamy przez BII A,&FF, bo wedlug
; instrukcji LH5801 rozkazy SHR/ROR nie ustawiaja flagi Z.
; Licznik znakow w UH (0 = 256), bez zmiennych w pamieci.
;
; Adres ladowania: SO = RAM+&0C5 (&40C5).
; Symbol wstawiany przez BASIC: TP = starszy bajt adresu bufora TX.
; =====================================================================
        RIE                 ; bez przerwan (timing!)
        LDA  XH
        BZS+ SMALL          ; N = 0..255
        BII  A,&80          ; CALL SO bez zmiennej: X = adres w ROM (XH>=&80)
        BZR+ N1             ;   -> 1 znak
        LDI  A,0            ; N = 256..32767 -> 256 (UH = 0)
        BCH+ NOK
SMALL:  LDA  XL
        BZR+ NOK            ; N = 1..255
N1:     LDI  A,1            ; N = 0 -> 1 znak
NOK:    STA  UH             ; UH = liczba znakow (0 = 256)
        LDI  XH,TP          ; X = bufor TX (poczatek strony)
        LDI  XL,0
        LDI  YH,&F0         ; Y = &F008 (port C)
        LDI  YL,&08
        ORI  #(Y),&80       ; PC7 = 1 (spoczynek) ...
        LDI  UL,12          ; ... przez ~1 bit przed pierwszym startem
IDLE:   LOP  UL,IDLE
CHAR:   LIN  X              ; A = znak, X++
        ANI  #(Y),&7F       ; bit startu (PC7 = 0)
        SEC
        ROR                 ; C = bit 0, znacznik 1 -> bit 7 A
        LDI  UL,7           ; dlugosc bitu startu
SDLY:   LOP  UL,SDLY
        NOP
OUT:    BCS+ ONE            ; wyslij bit z C
        REC                 ; (wyrownanie: zapis w tym samym cyklu)
        ANI  #(Y),&7F       ; PC7 = 0
        BCH+ BDLY
ONE:    ORI  #(Y),&80       ; PC7 = 1
        NOP                 ; (wyrownanie dlugosci galezi)
        SEC
BDLY:   LDI  UL,5           ; dlugosc bitu danych
DLY:    LOP  UL,DLY
        REC                 ; (dostrojenie: +4 cykle)
        SHR                 ; C = nastepny bit
        BII  A,&FF          ; A = 0 -> wyslano 8 bitow
        BZR- OUT
        NOP                 ; (wyrownanie ostatniego bitu danych)
        NOP
        REC
        ORI  #(Y),&80       ; bit stopu (PC7 = 1)
        LDI  UL,10          ; dlugosc bitu stopu (~1,2 bitu)
TDLY:   LOP  UL,TDLY
        DEC  UH
        BZR- CHAR           ; nastepny znak
        REC                 ; C=0: zmienna N bez zmian
        RTN
