; =====================================================================
; SERIN v56 - programowy odbiornik UART 9600 bps 8N1 dla Sharp PC-1500(A)
; CPU LH5801 @ 1,3 MHz, wejscie PB0 (&F00F bit 0, pin 9 zlacza 60-pin),
; polaryzacja TTL-232 (spoczynek = 1, bit startu = 0).
;
; Wywolanie z BASIC-a:
;   CALL SI          odbierz do 255 znakow
;   CALL SI,M        odbierz najwyzej M znakow (1..255; 0 lub >255 = 255)
; Wynik:
;   RC               liczba odebranych znakow, 1 bajt (0..255), RC = RX-1
;   RX..RX+254       odebrane znaki (RX = poczatek strony pamieci, &4200)
;   M                (tylko przy CALL SI,M) = liczba odebranych znakow
;                    (powrot z C=1 -> ROM wpisuje X do zmiennej z CALL)
; Czas:
;   pierwszy znak musi przyjsc w ciagu ~30 s, kolejne w odstepach < ~0,5 s,
;   po M-tym (lub 255.) znaku powrot natychmiast.
;
; Adres ladowania: SI = RAM+&130 (&4130).
; Symbole wstawiane przez BASIC: RP = strona bufora RX (RX = RP*256),
; CP = RP-1 (licznik RC = CP*256+&FF = RX-1).
; Bufor RX zaczyna sie od poczatku strony, wiec liczba znakow = XL.
; Skoki: LH5801 ma osobne kody dla skokow w przod (+) i w tyl (-),
; przesuniecie jest ZAWSZE dodatnie (0..255), liczone od nastepnego rozkazu.
; Wersja 9600 (jak v53): petla bitu = 134,5 / 137,5 cyklu (tablica MAME /
; instrukcja LH5801; idealnie 135,4) i krotszy czas do polowy bitu startu.
; Pierwsza probka ok. 1,4 bitu po zboczu startu.
; v56 = v55 z wejsciem PB0 zamiast PB2 (CMT-IN): zmienione sa tylko maski
; bitu (ANI &FE, BII &01), wiec czasy i dlugosc kodu sa takie same jak w v55.
; PB0 to wolne wejscie CMOS bez podciagania: dac 10 kOhm do VCC.
; Plik jest zrodlem dla tools/build_v56.py (asembler + generator POKE).
; =====================================================================
        RIE                 ; bez przerwan (timing!)
        LDA  XH             ; bez zmiennej (adres w ROM) albo M>255
        BZR+ MAXM           ;   -> 255 znakow
        LDA  XL             ; CALL SI,M: X = M
        BZS+ MAXM           ; M = 0 -> 255 znakow
        DEC  A              ; r = M-1 (0..254)
        BCH+ SETM
MAXM:   LDI  A,&FE          ; r = 254 -> 255 znakow (caly bufor)
SETM:   STA  (CP,&FF)       ; RC = r (pozostalo r+1 znakow)
        LDI  XH,RP          ; X = RX (poczatek strony)
        LDI  XL,0
        LDI  YH,&F0         ; Y = &F00D (DDB, rejestr kierunku portu B)
        LDI  YL,&0D
        ANI  #(Y),&FE       ; PB0 = wejscie
        INC  Y
        INC  Y              ; Y = &F00F (port B, bit 0 = PB0)
        LDI  UH,&00         ; timeout 1. znaku: 18*256*256 obiegow ~ 30 s
        LDI  A,18
WH:     BII  #(Y),&01       ; czekaj na stan spoczynkowy (1 = mark)
        BZR+ WL             ; linia = 1 -> czekaj na bit startu
        LOP  UL,WH          ; 256 obiegow x 33 cykle
        DEC  UH
        BZR- WH
        DEC  A
        BZR- WH
        BCH+ DONE           ; timeout
WL:     BII  #(Y),&01       ; czekaj na zbocze 1->0 (bit startu)
        BZS+ START
        LOP  UL,WL
        DEC  UH
        BZR- WL
        DEC  A
        BZR- WL
        BCH+ DONE           ; timeout
START:  LDI  UL,3           ; ~pol bitu startu
HALF:   LOP  UL,HALF
        BII  #(Y),&01       ; srodek bitu startu: nadal 0?
        BZR- WL             ; nie -> zaklocenie, czekaj dalej
        LDI  UH,8           ; 8 bitow danych
BIT:    LDI  UL,5           ; petla bitu: 1 bit = 135,4 cyklu
DLY:    LOP  UL,DLY
        NOP                 ; (dostrojenie: +10 cykli)
        NOP
        BII  #(Y),&01
        SEC
        BZR+ ONE
        REC
ONE:    ROR                 ; LSB pierwszy
        DEC  UH
        BZR- BIT
        SIN  X              ; zapisz znak, X++
        LDA  (CP,&FF)       ; r = 0 -> to byl ostatni dozwolony znak
        BZS+ DONE
        DEC  A
        STA  (CP,&FF)
        LDI  UH,77          ; timeout miedzy znakami: 77*256 obiegow ~ 0,5 s
        LDI  A,1
        BCH- WH             ; czekaj na bit stopu i kolejny znak
DONE:   LDA  XL             ; liczba znakow = XL (RX zaczyna sie od strony)
        STA  (CP,&FF)       ; RC = liczba odebranych znakow
        LDI  XH,0           ; X = liczba znakow ...
        SEC                 ; ... C=1: BASIC wpisze X do zmiennej z CALL SI,M
        RTN
