from machine import UART, I2C, Pin
import time
import utime
import math
from bmi160 import BMI160
import struct

trig = Pin(7, Pin.OUT)
echo = Pin(6, Pin.IN)

i2c = I2C(
    1,
    sda=Pin(10),
    scl=Pin(11),
    freq=400_000
)

uart = UART(0, baudrate=115200, tx=0, rx=1)
uart1 = UART(1, baudrate=115200, tx=4, rx=5)

def lesing():
    if uart1.any():
        temp = uart1.read()
        temp1 = struct.unpack('@20s', temp)
        temp2 = temp1[0].decode("utf-8")
        if temp2.find("<") != -1 and temp2.find(">") != -1:
            temp = temp2.replace(">", "")
            temp1 = temp.replace("<", "")
            IMU = temp1
        else:
            IMU = '0'
    else:
        IMU = '0'
    return IMU

imu = BMI160(i2c)
utime.sleep_ms(500)

periode = 40
dt = 0.05
x = 0
alfa = 0.98
lagrekran = '0 0 0 0'
# initialiser gyro posisjon
ax, ay, az = imu.accel()
raw_roll_gyro = math.atan2(ay, az)
raw_pitch_gyro = math.atan2(-ax, math.sqrt(ay**2+az**2))
roll_filtered = raw_roll_gyro
pitch_filtered = raw_pitch_gyro
yaw_raw = 0



# vi initialiserer høyden
puls_start = 0
puls_slutt = 0
y_abs = 0
teller1 = 0


trig.low()
utime.sleep_us(2)
trig.high()
utime.sleep_us(10)
trig.low()


while echo.value() == 0:
    pass  
puls_start = utime.ticks_us()  

while echo.value() == 1:
    pass
puls_slutt = utime.ticks_us()

    
lyd_dt = time.ticks_diff(puls_slutt, puls_start)
y_start = (((lyd_dt/2)/1000000) * 343) * 1000
y_prev = y_start

time.sleep_us(int(periode*1000)) # MÅ ha denne eller fucker signalene i ultralyden seg

stew_start = False
stewart_initialroll = 0
deltaroll = 0
y_rel_rettet = 0
radius = 275.19 # radius fra senter av stewart til pin som holder ultralyd
theta_offset = 0.0946

sist = time.ticks_ms()
fmt = "@30s"
datating = []
teller = 0

run_y_read : list = []
pos_filter : list = []
rolldt_export : list = []
pos_export : list = []
dt : list = []
run_dt : list = []
dt_filter : list  = []
pos_len : int = 8
dt_len : int = 8
count : int = 0
comb : list = [0,0,0]
roll_filter: list = []
led = Pin("LED", Pin.OUT);
led.on()
rolldrift = raw_roll_gyro
raw = []
while True:
    teller1 += 1
    teller += periode
    start = time.ticks_ms()
    trig.low()
    utime.sleep_us(2)
    trig.high()
    utime.sleep_us(10)
    trig.low()
    pulse_timeout = time.ticks_ms()
    while echo.value() == 0:
        if time.ticks_diff(time.ticks_ms(), pulse_timeout) > 200:
            print('timeout')
            break
        pass  
    puls_start = time.ticks_us()
    while echo.value() == 1:
        if time.ticks_diff(time.ticks_ms(), pulse_timeout) > 200:
            print('timeout')
            break
        pass  
    puls_slutt = time.ticks_us()
    lyd_dt = time.ticks_diff(puls_slutt, puls_start)
    y_abs = (((lyd_dt/2)/1000000) * 343) * 1000
    y_rel = y_abs-y_start
    
    ax, ay, az = imu.accel()
    #ax = (ax * (32/32768))#//16
    ay = (ay * (32/32768))#//16
    az = (az * (32/32768))#//16
    
    gx, gy, gz = imu.gyro()
    gx = gx * (2000/32768) * (math.pi / 180)
    print(gx)
    #gy = gy * (2000/32768) * (math.pi / 180)
    #gz = gz * (2000/32768) * (math.pi / 180)

    roll_acc = math.atan2(ay, az)
    #pitch_acc = math.atan2(-ax, math.sqrt(ay**2+az**2))
    now = time.ticks_ms()
    dt = time.ticks_diff(now, sist) * 0.001
    sist = now
    prev = roll_filtered
    roll_filtered = (alfa*(roll_filtered + gx * dt) + (1-alfa) * roll_acc)
    
    #print(roll_filtered)
    y_abs_rettet = y_abs - radius*math.sin(-roll_filtered-theta_offset)
    #count vals
    
    count += 1
    comb[count-1] = y_abs_rettet

    if count == 3:
        #combine vals
        run_y_read.append(sum(comb)/3)
        count = 0
        comb = [0,0,0]
        #Pos_filter
        if len(run_y_read) > pos_len:
            run_y_read.pop(0)
        pos_filter.append(sum(run_y_read)/len(run_y_read))
        if len(pos_filter) > 3:
            pos_filter.pop(0)
        #Dt_create
        if teller1 > 16:
            dt_val = pos_filter[-1]-pos_filter[-2]
        else:
            dt_val = 0
        #Dt_filter
        run_dt.append(dt_val)
        if len(run_dt) > dt_len:
            run_dt.pop(0)
        if teller <= 500:
            roll_prev = roll_filtered
        filter_start = time.ticks_ms()
        rolldt = (round(roll_filtered - roll_prev,6))
        roll_prev = roll_filtered
        
        
        
        rolldt = str(round(rolldt*100000, 2))
        hdt_uart = str(round(sum(run_dt)/len(run_dt),3))
        
        tilstring = '<'+str(round(roll_filtered, 3)) + ' ' + str(round(pos_filter[-1], 1)) + ' ' + str(hdt_uart) + ' ' + rolldt +'>'
        pakket_data = struct.pack(fmt, tilstring)
        uart1.write(pakket_data)
        frakran = lesing()
        #print(frakran)
        if frakran != '0':
            lagrekran = frakran.replace('\x00','')
        tilstring = '<' + lagrekran+ ' ' + str(round(roll_filtered, 3)) + ' ' + str(round(pos_filter[-1], 1)) + '>'
        pakket_data = struct.pack('@33s', tilstring)
        #print(struct.unpack('@33s', pakket_data))
        uart.write(pakket_data)
    
    brukt_tid = time.ticks_diff(time.ticks_ms(), start)
    if brukt_tid < periode:
        time.sleep_us(int(periode-brukt_tid)*1000)
            
print('filtd=',dt_filter,'\nroll=',roll_filter,'\npos=',pos_export,'\nrolld=',rolldt_export)
print(drift)
print(nodrift)

        
        
        
        

