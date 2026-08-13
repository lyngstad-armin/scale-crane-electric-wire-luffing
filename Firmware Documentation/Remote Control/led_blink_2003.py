from machine import Pin
from time import sleep

RF = Pin(4, Pin.OUT, value=0)
MODE = Pin(11, Pin.OUT, value=0)
WNCH = Pin(13, Pin.OUT, value=0)
JIB = Pin(22, Pin.OUT, value=0)
LQIH = Pin(21, Pin.OUT, value=0)
LQIL = Pin(14, Pin.OUT, value=0)

x = 0
while x < 10:
    x += 1
    RF.toggle()
    sleep(0.1)
    MODE.toggle()
    sleep(0.1)
    WNCH.toggle()
    sleep(0.1)
    JIB.toggle()
    sleep(0.1)
    LQIL.toggle()
    sleep(0.2)
    LQIH.toggle()
    sleep(0.1)