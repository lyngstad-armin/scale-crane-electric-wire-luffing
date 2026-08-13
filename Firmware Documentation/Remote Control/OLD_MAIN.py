#RF TEST
import struct, time
from machine import Pin, I2C, SPI, ADC
from pcf8574 import PCF8574
from hd44780 import HD44780
from lcd import LCD

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
pcf = PCF8574(i2c)
hd44780 = HD44780(pcf, num_lines=2, num_columns=16)
lcd = LCD(hd44780, pcf)
lcd.backlight_on()
# -- ENCODER, ANALOG STICKS, SWITCH MULTIPLEX SETUP -----
b_pin = Pin(15, Pin.IN, Pin.PULL_UP)   #EC11
s_pin = Pin(12, Pin.IN, Pin.PULL_UP)   #EC11
d_pin = Pin(2, Pin.IN, Pin.PULL_UP)    #EC11

MPS00 = Pin(9, Pin.OUT, value = 0)    #AMALOG
MPS01 = Pin(8, Pin.OUT, value = 0)    #ANALOG
MPS02 = Pin(3, Pin.OUT, value = 0)    #ANALOG
MPS10 = Pin(6, Pin.OUT, value = 0)    #SWITCH
MPS11 = Pin(7, Pin.OUT, value = 0)    #SWITCH
MPS12 = Pin(5, Pin.OUT, value = 0)    #SWITCH

API = ADC(Pin(26))                    #ANALOG SIGNAL
SWI = Pin(10, Pin.IN, Pin.PULL_UP)    #SWITCH SIGNAL

RF = Pin(4, Pin.OUT, value=0)         #LED
MODE = Pin(11, Pin.OUT, value=0)      #LED
WNCH = Pin(13, Pin.OUT, value=0)      #LED
JIB = Pin(22, Pin.OUT, value=0)       #LED
LQIH = Pin(21, Pin.OUT, value=0)      #LED
LQIL = Pin(14, Pin.OUT, value=0)      #LED
DUMMY = Pin(27, Pin.OUT, value=0)     #DUMMY




#BOOLS AND INDEXES FOR ENCODER
MENU_ACTIVE = False
RECENT_INPUT = False
TIME_RECENT = 0
MENU_TIMEOUT = 5000
SPEED_INDEX = 10+1
CURRENT_INDEX = 0
zero = [0]
SPD_S = zero*SPEED_INDEX
SCREEN_REFRESH = 350
SCREEN_RECENT = 0
LED_RECENT = 0
LED_REFRESH = 250
INDEX_TEXT = {
                 0:"COMP MAX",
                 1:"SLEW MIN",
                 2:"SLEW MAX",
                 3:"BOOM MIN",
                 4:"BOOM MAX",
                 5:"JIB  MIN",
                 6:"JIB  MAX",
                 7:"WNCH MIN",
                 8:"WNCH MAX",
                 9:"COMP MIN",
                10:"COMP MAX",
                }

previous_value = True  #EC11
button_down = False    #EC11
LEFT = False           #EC11
RIGHT = False          #EC11

#ARGS FOR ANALOG MULTIPLEXER
JOY = zero*6 #CHANNEL VALUES
AX  = zero*6 #AXIS ON, OFF
DRM = zero*6 #AXIS DIRECTION
DZ  = zero*6 #Deadzone
MID = zero*6 #Joystick calibration
MIS = zero*6 #Min speed
MAS = zero*6 #Max speed
STR = zero*6 #Stroke
SPD = zero*6 #SPEED OUTPUT
channels = 5 #CHANNEL NUMBER AMOUNT
JOY_REFRESH = 100 #ms REFRESH RATE FOR JOYSTICKS
JOY_RECENT = 0 #UPDATE JOY ON FIRST TICK
SW_REFRESH = 200
SW_RECENT = 0
SW_LIST = zero*7 # LIST FOR STORING BUTTON AND SWITCH INFO
MAP_AXIS = {
            0:0,
            1:1,
            2:5,
            3:4,
            4:2,
            5:3
                }
LED_ADDRESS = {
                0:DUMMY.value,
                1:JIB.value,
                2:DUMMY.value,
                3:DUMMY.value,
                4:RF.value,
                5:MODE.value,
                6:WNCH.value,
                7:DUMMY.value,
                    }

#------------------------------------------
#                  RC OUTPUT BYTES
M0 : int = 0          #AXIS 0 Byte
M1 : int = 0          #AXIS 1 Byte
M2 : int = 0          #AXIS 2 Byte
M3 : int = 0          #AXIS 3 Byte
M4 : int = 0          #AXIS 4 Byte
M : list = zero*5    #LIST MOTOR BYTES
SW_BYTE : int  = 0    #SWITCH BYTE


#define functions for sweeping analog multiplexer

def chcheck(f,JOY,MAP_AXIS):
    n = bin(f)
    n = n.replace('0b','')
    while len(n) < 3:
        n = '0' + n
    MPS00.value(int(n[0]))
    MPS01.value(int(n[1]))
    MPS02.value(int(n[2]))
    
    #Debug BINARY SELECTOR
    #print(S0.value(),S1.value(),S2.value())
    
    JOY[MAP_AXIS.get(f)] = round(API.read_u16()*100 / 65535)
    
    return JOY

def chsweep(n,JOY,MAP_AXIS):
    for i in range(n):
            chcheck(i,JOY,MAP_AXIS)
    return JOY

def chchecks(f):
    n = bin(f)
    n = n.replace('0b','')
    while len(n) < 3:
        n = '0' + n
    MPS10.value(int(n[0]))
    MPS11.value(int(n[1]))
    MPS12.value(int(n[2]))
    return SWI.value()
def chsweeps(n,SW_BYTE):
    for i in range(n):
        SW_LIST[i] = chchecks(i)
    return SW_LIST
    
#SET DEFAULTS FOR ANALOG MULTIPLEXER LISTS
for i in range(len(DZ)):
    DZ[i] = 20
    MID[i] = 50
    MIS[i] = 200
    MAS[i] = 1200
    STR[i] = STR[i] = 100 - MID[i] - DZ[i]

#ASSIGN MIS MAS TO SPD_S
for i in range(len(SPD_S)):
    if i == 0:
        pass
    elif i%2 == 1:
        SPD_S[i] = int(MIS[(i//2)+1]/100)
    elif i%2 == 0:
        SPD_S[i] = int(MAS[(i//2)]/100)
    
# ── SPI setup ────────────────────────────────────────────────────────────────
spi  = SPI(0, baudrate=2_000_000, polarity=0, phase=0,
           firstbit=SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs   = Pin(17, Pin.OUT, value=1)
gdo0 = Pin(14, Pin.IN)

# ── Radio helpers ─────────────────────────────────────────────────────────────
def strobe(cmd):
    cs(0); spi.write(bytes([cmd])); cs(1)

def read_status(addr):
    cs(0); spi.write(bytes([addr | 0xC0]))
    buf = bytearray(1); spi.readinto(buf); cs(1)
    return buf[0]

def write_reg(addr, val):
    cs(0); spi.write(bytes([addr, val])); cs(1)

def read_fifo(n):
    cs(0); spi.write(bytes([0xFF]))
    buf = bytearray(n); spi.readinto(buf); cs(1)
    return buf

def rssi_dbm(raw):
    return (raw - 256) / 2 - 74 if raw >= 128 else raw / 2 - 74

def flush_and_rx():
    strobe(0x36); strobe(0x3A); time.sleep_us(100); strobe(0x34)

def send_packet(data):
    strobe(0x36); strobe(0x3B); time.sleep_us(100)
    cs(0); spi.write(bytes([0x7F])); spi.write(bytes([len(data)])); spi.write(data); cs(1)
    strobe(0x35)
    deadline = time.ticks_add(time.ticks_ms(), 100)
    while read_status(0xF5) not in (0x01, 0x0D):
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            break
        time.sleep_us(50)

def wait_packet(timeout_ms):
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    prev = 0; stable = 0
    while True:
        rxb = read_status(0xFB) & 0x7F
        if rxb > 0 and rxb == prev:
            stable += 1
            if stable >= 3:
                return rxb
        else:
            stable = 0
        prev = rxb
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return 0
        time.sleep_us(100)

# ── CC1101 init ───────────────────────────────────────────────────────────────
cs(0); time.sleep_us(5); cs(1); time.sleep_us(40)
cs(0); time.sleep_us(5); cs(1); time.sleep_ms(100)
strobe(0x30); time.sleep_ms(100)

config = [
    (0x02,0x06),(0x03,0x47),(0x04,0xD3),(0x05,0x91),
    (0x06,0x3D),(0x07,0x04),(0x08,0x45),(0x0A,0x00),
    (0x0B,0x06),(0x0C,0x00),(0x0D,0x10),(0x0E,0xA7),
    (0x0F,0x62),(0x10,0xCA),(0x11,0x83),(0x12,0x93),
    (0x13,0x22),(0x14,0xF8),(0x15,0x34),(0x17,0x3F),
    (0x18,0x18),(0x19,0x16),(0x1A,0x6C),(0x1B,0x43),
    (0x1C,0x40),(0x1D,0x91),(0x21,0x56),(0x22,0x10),
    (0x23,0xE9),(0x24,0x2A),(0x25,0x00),(0x26,0x1F),
    (0x2C,0x81),(0x2D,0x35),(0x2E,0x09),
]
for addr, val in config:
    write_reg(addr, val)
cs(0); spi.write(bytes([0x3E | 0x40, 0xC0])); cs(1)

# ── Main loop ─────────────────────────────────────────────────────────────────
link_rssi = None
link_lqi  = None
next_tx   = time.ticks_ms()
skjermtid = time.ticks_ms()
partnum_dt = 1000
partnum_recent = 0




while True:
    #ENCODER READ LOOP
    if previous_value != s_pin.value():
        if s_pin.value() == False:
            if d_pin.value() == False:
                LEFT = True
                TIME_RECENT = time.ticks_ms()
                RECENT_INPUT = True
                
                pass
            else:
                RIGHT = True
                TIME_RECENT = time.ticks_ms()
                RECENT_INPUT = True
                
                pass
        previous_value = s_pin.value()
    if b_pin.value() == False and not button_down:
    #OPEN MENU ON BUTTON PRESS
        if MENU_ACTIVE == False:
            MENU_ACTIVE = True
        CURRENT_INDEX += 1
        TIME_RECENT = time.ticks_ms()
        RECENT_INPUT = True
    #RESET BUTTON    
        button_down = True
    if b_pin.value() == True and button_down:
        button_down = False

    #MENU_TIMEOUT
    if time.ticks_diff(time.ticks_ms(),TIME_RECENT) >= MENU_TIMEOUT and RECENT_INPUT == True:
        RECENT_INPUT = False
        MENU_ACTIVE = False
        CURRENT_INDEX = 0
    
    #UPDATE IF IN MENU
    if MENU_ACTIVE == True:
        if CURRENT_INDEX >= SPEED_INDEX:
            CURRENT_INDEX = 1
        if LEFT == True:
            SPD_S[CURRENT_INDEX] += 1
        elif RIGHT == True:
            SPD_S[CURRENT_INDEX] -= 1
        if SPD_S[CURRENT_INDEX] > 32:
            SPD_S[CURRENT_INDEX] = 32
        elif SPD_S[CURRENT_INDEX] <= 0:
            SPD_S[CURRENT_INDEX] = 1
        SPD_S[0] = SPD_S[10]
        M = [128]*5
        
    #SHOW MENU
    if time.ticks_diff(time.ticks_ms(),SCREEN_RECENT) >= SCREEN_REFRESH:
        if MENU_ACTIVE == True:
            lcd.backlight_on()
            lcd.write_lines(f"{INDEX_TEXT.get(CURRENT_INDEX-1)} SPD:{SPD_S[CURRENT_INDEX-1]}\n{INDEX_TEXT.get(CURRENT_INDEX)} SPD:{SPD_S[CURRENT_INDEX]}")
            #lcd.cursor_on()
            lcd.hd44780.set_cursor(1,12)
            lcd.blink_on()
            pass
        elif MENU_ACTIVE == False:
            #lcd.backlight_off()
            #lcd.write_lines(f"")
            pass
            
            #WHEN EXITING MENU UPDATE SPEED TABLE FOR ANALOG AXIS
            for i in range(len(SPD_S)):
                if i == 0:
                    gigglefart = False
                elif i%2 == 1:
                    MIS[(i//2)] = SPD_S[i]*100
                elif i%2 == 0:
                    MAS[(i//2)-1] = SPD_S[i]*100
            pass
        SCREEN_RECENT = time.ticks_ms()   
    
    #RESET
    LEFT = False
    RIGHT = False  
    
    
    #MULTIPLEXER LOOP
    if MENU_ACTIVE == False and time.ticks_diff(time.ticks_ms(),JOY_RECENT) >= JOY_REFRESH:
        chsweep(channels+1,JOY,MAP_AXIS)
        JOY[MAP_AXIS.get(2)] = 50
        #Debug channel values
        #print(JOY)
        for i in range(channels):
            #1 DIR
            if JOY[i] >= MID[i] + DZ[i]:
                if AX[i] == 0:
                    AX[i] = 1
                    #print('Motor',i,'run: 1')
                    DRM[i] = 1
                    
                elif AX[i] == 1:
                    pos = JOY[i] - MID[i] - DZ[i]
                    SPD[i] = int(MIS[i] + pos*(MAS[i]-MIS[i])/STR[i] // 1)
                    #print('Motor',i,'Speed:',SPD[i])
                    
            #-1 DIR
            elif JOY[i] <= MID[i] - DZ[i]:
                if AX[i] == 0:
                    AX[i] = 1
                    #print('Motor',i,'run: -1')
                    DRM[i] = 0
                        
                elif AX[i] == 1:
                    pos = JOY[i]
                    SPD[i] = int(MAS[i] - pos*(MAS[i]-MIS[i])/STR[i]) // 1
                    #print('Motor',i,'Speed:',SPD[i])
                    
            elif MID[i] - DZ[i] < JOY[i] < MID[i] + DZ[i] and AX[i] == 1:
                AX[i] = 0
                DRM[i] = 0
                SPD[i] = 0
                #print('Motor',i,'stop')
                
        JOY_RECENT = time.ticks_ms()
        #ENCODING AND WRITE FOR JOYSTICK AXIS
        for i in range(5):
            if SPD[i] // 100 == 32:
                SPD[i] = 3100
            M[i] = int(128 + AX[i]*64 + DRM[i]*32 + SPD[i]//100)
    
    
    #SW MULTIPLEXER
    if time.ticks_diff(time.ticks_ms(),SW_RECENT) >= SW_REFRESH: 
        chsweeps(7,SW_LIST)
        SW_RECENT = time.ticks_ms()
        #print(SW_LIST)
        SW_BYTE = SW_LIST[1]*32+SW_LIST[2]*16+SW_LIST[3]*8+SW_LIST[4]*4+SW_LIST[5]*2+SW_LIST[6]*1
        #print(SW_BYTE)
        
        #ID[1] = JIB
        #ID[2] = BUTTON
        #ID[3] = AUX
        #ID[4] = RF
        #ID[5] = MODE
        #ID[6] = WNCH
    skjerm_dt = time.ticks_diff(time.ticks_ms(), skjermtid)

    

    # 3. Listen for RSSI telemetry reply (30ms window)
    send_packet(struct.pack("BBBBBB", M[0],M[1],M[2],M[3],M[4],SW_BYTE))
    flush_and_rx()
    rxb = wait_packet(timeout_ms=300)
    if rxb >= 4:
        length = read_fifo(1)[0]
        rxb2 = read_status(0xFB) & 0x7F
        if length == 2 and rxb2 >= 4:
            payload = read_fifo(2)
            status  = read_fifo(2)
            if status[1] & 0x80:
                link_rssi = rssi_dbm(payload[0])
                link_lqi  = payload[1]

    partnum = read_status(0xF0)
    version = read_status(0xF1)
    
    
    #TODO DEBUG
    #print(time.ticks_diff(partnum_recent,time.ticks_ms()))
    #if time.ticks_diff(partnum_recent,time.ticks_ms()) >= partnum_dt:
    #    partnum_recent = time.ticks_ms()
    #    print('partnum')
    #    if partnum != 0 or version != 20:
    #        lcd.write_lines(f"INCORRECT SIGNAL")

    if link_rssi is not None:
        if skjerm_dt > 350 and MENU_ACTIVE == False:
            
            #DECODE SPEEDS FOR TESTING
            DECODE = zero*len(M)
            for i in range(len(M)):
                DECODE[i] = (M[i]-128)%32
            
            #print('skriver til skjerm')
            lcd.write_lines(f"{link_rssi:.1f}dbm lqi:{link_lqi}\n{DECODE[0]} {DECODE[1]} {DECODE[2]} {DECODE[3]} {DECODE[4]} {SW_BYTE} {wait}")
            skjermtid = time.ticks_ms()
    else:
        #print(f"x1={x1} y1={y1}  no link")
        if skjerm_dt > 350 and MENU_ACTIVE == False:
            
            #DECODE SPEEDS FOR TESTING
            DECODE = zero*len(M)
            for i in range(len(M)):
                DECODE[i] = (M[i]-128)%32
                
            #print('skriver til skjerm')
            lcd.write_lines(f"no link\n{DECODE[0]} {DECODE[1]} {DECODE[2]} {DECODE[3]} {DECODE[4]} {SW_BYTE} {wait}")
            skjermtid = time.ticks_ms()



    #LED TIME
    if time.ticks_diff(time.ticks_ms(),LED_RECENT) >= LED_REFRESH: 
        LED_RECENT = time.ticks_ms()
        for i in range(len(SW_LIST)):
            LED_ADDRESS.get(i)(SW_LIST[i])


    
    #print(M)
    
    
    # 5. Pace to 20Hz (50ms per cycle)
    
    
    #TEST WITH 10ms instead
    next_tx = time.ticks_add(next_tx, 50)#20ms
    wait = time.ticks_diff(next_tx, time.ticks_ms())
    if wait > 0:
        time.sleep_ms(wait)

