#MOTOR RC DECODING AND MOTOR COMMANDS
from velo import stacy, encoder, link
from machine import UART, Pin, SPI, WDT
import struct, time, gc, bisect, umatrix, math




'''===========================================================================================================
DECLARE ALL INPUTS AND OUTPUTS
RELATED TO MOTOR FUNCTION

FOR MOTOR:
OBJECTNAME = stacy(PUL,DIR)

FOR ENCODER:
OBJECTNAME = encoder(SDA,SCL,CHANNEL,SAVE ID, FREQUENCY[Hz], AVERAGE OVER X READS)

FOR LINK:
OBJECTNAME = link(MOTOR,ENCODER)
'''

#DECLARE MOTOR WIRING
jib2 = stacy(0,1)
jib1 = stacy(3,2)
comp1 = stacy(8,20)
comp2 = stacy(11,10)
winch = stacy(13,12)
boom = stacy(15,14)
slew1 = stacy(6,7,rid=1) #rid = 1 
slew2 = stacy(22,21)

#DECLARE ENCODERS
time.sleep(0.5)
Ejib2 = encoder(26,27,ch=5,sid=1,freq=60,mva=1)
Eboom = encoder(26,27,ch=6,sid=2,freq=60,mva=1)
Ejib1 = encoder(26,27,ch=7,sid=3,freq=60,mva=1)
Ecomp = encoder(26,27,ch=3,sid=5,freq=60,mva=1)
Ewinch = encoder(26,27,ch=4,sid=4,freq=60,mva=1)

#DECLARE MOTOR LINK
Ljib2 = link(jib2,Ejib2)

'''===========================================================================================================
LOAD ALL LOOKUP TABLES INTO MEMORY
 - BOOM ANGLE LOOKUP
 - RELATIVE BOOM SPEED LOOKUP
 - JIB ANGLE LOOKUP

'''

#LOAD BOOM LOOKUP TABLE
boom_pos : list = []
ang_deg  : list = []
with open('boom_angle.csv','r') as file:
    for line in file:
            row = line.rstrip('\n').rstrip('\r').split(',')
            boom_pos.append(int(row[0]))
            ang_deg.append(int(row[1]))
del file; del line; del row;
gc.collect()

#LOAD RELATIVE BOOM SPEED
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

#JIB ANGLE LOOKUP TABLE
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

'''===========================================================================================================
USE LOOKUP TABLES TO CALCULATE
-BOOM ANGLE
-RELATIVE BOOM SPEED
-JIB ANGLE
'''

#BOOM ANGLE CALCULATION
def boom_angle(l,bp,ad):
    if bp == None:
        return 0
    if l >= 4875:
        return 70
    idex = bisect.bisect(bp,l)
    return ad[idex]

#BOOM SPEED CALCULATION
def boom_speed(act_angle,ang_deg_boom,jib1,jib2):
    if act_angle >= 70:
        return 0.97,0.79
    else:
        idex = bisect.bisect(ang_deg_boom,act_angle)
        return jib1[idex],jib2[idex]

#JIB ANGLE CALCULATION
def jib_angle(boom_angle,jib1e,file):
    jib1pos = []
    jib2pos = []
    offset = 2859
    if jib1e is None:
        return 0
    jibcheck = -jib1e #+ offset
    #print(file)
    for i in range(len(file)):
        #print(boom_angle,i)
        if i == boom_angle:
            sline = file[i]
    del i;
    try:
        l = enumerate(sline)
        for j, info in l:
            if j % 2 == 1:
                jib1pos.append(int(sline[j]))
            #elif j % 2 == 0:
            #    jib2pos.append(int(sline[j]))
        
        del l; del j; del info;
        idex = bisect.bisect(jib1pos,jibcheck)
        #print(idex)
        del jib1pos; del jib2pos;
    except Exception as e:
        print(f"{e}")
        idex = 0
    return 132 - idex*2

'''===========================================================================================================
CALCULATE
-WIRE POSITION
-COMPENSATOR POSITION
-SLEWING DEAD RECKONING
'''

#WIRE POSITION CALCULATION
def wlcalc(read):
    if read <= 0:
        read = -read
    read += 24840
    #print(read)
    i = 0
    length = 0
    gear_ratio = 2.7
    resolution = 400 * gear_ratio
    partial_spool = read % resolution
    spools = read // resolution
    layers = spools // 6
    spools_remainder = spools % 6
    #print(partial_spool, spools, layers, spools_remainder)
    for i in range(int(layers)):
        length += 6*(12+2*i)*math.pi
    length += spools_remainder*(12+(2*(i+1)))*math.pi
    length += (12+2*(i+1))*math.pi*partial_spool / resolution
    
    return round(length,1)

    #Setposition is 3 layers and 5 spools
    #Wire down is encoder negative direction
    #Small gear (driving) is 20 tooth
    #Big gear (driven) is 54 tooth
    #Gear ratio is 2.7

#COMPENSATOR POSITION
def comp_pos(getpos):
    pos = round((getpos) * 110/1160,1)
    if pos >= 110:
        Ecomp.setpos(1160)
        pos = 110.0
    elif pos <= 0:
        Ecomp.setpos(0)
        pos = 0.0
    return pos

    #front to back
    #0mm == fully forward
    #110mm == fully back

#SLEWING DEAD RECKONING
def slew_reck():
    steppos = slew1.getreck()
    angpos =steppos*360 / (38500)  % 360  //1
    return round(angpos,1)

'''===========================================================================================================
HEAVE COMPENSATION INITIALIZATION AND
HEAVE COMPENSATION CALCULATION
'''

#HEAVE COMPENSATION INITIALIZATION
sequence = [0,0,0]
count_over = 0
count_under = 0
def compensate(heave_save, hsave, sequence):
    global count_over, count_under
    #time.ticks_ms()
    hspeed  = -(heave_save+hsave) * 1160/110 *1
    limit = 5
    if abs(hspeed) <= limit:
        #count_under += 1
        hsave += heave_save
        hspeed = 0
        if abs(heave_save) <= 0.2:
            sequence = [sequence[1], sequence[2], None]
        else:
            sequence = [sequence[1], sequence[2], 'On']
        if sequence == [None, None, None]:
            COMP_OFF()
        #print(sequence)
        return hspeed, heave_save, hsave, sequence
    #count_over += 1
    if save_comp < 108 and hspeed >= limit:
        COMP_ON(1)
        COMP_SPD(hspeed,1)
        pass
    elif save_comp > 2 and hspeed <= -limit:
        COMP_ON(0)
        COMP_SPD(-hspeed,0)
        pass
    hsave = 0
    return hspeed, heave_save, hsave, sequence

#===== HEAVE CALCULATION ======
def heave_calc(POS, th1,th2,th3,th4,rolld,hd):
    th4 = -th4
    degrad = math.pi / 180
    
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
    cos = math.cos
    sin = math.sin
    #Relative Rotation Matrices
    
    c1, s1 = cos(th1), sin(th1)
    c2, s2 = cos(th2*degrad), sin(th2*degrad)
    c3, s3 = cos(th3*degrad), sin(th3*degrad)
    c4, s4 = cos(th4*degrad), sin(th4*degrad)
    
    R1 = umatrix.matrix([1,0,0],[0,c1,-s1],[0,s1,c1])  #ROLL
    R21 = umatrix.matrix([c2,-s2,0],[s2,c2,0],[0,0,1]) #SLEW
    R32 = umatrix.matrix([1,0,0],[0,c3,-s3],[0,s3,c3]) #BOOM
    R43 = umatrix.matrix([1,0,0],[0,c4,-s4],[0,s4,c4]) #JIB
    #Additional Relative Rotations
    R21T = R21.transpose
    R31T = R21T * R32.transpose
    R41T = R31T * R43.transpose 
    #Absolute Rotation Matrices
    R2 = R1 * R21
    R3 = R2 * R32
    R4 = R3 * R43
    #Angluar Velocities
    W1 = umatrix.matrix([rolld],[0],[0])
    #Linear Velocity (Heave)
    #ht = umatrix.matrix([0,0,hd]).transpose
    #Lie Group
    #e3 = umatrix.matrix([0,0,1])
    #Simplify multiplication order
    R1C = P_PS*W1
    R2C_1 = R21T*W1
    R2C_2 = P_SB*R2C_1
    R3C_1 = R31T*W1
    R3C_2 = P_BJ*R3C_1
    R4C_1 = R41T*W1
    R4C_2 = P_JR*R4C_1
    
    XCDOT3 = ( R1 * R1C + R2 * R2C_2 + R3 * R3C_2 + R4 * R4C_2)
    return float(hd + XCDOT3[2][0])

'''===========================================================================================================
RADIO SETUP AND CREATE HELPER FUNCTIONS FOR SPI ANTENNA
'''

#SPI
spi = SPI(0, baudrate=2_000_000, polarity=0, phase=0,
          firstbit=SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs  = Pin(17, Pin.OUT, value=1)
#UART
uart1 = UART(1, baudrate=115200, tx=4, rx=5)

#CC1101 HELPERS
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
    deadline = time.ticks_add(time.ticks_ms(), 50)
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

partnum = read_status(0xF0)
version = read_status(0xF1)
print(hex(partnum))
print(hex(version))

'''===========================================================================================================
DECLARE DECODING LISTS AND
DECLARE SKEWED POSITIONAL VECTORS FOR HEAVE COMPENSATION
'''

#DECLARE PAYLOAD LISTS FOR DECODING
zero     : list = [0]
zerobool : list = [False]
DEC_AX   : list = zero*5
DEC_SPD  : list = zero*5
DEC_DIR  : list = zero*5
DEC_SW   : list = zero*7
DATA     : list = zero*6


#DECLARE POSITION VECTORS FOR HEAVE
P_PS = umatrix.matrix( [     0,	 103.6,	  0.0],
                           [-103.6,	     0,	   0.0],
                           [   0.0,	  0.0,	     0] )
#(0,0,103.6)
    
P_SB = umatrix.matrix( [     0,	 -76.67,	22.58],
                           [76.67,	     0,	   0.0],
                           [-22.58,	  0.0,	     0] )
#(0,22.6,76.7)
P_BJ = umatrix.matrix( [     0,	   0.0,	500.0],
                           [  0.0,	     0,	   0.0],
                           [ -500.0,	  0.0,	     0] )
#(0,500,0)    
P_JR = umatrix.matrix( [      0,	110.2,	286.4],
                        [ -110.2,	      0,	    0.0],
                        [ -286.4,	   0.0,	      0] )

#(0,286.4,-110.2)
POS = P_PS.transpose, P_SB.transpose, P_BJ.transpose, P_JR.transpose
del P_PS; del P_SB; del P_BJ; del P_JR


'''===========================================================================================================
DECLARE FUNCTION BLOCKS FOR CRANE OPERATION
'''

#FUNCTIONS ON
def SLEW_ON(dr):
    slew1.run(dr)
    slew2.run(dr)
def COMP_ON(dr):
    if dr == 0:
        dr = -1
    comp1.run(-dr)
    comp2.run(dr)
def BOOM_ON(dr):
    if dr == 0:
        dr = -1
    jib1.run(-dr)
    jib2.run(dr)
    boom.run(dr)
def JIB_ON(dr):
    if dr == 0:
        dr = -1
    jib1.run(dr)
    jib2.run(dr)
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
    comp1.speed(spd*2)
    comp2.speed(spd*2)
    #print(spd)
    
def BOOM_SPD(spd,dr):
    #DYNAMIC SPEED PER POSITION
    try:
        jib1s, jib2s = boom_speed(boom_angle(4675+Eboom.getavg(),boom_pos,ang_deg),ang_deg_boom,jib1_speeds,jib2_speeds)
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
    #2.5 ish should theoretically be dynamic though
    jib2.speed(int(spd*2.5))
    
def WINCH_SPD(spd,dr):
    winch.speed(spd)

def SINGLE_JIB_SPD(spd,dr):
    jib2.speed(spd)

'''===========================================================================================================
CREATE RESLACKING FUNCTION
RETURNS TO LAST CORRECT LOOKUP POSITION FOR UNDERWIRE ACCORDING TO BOOM ANGLE AND JIB ANGLE

CREATE FUNCTIONALITY FOR ADDING CORRECTION MAPS TO THE RESLACKING FUNCTION
-Add correction
-Add correction range
-Create correction map
'''

def RESLACK(jib1e,bangle,jib_set,correction):
    jib1pos = []
    jib2pos = []
    jibcheck = jib1e #+ offset
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

#Generate correction map for reslack function
correction_map = CORRECTION() 

'''===========================================================================================================
UART HELPER FUNCTION FOR MRU
'''

prev_IMU = [None,None,None,None]
prev_parts = [0,0,0,0]
def lesing():
    global prev_IMU, prev_parts
    try:
        if not uart1.any():
            return prev_parts
        
        raw = uart1.read(uart1.any())
        text = raw.decode('utf-8', 'ignore')
        
        start = text.find('<')
        end   = text.find('>')
        
        if start == -1 or end == -1 or end < start:
            return prev_parts
        
        parts = text[start+1:end].split(' ')
        if len(parts) < 4:
            return prev_parts
        
        dt    = int(parts[3]) - int(prev_IMU[3]) if prev_IMU[3] else 0
        rolld = (float(parts[0]) - float(prev_parts[0])) / (dt / 1000) if prev_IMU[0] else 0
        prev_IMU = parts[0:4]
        parts[3] = rolld
        prev_parts = parts[0:4]
        return parts[0:4]

    except Exception:
        return prev_parts

'''===========================================================================================================
DICT FOR HANDLING MOTOR COMMANDS
'''

#DICTS FOR HANDLING MOTOR COMMANDS
ACTUAL_ON    : list = zerobool*5
AXIS_MAP_ON  : dict = {     0:SLEW_ON,
                            1:BOOM_ON,
                            2:JIB_ON,
                            4:COMP_ON,
                            3:WINCH_ON,
                            9:SINGLE_JIB_ON
                                        }
AXIS_MAP_OFF : dict = {     0:SLEW_OFF,
                            1:BOOM_OFF,
                            2:JIB_OFF,
                            4:COMP_OFF,
                            3:WINCH_OFF,
                                       }
AXIS_MAP_SPD : dict = {     0:SLEW_SPD,
                            1:BOOM_SPD,
                            2:JIB_SPD,
                            4:COMP_SPD,
                            3:WINCH_SPD,
                            9:SINGLE_JIB_SPD,
                                        }

'''===========================================================================================================
INITIALIZE RADIO TRANSCIEVER
CONFIGURE TRANSCIEVER FUNCTION
'''


# CC1101 INITIALIZE
cs(0); time.sleep_us(5); cs(1); time.sleep_us(40)
cs(0); time.sleep_us(5); cs(1); time.sleep_ms(100)
strobe(0x30); time.sleep_ms(100)

config = [
    #(0x00,0x01),
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



'''===========================================================================================================
FINAL INITALIZATION BEFORE COMPUTING LOOP
'''

#INITIALIZE POSITIONS FOR BROADCAST
save_boom_pos = boom_angle(-Eboom.getavg(),boom_pos,ang_deg) if Eboom.getavg() is not None else 0
save_jib_pos  = jib_angle(save_boom_pos,-Ejib1.getavg(),jib_set) if Ejib1.getavg() is not None else 0
save_slew= slew_reck()
save_comp=comp_pos(Ecomp.getavg()) if Ecomp.getavg() is not None else 0
save_wire=wlcalc(Ewinch.getavg()) if Ewinch.getavg() is not None else 0

#DECLARE REFRESH SPEEDS FOR REPEATING FUNCTIONS
ENCODER_RECENT         : int = 0
ENCODER_REFRESH        : int = 1800 #ms between refreshes on encoder active code
PAYLOAD_PACKET_RECENT  : int = 0
PAYLOAD_PACKET_REFRESH : int = 100 #ms between refreshes on decoded data and motor signals
POS_RECENT             : int = 0
POS_REFRESH            : int = 100 #ms
HEAVE_RECENT           : int = 0
HEAVE_REFRESH          : int = 80 #ms
hsave = 0
heave_on = 0
del zero; del zerobool;

print("System Initialized")
flush_and_rx()

#CLEAR UART BUFFER
def clear_rx_buffer(uart):
    uart.read(uart.any())
clear_rx_buffer(uart1)
timing = 0

#Watchdog timer for automatic restart after error code
#wdt = WDT(timeout=7000)

'''===========================================================================================================
COMPUTING LOOP
'''

while True:
    #wdt.feed()
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
        Ecomp.save_rotation()
        
    # 1. Wait for joystick packet
    rxb = wait_packet(timeout_ms=300)
    IMU = lesing()
    print(IMU)
    #print(IMU)
    
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
        
        #PAYLOAD TASK --- DECODE STRUCT PACKET AND RUN MOTORS
        if time.ticks_diff(time.ticks_ms(),PAYLOAD_PACKET_RECENT) >= PAYLOAD_PACKET_REFRESH:
            PAYLOAD_PACKET_RECENT = time.ticks_ms()
            DATA = struct.unpack('BBBBBB', payload)
            #DECODE PAYLOAD
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

            #ACTUATE MOTORS
            for i in range(5):
                g = i
                #SINGLE JIB EDGE CASE
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
                if DEC_SW[5] == 0:
                    #Calculate crane positions
                    save_boom_pos = boom_angle(-Eboom.getavg(),boom_pos,ang_deg) if Eboom.getavg() is not None else 0
                    save_jib_pos  = jib_angle(save_boom_pos,-Ejib1.getavg(),jib_set) if Ejib1.getavg() is not None else 0
                save_slew= slew_reck()
                save_comp=comp_pos(Ecomp.getavg()) if Ecomp.getavg() is not None else 0
                save_wire=wlcalc(Ewinch.getavg()) if Ewinch.getavg() is not None else 0
                
                #Prepare UART string
                tilstring = '<' + str(save_boom_pos) + ' ' + str(save_jib_pos) + ' ' + str(save_slew) + ' ' + str(save_comp) + ' ' + str(save_wire) + '>'
                tsSPI = '<' + str(save_boom_pos) + ' ' + str(save_jib_pos) + ' ' + str(save_slew) + ' ' + str(save_comp) + '>'
                pakke = struct.pack('@30s', tilstring)
                pakkeSPI = struct.pack('@20s', tsSPI)
                uart1.write(pakke)
                
                #Debug switch on controller
                if DEC_SW[6] == 1:
                    #print(DEC_SW)
                    
                    #print('Heave mm/s:', heave_save)
                    print('Winch:',Ewinch.getavg())
                    print('Comp :',Ecomp.getavg())
                    print('Jib1 :',Ejib1.getavg())
                    print('Jib2 :',Ejib2.getpos())
                    print('Boom :',Eboom.getavg())
                    
                    print('\nComp Pos:',save_comp,'mm')
                    print('Boom Angle:',save_boom_pos)
                    print('Jib  Angle:',save_jib_pos)
                    print('Slew Angle:',slew_reck())
                    print('Wire Length:',save_wire,'mm')
                    pass
                if DEC_SW[2] == 0:
                    #RESLACK(Ejib1.getavg(),save_boom_pos,jib_set,correction_map)
                    #print(DEC_SW)
                    pass
        #Heave Task      
        if time.ticks_diff(time.ticks_ms(),HEAVE_RECENT) >= HEAVE_REFRESH:                
                HEAVE_RECENT = time.ticks_ms()
                
                #ACTIVE HEAVE CALCULATION
                if DEC_SW[5] == 1:
                    heave_on = 1
                                             #V    #Roll                                                 #Rolld     #Heaved
                    heave_save = heave_calc(POS,float(IMU[0]),save_slew,save_boom_pos,save_jib_pos,float(IMU[3]),float(IMU[2]))
                    
                   
                    hspeed, heave_save, hsave, sequence = compensate(heave_save, hsave, sequence)
                    #print('\n\n\n',round(hspeed,0))
                    #print('\n', 'Co:',count_over,'Cu:',count_under)
                
                elif DEC_SW[5] == 0:
                    if heave_on == 1:
                        COMP_OFF()
                        heave_on = 0
                    
                #RESET SWITCH
                if DEC_SW[4] == 1:
                    slew1.resetreck()
                    Eboom.setpos(0)
                    Ejib1.setpos(0)
                    Ejib2.setpos(0)
                    Ewinch.setpos(0)
                    
                    #RESLACK(Ejib1.getpos(),save_boom_pos,jib_set,correction_map)
                
    
    #RESPOND TO REMOTE
    send_packet(bytes([status[0], status[1] & 0x7F]) + pakkeSPI)
    
    #RETURN TO RX
    flush_and_rx()
    
    
    
print('feil partnum og/eller version')

    
  