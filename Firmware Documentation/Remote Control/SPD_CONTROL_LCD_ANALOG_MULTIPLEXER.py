#TEST_FULL INSTRUMENTATION - RF
#ENCODER AND LED TEST
import time
from machine import Pin, I2C, SPI, ADC
from pcf8574 import PCF8574
from hd44780 import HD44780
from lcd import LCD

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
pcf = PCF8574(i2c)
hd44780 = HD44780(pcf, num_lines=2, num_columns=16)
lcd = LCD(hd44780, pcf)

b_pin = Pin(15, Pin.IN, Pin.PULL_UP)   #EC11
s_pin = Pin(12, Pin.IN, Pin.PULL_UP)   #EC11
d_pin = Pin(2, Pin.IN, Pin.PULL_UP)    #EC11

MPS00 = Pin(9, Pin.OUT, value = 0)    #AMALOG
MPS01 = Pin(8, Pin.OUT, value = 0)    #ANALOG
MPS02 = Pin(3, Pin.OUT, value = 0)    #ANALOG
MPS10 = Pin(5, Pin.OUT, value = 0)    #SWITCH
MPS11 = Pin(6, Pin.OUT, value = 0)    #SWITCH
MPS12 = Pin(7, Pin.OUT, value = 0)    #SWITCH

API = ADC(Pin(26))                    #ANALOG SIGNAL
SWI = Pin(10, Pin.IN, Pin.PULL_UP)    #SWITCH SIGNAL

#BOOLS AND INDEXES FOR ENCODER
MENU_ACTIVE = False
RECENT_INPUT = False
TIME_RECENT = 0
MENU_TIMEOUT = 5000
SPEED_INDEX = 10+1
CURRENT_INDEX = 0
zero = [0]
SPD_S = zero*SPEED_INDEX
SCREEN_REFRESH = 400
SCREEN_RECENT = 0
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
MAP_AXIS = {
            0:0,
            1:1,
            2:5,
            3:4,
            4:2,
            5:3
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
    

#ROTARY ENCODER LOOP
while True:
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
            lcd.backlight_off()
            lcd.write_lines(f"")
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
    
    time.sleep(0.01)
