#RF TEST
import struct, time
from machine import Pin, I2C, SPI, ADC
from pcf8574 import PCF8574
from hd44780 import HD44780
from lcd import LCD
import _thread

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
pcf = PCF8574(i2c)
hd44780 = HD44780(pcf, num_lines=2, num_columns=16)
lcd = LCD(hd44780, pcf)
lcd.backlight_on()
# -- ENCODER, ANALOG STICKS, SWITCH MULTIPLEX SETUP -----
b_pin = Pin(15, Pin.IN, Pin.PULL_UP)   #EC11
s_pin = Pin(2, Pin.IN, Pin.PULL_UP)   #EC11
d_pin = Pin(12, Pin.IN, Pin.PULL_UP)    #EC11

MPS00 = Pin(9, Pin.OUT, value = 0)    #AMALOG
MPS01 = Pin(20, Pin.OUT, value = 0)    #ANALOG
MPS02 = Pin(3, Pin.OUT, value = 0)    #ANALOG
MPS10 = Pin(6, Pin.OUT, value = 0)    #SWITCH
MPS11 = Pin(7, Pin.OUT, value = 0)    #SWITCH
MPS12 = Pin(28, Pin.OUT, value = 0)    #SWITCH

API = ADC(Pin(26))                    #ANALOG SIGNAL
SWI = Pin(10, Pin.IN, Pin.PULL_UP)    #SWITCH SIGNAL

RF = Pin(4, Pin.OUT, value=0)         #LED
MODE = Pin(11, Pin.OUT, value=0)      #LED
WNCH = Pin(13, Pin.OUT, value=0)      #LED
JIB = Pin(22, Pin.OUT, value=0)       #LED
LQIH = Pin(21, Pin.OUT, value=0)      #LED
LQIL = Pin(27, Pin.OUT, value=0)      #LED
DUMMY = Pin(8, Pin.OUT, value=0)     #DUMMY




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
LED_REFRESH = 500
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
JOY = zero*8 #CHANNEL VALUES
AX  = zero*6 #AXIS ON, OFF
DRM = zero*6 #AXIS DIRECTION
DZ  = zero*6 #Deadzone
MID = zero*6 #Joystick calibration
MIS = zero*6 #Min speed
MAS = zero*6 #Max speed
STR = zero*6 #Stroke
SPD = zero*6 #SPEED OUTPUT
channels = 8 #CHANNEL NUMBER AMOUNT
SW_LIST = zero*8  # LIST FOR STORING BUTTON AND SWITCH INFO
MAP_AXIS = {
#     0:0,1:1,2:2,3:3,4:4,5:5,6:6,7:7
        0:0, #SLEW
        1:1, #BOOM
        2:3, #WNCH
        3:2, #JIB
        5:4, #COMP
        4:6,
        6:6,
        7:6,
                }
LED_ADDRESS = {
                0:DUMMY.value, #DUMMY.value
                1:DUMMY.value,   #JIB.value
                2:WNCH.value, #DUMMY.value
                3:MODE.value, #DUMMY.value
                4:JIB.value,    #RF.value
                5:DUMMY.value,  #MODE.value
                6:RF.value,  #WNCH.value
                7:DUMMY.value, #DUMMY.value
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
    time.sleep_us(50)
    MPS00.value(int(n[0]))
    time.sleep_us(50)
    MPS01.value(int(n[1]))
    time.sleep_us(50)
    MPS02.value(int(n[2]))
    
    #Debug BINARY SELECTOR
    #print(MPS00.value(),MPS01.value(),MPS02.value())
    time.sleep_us(100)
    JOY[MAP_AXIS.get(f)] = round(API.read_u16()*100 / 65535)
    
    return JOY

def chsweep(n,JOY,MAP_AXIS):
    for i in range(n):
            chcheck(i,JOY,MAP_AXIS)
            time.sleep_us(100)
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
        time.sleep_us(10)
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
#gdo0 = Pin(14, Pin.IN)

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




def encoder_task(MENU_ACTIVE, CURRENT_INDEX, previous_value, button_down, TIME_RECENT, RECENT_INPUT):
    global _enc_left, _enc_right
    LEFT = False
    RIGHT = False

    with _enc_lock:
        left_count  = _enc_left
        right_count = _enc_right
        _enc_left   = 0
        _enc_right  = 0
        delta      = _enc_delta
        if delta != 0:
            pass
            #print("delta:", delta)

    if left_count > 0:
        LEFT = True
        TIME_RECENT  = time.ticks_ms()
        RECENT_INPUT = True
    if right_count > 0:
        RIGHT = True
        TIME_RECENT  = time.ticks_ms()
        RECENT_INPUT = True

    # Button unchanged
    if b_pin.value() == False and not button_down:
        time.sleep_ms(10)
        if b_pin.value() == False:
            if MENU_ACTIVE == False:
                MENU_ACTIVE = True
            CURRENT_INDEX += 1
            TIME_RECENT   = time.ticks_ms()
            RECENT_INPUT  = True
            button_down   = True
    if b_pin.value() == True and button_down:
        button_down = False

    return MENU_ACTIVE, CURRENT_INDEX, TIME_RECENT, RECENT_INPUT, previous_value, LEFT, RIGHT, button_down
        
    
def updatemenu_task(M,SPD_S,RIGHT,LEFT,CURRENT_INDEX, SPEED_INDEX, MENU_ACTIVE):
    if CURRENT_INDEX >= SPEED_INDEX:
        CURRENT_INDEX = 1
    if MENU_ACTIVE == True:    
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
        #print(SPD_S[CURRENT_INDEX])
    return M, SPD_S, CURRENT_INDEX



def joystick_task(JOY,MAP_AXIS,channels,MID,DZ,AX,DRM,MIS,MAS,STR,SPD):
    chsweep(channels,JOY,MAP_AXIS)
    #JOY[MAP_AXIS.get(3)] = 50
    for i in range(5):
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

    #ENCODING AND WRITE FOR JOYSTICK AXIS
    for i in range(5):
        if SPD[i] // 100 == 32:
            SPD[i] = 3100
        M[i] = int(128 + AX[i]*64 + DRM[i]*32 + SPD[i]//100)
    #print(M)
    return JOY, MAP_AXIS, MID, DZ, AX, DRM, MIS, MAS, STR, SPD

def switch_task(SW_LIST,SW_BYTE):
    chsweeps(8,SW_LIST)
                #ID[1]        #ID[2]        #ID[3]      #ID[4]       #ID[5]        #ID[6]
    SW_BYTE = SW_LIST[4]*32+SW_LIST[0]*16+SW_LIST[5]*8+SW_LIST[6]*4+SW_LIST[3]*2+SW_LIST[2]*1
    #print(SW_LIST)
    return SW_BYTE, SW_LIST
        #ID[1] = JIB
        #ID[2] = BUTTON x
        #ID[3] = AUX  x
        #ID[4] = RF   x
        #ID[5] = MODE x
        #ID[6] = WNCH x 

        #SW_LIST[0] BUTTON
        #SW_LIST[2] WNCH
        #SW_LIST[3] MODE
        #SW_LIST[4] JIB
        #SW_LIST[5] AUX
        #SW_LIST[7] RF
        #NOTE BUTTON NOT WORKING

def show_menu(MENU_ACTIVE,lcd,SPD_S,MIS,MAS,CURRENT_INDEX,INDEX_TEXT):
    if MENU_ACTIVE == True:
        lcd.backlight_on()
        lcd.write_lines(f"{INDEX_TEXT.get(CURRENT_INDEX-1)} SPD:{SPD_S[CURRENT_INDEX-1]}\n{INDEX_TEXT.get(CURRENT_INDEX)} SPD:{SPD_S[CURRENT_INDEX]}")
        #lcd.cursor_on()
        lcd.hd44780.set_cursor(1,12)
        lcd.blink_on()
        pass
    elif MENU_ACTIVE == False:
        lcd.blink_off()
        for i in range(len(SPD_S)):
            if i == 0:
                pass
            elif i%2 == 1:
                MIS[(i//2)] = SPD_S[i]*100
            elif i%2 == 0:
                MAS[(i//2)-1] = SPD_S[i]*100
    return SPD_S,MIS,MAS

seq = 0
def LQIblink(seq):
    seq += 1
    if seq == 1:
        LQIH.value(0)
        LQIL.value(0)
    elif seq == 2:
        LQIH.value(1)
        LQIL.value(0)
    elif seq == 3:
        LQIH.value(0)
        LQIL.value(1)
    elif seq == 4:
        LQIH.value(0)
        LQIL.value(1)
        seq = 0
    return seq



e_rec = 0 
e_ref = 100
ms_rec = 10
ms_ref = 20
joy_rec = 0
joy_ref = 100
sw_rec = 75
sw_ref = 200
ld_rec = 0
ld_ref = 200


betwixed = 0

DECODE = zero*len(M)

shared = {
    "rssi"        : None,
    "lqi"         : None,
    "decode"      : [0]*5,
    "sw_byte"     : 0,
    "betwixed"    : 0,
    "menu_active" : False,
    "current_idx" : 0,
    "spd_s"       : SPD_S[:],
    "mis"         : MIS[:],
    "mas"         : MAS[:],
    # written back TO core 0:
    "mis_out"     : MIS[:],
    "mas_out"     : MAS[:],
}
screen_lock = _thread.allocate_lock()

positions = [359,59,131,109,0]

# -- Interrupt Encoder ----
# Shared encoder state
_enc_left  = 0
_enc_right = 0
_enc_lock  = _thread.allocate_lock()
_last_isr   = 0
_last_dir   = 0
_enc_delta = 0


def encoder_isr(pin):
    global _enc_delta, _last_isr
    now     = time.ticks_us()
    elapsed = time.ticks_diff(now, _last_isr)

    if elapsed < 2000:
        return

    # Read d_pin twice and confirm they agree
    d1 = d_pin.value()
    d2 = d_pin.value()
    if d1 != d2:
        return  # unstable — likely noise

    _last_isr = now

    if d1 == 0:
        _enc_delta -= 1
    else:
        _enc_delta += 1
        
s_pin.irq(trigger=Pin.IRQ_FALLING, handler=encoder_isr)

# ── Core 1 screen loop ────────────────────────────────────────────────────────
def screen_loop():
    import time
    while True:
        try:
            with screen_lock:
                rssi    = shared["rssi"]
                lqi     = shared["lqi"]
                dec     = shared["decode"][:]
                sw      = shared["sw_byte"]
                bw      = shared["betwixed"]
                menu    = shared["menu_active"]
                cidx    = shared["current_idx"]
                spd_s   = shared["spd_s"][:]
                mis     = shared["mis"][:]
                mas     = shared["mas"][:]

            if menu:
                # Speed selection menu
                lcd.backlight_on()
                line1 = "{} SPD:{}".format(INDEX_TEXT.get(cidx - 1), spd_s[cidx - 1])
                line2 = "{} SPD:{}".format(INDEX_TEXT.get(cidx),     spd_s[cidx])
                lcd.write_lines(line1 + '\n' + line2)
                lcd.hd44780.set_cursor(1, 12)
                lcd.blink_on()

            else:
                # Update MIS/MAS from SPD_S (was the non-menu branch of show_menu)
                lcd.blink_off()
                for i in range(len(spd_s)):
                    if i == 0:
                        pass
                    elif i % 2 == 1:
                        mis[i // 2] = spd_s[i] * 100
                    elif i % 2 == 0:
                        mas[(i // 2) - 1] = spd_s[i] * 100

                # Write back updated MIS/MAS so core 0 can use them
                with screen_lock:
                    shared["mis_out"] = mis[:]
                    shared["mas_out"] = mas[:]

                # Normal telemetry screen
                #if positions[4] == 1:
                #    HON = 'ON'
                #elif positions[4] == 0:
                #    HON = 'OFF'
                HON = 'OFF'
                if rssi is not None:
                    line1 = "{:.0f}dBm F{} H: {:03s}".format(int(abs(rssi)),bw,HON)
                else:
                    line1 = "NLINK F{} H: {:03s}".format(bw,HON)
                line2 = "{:03d} {:02d} {:03d} {:03d}".format(
                    positions[2],positions[0],positions[1],positions[3])
                lcd.write_lines(line1 + '\n' + line2)

        except Exception as e:
            print("Screen core error:", e)

        time.sleep_ms(350)        

_thread.start_new_thread(screen_loop, ())



#wdt = WDT(timeout=3000)
#CORE 0 - MAIN LOOP

partnum = read_status(0xF0)
version = read_status(0xF1)
print(hex(partnum))
print(hex(version))



while True:
    #wdt.feed()
    then = time.ticks_ms()
    
    #Encoder Task
    now = time.ticks_ms()
    if now - e_rec >= e_ref:
        e_rec = time.ticks_ms()
        MENU_ACTIVE, CURRENT_INDEX, TIME_RECENT, RECENT_INPUT, previous_value, LEFT, RIGHT, button_down = encoder_task(MENU_ACTIVE, CURRENT_INDEX, previous_value, button_down, TIME_RECENT, RECENT_INPUT)
        M , SPD_S, CURRENT_INDEX = updatemenu_task(M,SPD_S,RIGHT,LEFT,CURRENT_INDEX, SPEED_INDEX, MENU_ACTIVE)
        #print(CURRENT_INDEX,SPEED_INDEX)
        #print(LEFT,RIGHT)
        #(CURRENT_INDEX,SPD_S)
    
    #Menu Timeout Task
    now = time.ticks_ms()
    if now - TIME_RECENT >= MENU_TIMEOUT and RECENT_INPUT == True:
        CURRENT_INDEX = 0
        RECENT_INPUT = False
        MENU_ACTIVE = False
    
    #Menu Screen 
    now = time.ticks_ms()
    if now - ms_rec >= ms_ref:
        ms_rec = time.ticks_ms()
        
    #Joystick Task
    now = time.ticks_ms()
    if now - joy_rec >= joy_ref:
        joy_rec = time.ticks_ms()
        JOY, MAP_AXIS, MID, DZ, AX, DRM, MIS, MAS, STR, SPD = joystick_task(JOY,MAP_AXIS,channels,MID,DZ,AX,DRM,MIS,MAS,STR,SPD)
        DECODE = zero*len(M)
#         print(JOY)
        for i in range(len(M)):
            DECODE[i] = (M[i]-128)%32
    #Switch Task
    now = time.ticks_ms()
    if now - sw_rec >= sw_ref:
        SW_BYTE, SW_LIST = switch_task(SW_LIST,SW_BYTE)
        #print(SW_LIST)
        #print(DECODE) 
        sw_rec = time.ticks_ms()
        
    #Screen Menu Task
    #now = time.ticks_ms()
    #if now- sm_rec >= sm_ref:
    #    sm_rec = time.ticks_ms()
    #    SPD_S, MIS, MAS = show_menu(MENU_ACTIVE,lcd,SPD_S,MIS,MAS,CURRENT_INDEX,INDEX_TEXT)
        
    #SPI RF
    send_packet(struct.pack("BBBBBB", M[0],M[1],M[2],M[3],M[4],SW_BYTE))
    #print(struct.pack("BBBBBB", M[0],M[1],M[2],M[3],M[4],SW_BYTE))
    #print(M,SW_BYTE)
    flush_and_rx()
    rxb = wait_packet(timeout_ms=40)
    if rxb >= 4:
        length = read_fifo(1)[0]
        rxb2   = read_status(0xFB) & 0x7F
        if 0 < length <= 61 and rxb2 >= length + 2:
            payload = read_fifo(length)
            status  = read_fifo(2)
            if status[1] & 0x80:
                link_rssi = rssi_dbm(payload[0])
                link_lqi  = payload[1] & 0x7F
                if len(payload) >= 22:
                    raw = struct.unpack('@20s',payload[2:22])[0]
                    raw = raw.decode('utf-8').strip('\0x00')
                    if raw.startswith('<') and raw.endswith('>'):
                        positions = raw[1:-1].split(' ')
                        for i in range(len(positions)):
                            positions[i] = int(round(float(positions[i]),0))
        #print(type(positions))
        #print(type(positions[1]))
    else:
        link_rssi = None
        link_lqi = None
    
    with screen_lock:
        shared["rssi"]        = link_rssi
        shared["lqi"]         = link_lqi
        shared["decode"]      = DECODE[:]
        shared["sw_byte"]     = SW_BYTE
        shared["betwixed"]    = betwixed
        shared["menu_active"] = MENU_ACTIVE
        shared["current_idx"] = CURRENT_INDEX
        shared["spd_s"]       = SPD_S[:]
        shared["mis"]         = MIS[:]
        shared["mas"]         = MAS[:]
        shared["positions"]   = positions
        # Read back MIS/MAS updates from screen core
        MIS = shared["mis_out"][:]
        MAS = shared["mas_out"][:]
    
    #partnum = read_status(0xF0)
    #version = read_status(0xF1)
    
    
    #Update LEDs    
    now = time.ticks_ms()   
    if now-ld_rec >= ld_ref: 
        ld_rec = time.ticks_ms()
        for i in range(len(SW_LIST)):
            LED_ADDRESS.get(i)(SW_LIST[i])
        if link_lqi is not None:
            if link_lqi >= 80:
                LQIH.value(1)
                LQIL.value(1)
            elif 40 >= link_lqi >= 80:
                LQIH.value(0)
                LQIL.value(1)
            elif link_lqi <= 40:
                LQIH.value(0)
                LQIL.value(0)
        else:
            #LQIL.toggle()
            seq = LQIblink(seq)
            pass
    #print(DECODE)
    #TEST WITH 10ms instead
    now = time.ticks_ms()
    betwixed = now - then
    #print(betwixed)
    #if betwixed <= 30:
    #    time.sleep_ms(betwixed)

