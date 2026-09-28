; =====================================================================
; SERIN v55 - programowy odbiornik UART 9600 bps 8N1 dla Sharp PC-1500(A)
; CPU LH5801 @ 1,3 MHz, wejscie PB2 (CMT-IN, pin 27 zlacza 60-pin),
; polaryzacja TTL-232 (spoczynek = 1, bit startu = 0).
;
; Wywolanie z BASIC-a:
;   CALL SI          odbierz do 256 znakow
;   CALL SI,M        odbierz najwyzej M znakow (1..256; 0 lub >256 = 256)
; Wynik:
;   RC, RC+1         liczba odebranych znakow, 16 bitow (starszy bajt pierwszy)
;   RX..RX+255       odebrane znaki (RX = poczatek strony pamieci, &4200)
;   M                (tylko przy CALL SI,M) = liczba odebranych znakow
;                    (powrot z C=1 -> ROM wpisuje X do zmiennej z CALL)
; Czas:
;   pierwszy znak musi przyjsc w ciagu ~30 s, kolejne w odstepach < ~0,5 s,
;   po M-tym (lub 127.) znaku powrot natychmiast.
;
; Adres ladowania: SI = RAM+&130 (&4130).
; Symbole wstawiane przez BASIC: RP = strona bufora RX (RX = RP*256),
; CP = RP-1 (licznik RC = CP*256+&FE), NP = 256-RP.
; Skoki: LH5801 ma osobne kody dla skokow w przod (+) i w tyl (-),
; przesuniecie jest ZAWSZE dodatnie (0..255), liczone od nastepnego rozkazu.
; Wersja 9600 (jak v53): petla bitu = 134,5 / 137,5 cyklu (tablica MAME /
; instrukcja LH5801; idealnie 135,4) i krotszy czas do polowy bitu startu.
; Pierwsza probka ok. 1,4 bitu po zboczu startu.
; Plik jest zrodlem dla tools/build_v55.py (asembler + generator POKE).
; =====================================================================
        RIE                 ; bez przerwan (timing!)
        LDA  XH             ; bez zmiennej (adres w ROM), M=256 lub M>256
        BZR+ MAXM           ;   -> 256 znakow
        LDA  XL             ; CALL SI,M: X = M (1..255)
        DEC  A              ; r = M-1 (M = 0 -> &FF, czyli 256 znakow)
        BCH+ SETM
MAXM:   LDI  A,&FF          ; r = 255 -> 256 znakow (caly bufor)
SETM:   STA  (CP,&FE)       ; RC = r (pozostalo r+1 znakow)
        LDI  XH,RP          ; X = RX (poczatek strony)
        LDI  XL,0
        LDI  YH,&F0         ; Y = &F00D (DDB, rejestr kierunku portu B)
        LDI  YL,&0D
        ANI  #(Y),&FB       ; PB2 = wejscie
        INC  Y
        INC  Y              ; Y = &F00F (port B, bit 2 = CMT-IN)
        LDI  UH,&00         ; timeout 1. znaku: 18*256*256 obiegow ~ 30 s
        LDI  A,18
WH:     BII  #(Y),&04       ; czekaj na stan spoczynkowy (1 = mark)
        BZR+ WL             ; linia = 1 -> czekaj na bit startu
        LOP  UL,WH          ; 256 obiegow x 33 cykle
        DEC  UH
        BZR- WH
        DEC  A
        BZR- WH
        BCH+ DONE           ; timeout
WL:     BII  #(Y),&04       ; czekaj na zbocze 1->0 (bit startu)
        BZS+ START
        LOP  UL,WL
        DEC  UH
        BZR- WL
        DEC  A
        BZR- WL
        BCH+ DONE           ; timeout
START:  LDI  UL,3           ; ~pol bitu startu
HALF:   LOP  UL,HALF
        BII  #(Y),&04       ; srodek bitu startu: nadal 0?
        BZR- WL             ; nie -> zaklocenie, czekaj dalej
        LDI  UH,8           ; 8 bitow danych
BIT:    LDI  UL,5           ; petla bitu: 1 bit = 135,4 cyklu
DLY:    LOP  UL,DLY
        NOP                 ; (dostrojenie: +10 cykli)
        NOP
        BII  #(Y),&04
        SEC
        BZR+ ONE
        REC
ONE:    ROR                 ; LSB pierwszy
        DEC  UH
        BZR- BIT
        SIN  X              ; zapisz znak, X++
        LDA  (CP,&FE)       ; r = 0 -> to byl ostatni dozwolony znak
        BZS+ DONE
        DEC  A
        STA  (CP,&FE)
        LDI  UH,77          ; timeout miedzy znakami: 77*256 obiegow ~ 0,5 s
        LDI  A,1
        BCH- WH             ; czekaj na bit stopu i kolejny znak
DONE:   LDA  XH             ; liczba znakow = X - RX (0..256)
        REC
        ADI  A,NP           ; starszy bajt: XH - RP (0 lub 1)
        STA  (CP,&FE)       ; RC   = starszy bajt
        STA  XH             ; X = liczba znakow ...
        LDA  XL
        STA  (CP,&FF)       ; RC+1 = mlodszy bajt
        SEC                 ; ... C=1: BASIC wpisze X do zmiennej z CALL SI,M
        RTN
