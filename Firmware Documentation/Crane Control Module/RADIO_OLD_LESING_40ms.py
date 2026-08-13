#MOTOR RC DECODING AND MOTOR COMMANDS
from velo import stacy, encoder, link
from machine import UART, Pin, SPI
import struct, time, gc, bisect, umatrix, math

#=========================================CALL CLASSES, DECLARE OBJECTS ======================================

#DECLARE MOTORS (STEP,DIR)
# jib2 = stacy(8,7)
# jib1 = stacy(3,2)
# comp1 = stacy(12,15)
# comp2 = stacy(28,20)
# winch = stacy(11,10)
# boom = stacy(5,21)
# slew1 = stacy(6,13,RECK=1) 
# slew2 = stacy(22,14)
jib2 = stacy(0,1)
jib1 = stacy(3,2)
comp1 = stacy(8,20)
comp2 = stacy(11,10)
winch = stacy(13,12)
boom = stacy(15,14)
slew1 = stacy(6,7,rid=0) #rid = 1 
slew2 = stacy(22,21)


#DECLARE ENCODERS
time.sleep(0.5)
Ejib2 = encoder(26,27,ch=5,sid=1,freq=40)
Eboom = encoder(26,27,ch=6,sid=2,freq=40)
Ejib1 = encoder(26,27,ch=7,sid=3,freq=40)
Ecomp = encoder(26,27,ch=3,sid=5,freq=20)    #COMP (1160 steps ish)
Ewinch = encoder(26,27,ch=4,sid=4,freq=5)

#Declare JIB2 LINK
Ljib2 = link(jib2,Ejib2)

def clear_rx_buffer(uart):
    uart.read(uart.any())
#==================================================POSITION/ANGLE READING===============================================
 
#READ BOOM ANGLE LISTS FROM CSV TO MEMORY
boom_pos : list = []
ang_deg  : list = []
with open('boom_angle.csv','r') as file:
    for line in file:
            row = line.rstrip('\n').rstrip('\r').split(',')
            boom_pos.append(int(row[0]))
            ang_deg.append(int(row[1]))
del file; del line; del row;
gc.collect()
#READ RELATIVE BOOM SPEEDS
jib1_speeds : list = []
jib2_speeds : list = []
ang_deg_boom : list = []
with open('boom_speed.csv','r') as file:
    for line in file:
        row = line.rstrip('\n').rstrip('\r').split(',')
        ang_deg_boom.append(int(row[0]))
        jib1_speeds.append(float(row[1]))
        jib2_speeds.append(float(row[2]))
del file; del line; del row;
gc.collect()

#BOOM SPEED CALCULATION
def boom_speed(act_angle,ang_deg_boom,jib1,jib2):
    if act_angle >= 70:
        return 0.97,0.79
    else:
        idex = bisect.bisect(ang_deg_boom,act_angle)
        #print(idex)
        return jib1[idex],jib2[idex]


#BOOM ANGLE CALCULATION
def boom_angle(l,bp,ad):
    #BOOM CONSTANT OFFSET 330
    if l >= 4875:
        return 70
    idex = bisect.bisect(bp,l)
    return ad[idex]

def slew_reck():
    steppos = slew1.getreck()
    angpos = steppos*360 / (15150)  % 360
    angpos = 90
    return round(angpos,1)

#COMP POSITION CALC
def comp_pos(getpos):
    pos = round((getpos) * 110/1160,1)
    if pos >= 110:
        pos = 110.0
    elif pos <= 0:
        pos = 0.0
    return pos
    #front to back
    #0mm == fully forward
    #110mm == fully back

#JIB ANGLE
row = []
jib_set = []
with open('jib_angle.csv','r') as f:
    data = f.read()
for line in data.split('\r'):
    line = line.strip().strip('[]')
    if not line:
        continue
    row = [int(x) for x in line.split(',')]
    jib_set.append(row)
del f; del row; del line; del data;
#print(jib_set)

def jib_angle(boom_angle,jib1e,file):
    jib1pos = []
    jib2pos = []
    offset = 2859
    jibcheck = -jib1e #+ offset
    #print(file)
    for i in range(len(file)):
        #print(boom_angle,i)
        if i == boom_angle:
            sline = file[i]
    del i;
    gc.collect()

    try:
        l = enumerate(sline)
        for j, info in l:
            if j % 2 == 1:
                jib1pos.append(int(sline[j]))
            #elif j % 2 == 0:
            #    jib2pos.append(int(sline[j]))
        
        del l; del j; del info;
        gc.collect()
        idex = bisect.bisect(jib1pos,jibcheck)
        del jib1pos; del jib2pos;
        gc.collect()
    except Exception as e:
        print(f"{e}")
        idex = 0
    return 132 - idex*2

#COMP ACTIVATE
def compensate(heave_save):
    hspeed  = -heave_save * 1160/110 * 5
    if -1 < save_comp < 111 and abs(hspeed) >= 10:
        if hspeed > 0:
            COMP_ON(1)
            COMP_SPD(hspeed,1)
            pass
        elif hspeed < 0:
            COMP_ON(0)
            COMP_SPD(-hspeed,0)
            pass
    else:
        COMP_OFF()
        hspeed = 0
    return hspeed


#==================================================== HEAVE CALCULATION ==============================
def heave_calc(POS, th1,th2,th3,th4,rolld,hd):
    #POS      TUPLE POSITION VECTORS
    #TH1            ROLL ANGLE (RAD)
    #TH2            SLEW ANGLE (RAD)
    #TH3            BOOM ANGLE (RAD)
    #TH4            JIB  ANGLE (RAD)
    #ROLLD    ANGULAR VELOCITY (RAD/S)
    #HD       LINEAR  VELOCITY (mm/S)
    
    #OUTPUT XCDOT3  LINEAR VELOCITY 3-AXIS REP (mm/S)
    
    #Position Vectors (constant)
    P_PS, P_SB, P_BJ, P_JR = POS
    
    #Relative Rotation Matrices
    R1 = umatrix.matrix([1,0,0],[0,math.cos(th1),-math.sin(th1)],[0,math.sin(th1),math.cos(th1)])  #ROLL
    R21 = umatrix.matrix([math.cos(th2),-math.sin(th2),0],[math.sin(th2),math.cos(th2),0],[0,0,1]) #SLEW
    R32 = umatrix.matrix([1,0,0],[0,math.cos(th3),-math.sin(th3)],[0,math.sin(th3),math.cos(th3)]) #BOOM
    R43 = umatrix.matrix([1,0,0],[0,math.cos(th4),-math.sin(th4)],[0,math.sin(th4),math.cos(th4)]) #JIB
    #Additional Relative Rotations
    R31 = R21 * R32
    R41 = R31 * R43
    #Absolute Rotation Matrices
    R2 = R1 * R21
    R3 = R2 * R32
    R4 = R3 * R43
    #Angluar Velocities
    W1 = umatrix.matrix([0,0,rolld]).transpose
    #Linear Velocity (Heave)
    ht = umatrix.matrix([0,0,hd]).transpose
    #Lie Group
    e3 = umatrix.matrix([0,0,1])
    XCDOT3 =e3*( ht + R1 * P_PS * W1 + R2 * P_SB * R21.transpose * W1 + R3 * P_BJ * R31.transpose * W1 + R4 * P_JR * R41.transpose * W1)
    del ht; del e3; del W1; del R2; del R3; del R4; del R41; del R31; del R43; del R32; del R21; del R1; del P_PS; del P_SB; del P_BJ; del P_JR;
    return float(XCDOT3[0][0])


#================================================================= RADIO SETUP =====================================================



#SPI
spi = SPI(0, baudrate=400_000, polarity=0, phase=0,
          firstbit=SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs  = Pin(17, Pin.OUT, value=1)
#UART
uart1 = UART(1, baudrate=115200,rxbuf = 4096, tx=4, rx=5)
clear_rx_buffer(uart1)

_BUF1  = bytearray(1)
_BUF2  = bytearray(2)
_BUF4  = bytearray(4)
_BUF16 = bytearray(16)
_WBUF2 = bytearray(2)
_WBUF1 = bytearray(1)
#CC1101 HELPERS
def strobe(cmd):
    _WBUF1[0] = cmd
    cs(0); spi.write(_WBUF1); cs(1)

def read_status(addr):
    _WBUF1[0] = addr | 0xC0
    cs(0); spi.write(_WBUF1); spi.readinto(_BUF1); cs(1)
    return _BUF1[0]

def write_reg(addr, val):
    _WBUF2[0] = addr; _WBUF2[1] = val
    cs(0); spi.write(_WBUF2); cs(1)

def read_fifo(n):
    _WBUF1[0] = 0xFF
    buf = memoryview(_BUF16)[:n]   # no allocation, view into existing buffer
    cs(0); spi.write(_WBUF1); spi.readinto(buf); cs(1)
    return buf

def rssi_dbm(raw):
    return (raw - 256) / 2 - 74 if raw >= 128 else raw / 2 - 74

def flush_and_rx():
    strobe(0x36); strobe(0x3A); time.sleep_us(100); strobe(0x34)

def send_packet(data):
    strobe(0x36); strobe(0x3B); time.sleep_us(100)
    cs(0); spi.write(bytes([0x7F])); spi.write(bytes([len(data)])); spi.write(data); cs(1)
    strobe(0x35)
    deadline = time.ticks_add(time.ticks_ms(), 50)
    while read_status(0xF5) not in (0x01, 0x0D):
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            break
        time.sleep_us(50)

def wait_packet_old(timeout_ms):
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    prev = 0; stable = 0
    while True:
        rxb = read_status(0xFB) & 0x7F
        if rxb > 0 and rxb == prev:
            stable += 1
            if stable >= 2:
                return rxb
        else:
            stable = 0
        prev = rxb
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return 0
        time.sleep_us(100)
        
gdo0 = Pin(28, Pin.IN)

def wait_packet(timeout_ms):
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    
    t1 = time.ticks_ms()
    while gdo0.value() == 0:
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            #print("timeout waiting for HIGH")
            return 0
        time.sleep_us(50)
    
    t2 = time.ticks_ms()
    while gdo0.value() == 1:
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            #print("timeout waiting for LOW")
            return 0
        time.sleep_us(50)

    t3 = time.ticks_ms()
    #print(f"high_wait={time.ticks_diff(t2,t1)}ms low_wait={time.ticks_diff(t3,t2)}ms")
    return read_status(0xFB) & 0x7F


partnum = read_status(0xF0)
version = read_status(0xF1)
print(hex(partnum))
print(hex(version))

#================================================ DECLARE DECODE, AND PAIR MOTOR FUNCTIONS ===========================================

#DECLARE PAYLOAD LISTS FOR DECODING
zero     : list = [0]
zerobool : list = [False]
DEC_AX   : list = zero*5
DEC_SPD  : list = zero*5
DEC_DIR  : list = zero*5
DEC_SW   : list = zero*7
DATA     : list = zero*6

#DECLARE POSITION VECTORS FOR HEAVE
P_PS = umatrix.matrix( [     0,	 103.6,	  -0.0],
                           [-103.6,	     0,	   0.0],
                           [   0.0,	  -0.0,	     0] )
    
P_SB = umatrix.matrix( [     0,	 76.67,	-22.58],
                           [-76.67,	     0,	   0.0],
                           [ 22.58,	  -0.0,	     0] )
    
P_BJ = umatrix.matrix( [     0,	   0.0,	-500.0],
                           [  -0.0,	     0,	   0.0],
                           [ 500.0,	  -0.0,	     0] )
    
P_JR = umatrix.matrix( [      0,	-207.35,	-238.55],
                           [ 207.35,	      0,	    0.0],
                           [ 238.55,	   -0.0,	      0] )
POS = P_PS, P_SB, P_BJ, P_JR
del P_PS; del P_SB; del P_BJ; del P_JR

#FUNCTIONS ON
def SLEW_ON(dr):
    slew1.run(dr)
    slew2.run(dr)
def COMP_ON(dr):
    Ecomp.freq = 80
    if dr == 0:
        dr = -1
    comp1.run(-dr)
    comp2.run(dr)
def BOOM_ON(dr):
    jib1.run(dr)
    jib2.run(dr)
    boom.run(dr)
def JIB_ON(dr):
    if dr == 0:
        dr = -1
    jib1.run(dr)
    jib2.run(-dr)
def WINCH_ON(dr):
    winch.run(dr)

def SINGLE_JIB_ON(dr):
    jib2.run(dr)

#FUNCTIONS OFF
def SLEW_OFF():
    slew1.stop()
    slew2.stop()
def COMP_OFF():
    comp1.stop()
    comp2.stop()
    Ecomp.freq = 20
def BOOM_OFF():
    jib1.stop()
    jib2.stop()
    boom.stop()
    #DISABLE IF NOT WORKING
    #RESLACK(Ejib1.getpos(),save_boom_pos,jib_set,correction_map)
def JIB_OFF():
    jib1.stop()
    jib2.stop()
    #DISABLE IF NOT WORKING
    #RESLACK(Ejib1.getpos(),save_boom_pos,jib_set,correction_map)
def WINCH_OFF():
    winch.stop()
    
def CRANE_OFF():
    jib1.stop()
    jib2.stop()
    boom.stop()
    winch.stop()
    comp1.stop()
    comp2.stop()
    slew1.stop()
    slew2.stop()
    
#FUNCTIONS SPEED
def SLEW_SPD(spd,dr):
    slew1.speed(spd)
    slew2.speed(spd)
    
def COMP_SPD(spd,dr):
    spd = int(round(spd))
    comp1.speed(spd)
    comp2.speed(spd)
    #print(spd)
    
def BOOM_SPD(spd,dr):
    #DYNAMIC SPEED PER POSITION
    try:
        jib1s, jib2s = boom_speed(boom_angle(4675+Eboom.getpos(),boom_pos,ang_deg),ang_deg_boom,jib1_speeds,jib2_speeds)
    except Exception as e:
        print("Could not fetch Boom speed")
    finally:
        jib1s = 1.14
        jib2s = 0.8
    jib1s = int((jib1s+0.05)*spd)
    jib2s = int((jib2s+0)*spd)
    if jib1s <= 40:
        jib1s = 50
    if jib2s <= 40:
        jib2s = 50
    jib1.speed(jib1s)
    jib2.speed(jib2s)
    boom.speed(spd)
    
    del jib2s; del jib1s;
    
def JIB_SPD(spd,dr):
    jib1.speed(spd)
    #2.5 ish should be dynamic though
    jib2.speed(int(spd*2.5))
    
def WINCH_SPD(spd,dr):
    winch.speed(spd)

def SINGLE_JIB_SPD(spd,dr):
    jib2.speed(spd)

def RESLACK(jib1e,bangle,jib_set,correction):
    jib1pos = []
    jib2pos = []
    jibcheck = -jib1e #+ offset
    #Get jib angle list, at boom angle
    

    try:
        sline = jib_set[bangle]
        l = enumerate(sline)
        for j, info in l:
            #Odd entries in jib1
            if j % 2 == 1:
                jib1pos.append(int(sline[j]))
            #Even entries in jib2
            elif j % 2 == 0:
                jib2pos.append(int(sline[j]))
        #Intersect the list with input encoder value
        idex = bisect.bisect(jib1pos,jibcheck)
        jangle = 132 - idex*2
        #Go to jib2 of that intersection, minus offset
        if idex == 0:
            pos_goto = jib2pos[idex+1] -6771
        else:
            pos_goto = jib2pos[idex] -6771
        
        pos_nocorr = pos_goto
        val = correction.get((bangle,jangle//2),None)
        #If there is a correction entry, add it
        if val != None:
            pos_goto += int(val//1)
        
        #Ljib2.goto((-pos_goto),jib2.SPSA)
        Ljib2.goto((-pos_goto),600)
    except Exception as e:
        print(e)
    finally:
        try:
            print(pos_nocorr,'Actual target\n',pos_goto,'With correction')
        except Exception as e:
            print(e)
            
def ADD_CORRECTION(correction_map, bangle, jangle, jingle):
    correction_map[(bangle, jangle // 2)] = jingle
    return correction_map
def ADD_CORRECTION_RANGE(correction_map, bangle, jangle1, jangle2, jingle):
    diff = jangle2//2 - jangle1//2
    for i in range(diff):
        correction_map[(bangle, jangle1// 2 +i)] = jingle
def CORRECTION():
    correction_map = {}
    #ADD_CORRECTION(correction_map,bangle,jangle,jingle)
    #ADD_CORRECTION_RANGE(correction_map,bangle,jangle1,jangle2,jingle)
    
    #return list to call
    return correction_map

prev_IMU = [0,0,0,0]
def lesing():
    if uart1.any():
        global prev_IMU
        temp = uart1.read()
        temp1 = struct.unpack('@35s', temp)
        
        temp2 = temp1[0].decode("utf-8")
        if temp2.find("<") != -1 and temp2.find(">") != -1:
            temp = temp2.replace(">", " ")
            temp1 = temp.replace("<", "")
            temp1 = temp1.split(' ')
            curr_IMU = temp1
            
            dt = int(curr_IMU[3]) - int(prev_IMU[3])
            rolld = (float(curr_IMU[0]) - float(prev_IMU[0])) * dt/1000
            heave = float(curr_IMU[1])
            heaved = float(curr_IMU[2])            
            
            prev_IMU = curr_IMU[0:4]
            
            IMU = curr_IMU[0:4]
            print(IMU)
        else:
            IMU = [None,None,None,None]
    else:
        IMU = [None,None,None,None]
    return IMU

#Generate correction map for reslack function
correction_map = CORRECTION() 


#DICTS FOR HANDLING MOTOR COMMANDS
ACTUAL_ON    : list = zerobool*5
AXIS_MAP_ON  : dict = {     1:SLEW_ON,
                            0:BOOM_ON,
                            2:JIB_ON,
                            4:COMP_ON,
                            3:WINCH_ON,
                            9:SINGLE_JIB_ON
                                        }
AXIS_MAP_OFF : dict = {     1:SLEW_OFF,
                            0:BOOM_OFF,
                            2:JIB_OFF,
                            4:COMP_OFF,
                            3:WINCH_OFF,
                                       }
AXIS_MAP_SPD : dict = {     1:SLEW_SPD,
                            0:BOOM_SPD,
                            2:JIB_SPD,
                            4:COMP_SPD,
                            3:WINCH_SPD,
                            9:SINGLE_JIB_SPD,
                                        }

#========================================================= INITIALIZE RADIO TRANSCIEVER =============================


# CC1101 INITIALIZE
cs(0); time.sleep_us(5); cs(1); time.sleep_us(40)
cs(0); time.sleep_us(5); cs(1); time.sleep_ms(100)
strobe(0x30); time.sleep_ms(100)

config = [
    (0x00,0x01),
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



#============================================================ COMPUTING LOOP ===============================================

print("Kran er klar")
flush_and_rx()

ENCODER_RECENT         : int = 0
ENCODER_REFRESH        : int = 1600 #ms between refreshes on encoder active code
PAYLOAD_PACKET_RECENT  : int = 10
PAYLOAD_PACKET_REFRESH : int = 200 #ms between refreshes on decoded data and motor signals
POS_RECENT             : int = 50
POS_REFRESH            : int = 400 #ms
HEAVE_RECENT           : int = 100
HEAVE_REFRESH          : int = 200 #ms
del zero; del zerobool;



clear_rx_buffer(uart1)
timing = 0
while True:
    gc.collect()
    #ENCODER ALWAYS ON PROTOCOL
    if time.ticks_diff(time.ticks_ms(),ENCODER_RECENT) >= ENCODER_REFRESH:                
        ENCODER_RECENT = time.ticks_ms()    
        #print('Mem Free: [kB] ',gc.mem_free()//1024)
        Ejib1.enable(2)
        Ejib2.enable(2)
        Eboom.enable(2)
        Ewinch.enable(2)
        Ecomp.enable(2)
        
    # 1. Wait for joystick packet
    rxb = wait_packet(timeout_ms=300)
    IMU = lesing()
    clear_rx_buffer(uart1)

    if rxb == 0:
        print("(Ingen signal)")
        CRANE_OFF()                #TURN OFF MOTORS ON SIGNAL LOSS
        flush_and_rx()
        continue

    if read_status(0xF5) == 0x11:  # RX overflow
        flush_and_rx()
        continue

    if rxb < 4:
        flush_and_rx()
        continue

    length = read_fifo(1)[0]
    rxb2   = read_status(0xFB) & 0x7F

    if not (0 < length <= 61 and rxb2 >= length + 2):
        flush_and_rx()
        continue

    payload = read_fifo(length)
    status  = read_fifo(2)
    #print(payload)

    if not (status[1] & 0x80):  # CRC fail
        flush_and_rx()
        continue
    if partnum != 0 or version != 20:
        break
    #print(hex(version))

    if rxb != 0:
        
        #Payload task
        if time.ticks_diff(time.ticks_ms(),PAYLOAD_PACKET_RECENT) >= PAYLOAD_PACKET_REFRESH:
            PAYLOAD_PACKET_RECENT = time.ticks_ms()
            DATA = struct.unpack('BBBBBB', payload)
            
            #Decode payload
            for i in range(len(DATA)-1):
                DEC_AX[i] = (DATA[i]-128)//64
                DEC_SPD[i] = (DATA[i]-128)%32 * 100
                DEC_DIR[i] = ((DATA[i]-128)%64)//32
            DEC_SW[1] = DATA[5] // 32      #ID[1] = JIB
            DEC_SW[2] = DATA[5]%32 // 16   #ID[2] = BUTTON
            DEC_SW[3] = DATA[5]%16 // 8    #ID[3] = AUX
            DEC_SW[4] = DATA[5]%8 // 4     #ID[4] = RF
            DEC_SW[5] = DATA[5]%4 // 2     #ID[5] = MODE
            DEC_SW[6] = DATA[5]%2          #ID[6] = WNCH
            for i in range(5):
                g = i
                #SINGLE JIB TEST
                if i == 2 and DEC_SW[1] == 1:
                    g = 9
                    
                #START MOTOR
                if DEC_AX[i] == 1 and ACTUAL_ON[i] == False:
                    AXIS_MAP_ON.get(g)(DEC_DIR[i])
                    #AXIS_MAP_SPD.get(i)(DEC_SPD[i])
                    ACTUAL_ON[i] = True
                
                #STOP MOTOR  
                elif DEC_AX[i] == 0 and ACTUAL_ON[i] == True:
                    AXIS_MAP_OFF.get(i)()
                    ACTUAL_ON[i] = False
                
                #UPDATE SPEED
                elif DEC_AX[i] == 1 and ACTUAL_ON[i] == True:
                    if DEC_SPD[i] >= 100:
                        AXIS_MAP_SPD.get(g)(DEC_SPD[i],DEC_DIR[i])
                    
                        
                    
        #Position Task
        if time.ticks_diff(time.ticks_ms(),POS_RECENT) >= POS_REFRESH:                
                POS_RECENT = time.ticks_ms()
                
                #Calculate crane positions
                save_boom_pos = boom_angle(-Eboom.getpos(),boom_pos,ang_deg)
                save_jib_pos  = 0#jib_angle(save_boom_pos,Ejib1.getpos(),jib_set)
                save_slew= 0#slew_reck()
                save_comp=comp_pos(Ecomp.getpos())
                
                #Prepare UART string
                tilstring = '<' + str(save_boom_pos) + ' ' + str(save_jib_pos) + ' ' + str(save_slew) + ' ' + str(save_comp) + '>'
                pakke = struct.pack('@20s', tilstring)
                uart1.write(pakke)
                
                #Debug switch on controller
                if DEC_SW[6] == 1:
                    
                    #print('Heave mm/s:', heave_save)
                    #print('Winch:',Ewinch.getpos())
                    #print('Comp :',Ecomp.getpos())
                    #print('Jib1 :',Ejib1.getpos())
                    #print('Jib2 :',Ejib2.getpos())
                    #print('Boom :',Eboom.getpos())
                    
                    print('\nComp Pos  :',save_comp,'mm')
                    print('Boom Angle:',save_boom_pos)
                    print('Jib  Angle:',save_jib_pos)
                    print('Slew Angle:',slew_reck())
                    pass
                
                
        #Heave Task      
        if time.ticks_diff(time.ticks_ms(),HEAVE_RECENT) >= HEAVE_REFRESH:                
                HEAVE_RECENT = time.ticks_ms()
                
                #ACTIVE HEAVE CALCULATION
                if DEC_SW[5] == 1:
                    #heave_save = heave_calc(POS,float(IMU[0]),save_slew,save_boom_pos,save_jib_pos,float(IMU[3])/10000,float(IMU[2]))
                    heave_save = heave_calc(POS,0,0,0,0,0,0)
                    print(compensate(heave_save))
                #RESLACK ON BUTTON PRESS
                if DEC_SW[2] == 0:
                    RESLACK(Ejib1.getpos(),save_boom_pos,jib_set,correction_map)
                
    
    # 3. sender telemetri tilbake
    send_packet(bytes([status[0], status[1] & 0x7F]))

    # 4. Back to RX
    flush_and_rx()
    loop_tid = time.ticks_diff(time.ticks_ms(), timing)
    print(loop_tid)
    #if loop_tid < 40:
    #    time.sleep_ms(40-loop_tid)
    timing = time.ticks_ms()
    
    
    
    
print('feil partnum og/eller version')

    
