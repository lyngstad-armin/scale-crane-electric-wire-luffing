from machine import UART, I2C, Pin
import time
import utime
import math
from bmi160 import BMI160
import struct

## Pins
led = Pin("LED", Pin.OUT);
led.on()

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
##


def lesing():
    if uart1.any():
        temp = uart1.read()
        temp1 = struct.unpack('@30s', temp)
        print(temp1)
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

def ultralyd_poll():
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
    y = (((lyd_dt/2)/1000000) * 343) * 1000
    return y

def gyropoll():
    gx, gy, gz = imu.gyro()
    gx = gx * (2000/32768) * (math.pi / 180)
    gy = gy * (2000/32768) * (math.pi / 180)
    gz = gz * (2000/32768) * (math.pi / 180)
    return gx, gy, gz

def accelpoll():
    ax, ay, az = imu.accel()
    ax = (ax * (32/32768))
    ay = (ay * (32/32768))
    az = (az * (32/32768))
    return ax, ay, az
    
imu = BMI160(i2c)

## initialiser gyro posisjon
startaccel = accelpoll()
roll_filtered = math.atan2(startaccel[1], startaccel[2]) ## starter roll fra accelerometer posisjon
##

## declare loop parametre
alfa = 0.98
periode = 40
teller1 = 0
teller = 0
sist = time.ticks_ms()
radius = 275.19 # radius fra senter av stewart til pin som holder ultralyd
theta_offset = 0.0946
run_y_read : list = []
pos_filter : list = [ultralyd_poll() - radius*math.sin(-roll_filtered-theta_offset)]
rolldt_export : list = []
pos_export : list = []
dt : list = []
run_dt : list = []
dt_filter : list  = []
pos_len : int = 4
dt_len : int = 4
count : int = 0
comb : list = [0,0,0]
hdt_uart : float = 0.0
lagrekran = ''
start_absolutt = time.ticks_ms()
##

# main loop
time.sleep_ms(100)
while True:
    start = time.ticks_ms()
    
    teller1 += 1
    teller += periode
    
    loopaccel = accelpoll()
    loopgyro = gyropoll()
    
    now = time.ticks_ms()
    dt = time.ticks_diff(now, sist) * 0.001
    sist = now
    roll_acc = math.atan2(loopaccel[1], loopaccel[2])
    roll_filtered = (alfa*(roll_filtered + loopgyro[0] * dt) + (1-alfa) * roll_acc)
    
    y = ultralyd_poll() - radius*math.sin(-roll_filtered-theta_offset)
    
    
    ## armin filter
    count += 1
    comb[count-1] = y

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
            dt_val = (pos_filter[-1]-pos_filter[-2])/0.12
        else:
            dt_val = 0
        #Dt_filter
        run_dt.append(dt_val)
        if len(run_dt) > dt_len:
            run_dt.pop(0)
        if teller <= 500:
            roll_prev = roll_filtered

        hdt_uart = str(round(sum(run_dt)/len(run_dt),3))
    ##
    
    ## Skriv til kran
    absolutt_tid = time.ticks_diff(time.ticks_ms(), start_absolutt)
    if absolutt_tid > 90000:
        start_absolutt = time.ticks_ms()
    tilstring = '<'+str(round(roll_filtered, 6)) + ' ' + str(round(pos_filter[-1], 1)) + ' ' + str(hdt_uart) + ' ' + str(absolutt_tid) +'>'
    pakket_data = struct.pack("@35s", tilstring)
    uart1.write(pakket_data)
    ##
    
    ## les fra kran og send til server
    frakran = lesing()
    #print(frakran)
    if frakran != '0':
        lagrekran = frakran.replace('\x00','')
    tilstring = '<' + lagrekran+ ' ' + str(round(roll_filtered, 3)) + ' ' + str(round(pos_filter[-1], 1)) + '>'
    pakket_data = struct.pack('@40s', tilstring)
    print(struct.unpack('@40s', pakket_data))
    uart.write(pakket_data)
    
    brukt_tid = time.ticks_diff(time.ticks_ms(), start)
    if brukt_tid < periode:
        time.sleep_us(int(periode-brukt_tid)*1000)

    













