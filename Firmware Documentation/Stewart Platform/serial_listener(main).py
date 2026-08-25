import sys
import select
from machine import Pin, WDT
from accel import stacy
import gc
import time
DEBUG = True

#Create Objects and Dict
enab_p = Pin(20,Pin.OUT)
s1 = stacy(0,1)
s2 = stacy(8,9)
s3 = stacy(6,5)
s4 = stacy(28,18)
s5 = stacy(26,22)
s6 = stacy(21,19)
dm = {0:s1,1:s2,2:s3,3:s4,4:s5,5:s6}

#Disable motor current
enab_p.value(1)

if DEBUG != True:
    wdt = WDT(timeout=8300)
 
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)
buf = bytearray()
PACKET_LEN = 19  # cmd (1) + 6 motors x 3 bytes = 19
while True:
    if DEBUG != True:
        wdt.feed()
    events = poll.poll(100)  # wait up to 100ms for data, then loop again regardless
    if events:
        buf += sys.stdin.buffer.read(1)
    if len(buf) < PACKET_LEN:
        continue
    raw = bytes(buf[:PACKET_LEN])
    buf = buf[PACKET_LEN:]
    cmd = raw[0]
    param = raw[1:19]
 
 
    try:
        #Command ON
        if cmd == 0x10:
            enab_p.value(0)
            for i in range(6):
                dm.get(i).stop()
            sys.stdout.buffer.write(bytes([1]))
     
        #Command OFF
        elif cmd == 0x11:
            enab_p.value(1)
            for i in range(6):
                dm.get(i).stop()
            sys.stdout.buffer.write(bytes([2]))
     
        #Command MOTOR DATA
        elif cmd == 0x12:
            for i in range(6):
                b0 = param[3*i]
                b1 = param[3*i + 1]
                b2 = param[3*i + 2]
                payload = ((b0 & 0x7F) << 14) | ((b1 & 0x7F) << 7) | (b2 & 0x7F)
                on = (payload >> 15) & 0x1
                direction = (payload >> 14) & 0x1
                speed = payload & 0x3FFF
                motor = dm.get(i)
                if on == 1:
                        motor.speed(speed)
                        sign = 1 if direction == 1 else -1
                        motor.run(sign)
                else:
                    if motor.motor_active == True:
                        motor.stop()
            sys.stdout.buffer.write(bytes([3]))
            
             #Unrecognized command
        else:
            sys.stdout.buffer.write(bytes([0xFE]))
     
    except Exception as e:
        # Report error over serial instead of letting the script crash to REPL
        sys.stdout.buffer.write(bytes([0xFF]))
        sys.stdout.buffer.write(str(e).encode())
        sys.stdout.buffer.write(b'\n')