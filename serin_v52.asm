; =====================================================================
; SERIN v52 - programowy odbiornik UART 4800 bps 8N1 dla Sharp PC-1500(A)
; CPU LH5801 @ 1,3 MHz, wejscie PB2 (CMT-IN, pin 27 zlacza 60-pin),
; polaryzacja TTL-232 (spoczynek = 1, bit startu = 0).
;
; Wywolanie z BASIC-a:
;   CALL SI          odbierz do 127 znakow
;   CALL SI,M        odbierz najwyzej M znakow (1..127; 0 lub >127 = 127)
; Wynik:
;   RX+0             liczba odebranych znakow (0 = nic nie przyszlo)
;   RX+1..RX+127     odebrane znaki
;   M                (tylko przy CALL SI,M) = liczba odebranych znakow
;                    (powrot z C=1 -> ROM wpisuje X do zmiennej z CALL)
; Czas:
;   pierwszy znak musi przyjsc w ciagu ~30 s, kolejne w odstepach < ~0,5 s,
;   po M-tym (lub 127.) znaku powrot natychmiast.
;
; Adres ladowania: SI = RAM+&22A (&422A), 121 bajtow (&422A..&42A2).
; Symbole wstawiane przez BASIC: RH/RL = adres RX, R1 = RL+1, CN = 255-RL.
; Skoki: LH5801 ma osobne kody dla skokow w przod (+) i w tyl (-),
; przesuniecie jest ZAWSZE dodatnie (0..255), liczone od nastepnego rozkazu.
; Petla bitu jest bajt w bajt taka jak w sprawdzonym SERIN v47.
; Plik jest zrodlem dla tools/build_serin.py (asembler + generator POKE).
; =====================================================================
        RIE                 ; bez przerwan (timing!)
        LDA  XH             ; CALL SI bez zmiennej: X = adres w ROM (XH<>0)
        BZR+ MAXM           ;   -> m = 127
        LDA  XL             ; CALL SI,M: X = M
        BZS+ MAXM           ; M = 0 -> m = 127
        BII  A,&80          ; M >= 128 ?
        BZS+ SETM           ; 1..127 -> zostaw
MAXM:   LDI  A,&7F          ; m = 127 (caly bufor)
SETM:   STA  (RX)           ; RX[0] = licznik pozostalych znakow (m)
        LDI  XH,RH          ; X = RX+1 (pierwszy bajt danych)
        LDI  XL,R1
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
START:  LDI  UL,7           ; ~pol bitu (ten sam czas do 1. probki co v47)
HALF:   LOP  UL,HALF
        BII  #(Y),&04       ; srodek bitu startu: nadal 0?
        BZR- WL             ; nie -> zaklocenie, czekaj dalej
        LDI  UH,8           ; 8 bitow danych
BIT:    LDI  UL,&13         ; petla bitu IDENTYCZNA jak w v47
DLY:    LOP  UL,DLY
        BII  #(Y),&04
        SEC
        BZR+ ONE
        REC
ONE:    ROR                 ; LSB pierwszy
        DEC  UH
        BZR- BIT
        SIN  X              ; zapisz znak, X++
        LDA  (RX)           ; pozostalo--
        DEC  A
        BZS+ DONE           ; odebrano m znakow -> koniec
        STA  (RX)
        LDI  UH,77          ; timeout miedzy znakami: 77*256 obiegow ~ 0,5 s
        LDI  A,1
        BCH- WH             ; czekaj na bit stopu i kolejny znak
DONE:   LDA  XL             ; liczba znakow = XL - (RL+1)
        REC
        ADI  A,CN           ; CN = 255-RL
        STA  (RX)           ; RX[0] = liczba odebranych znakow
        STA  XL             ; X = liczba znakow ...
        LDI  XH,0
        SEC                 ; ... C=1: BASIC wpisze X do zmiennej z CALL SI,M
        RTN
