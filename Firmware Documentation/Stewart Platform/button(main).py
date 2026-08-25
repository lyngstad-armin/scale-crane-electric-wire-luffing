from machine import Pin
import time
import gc
led = Pin(25, Pin.OUT)
button = Pin(15, Pin.IN, Pin.PULL_UP)
button_stop = Pin(13, Pin.IN, Pin.PULL_UP)

#0 if pressed

run_sc = 0

print('Main loop started')
while True:
    led.value(1)
    if button.value() == 0:
        run_sc = 1
    if button_stop.value() == 0:
        run_sc = 0
    #print(run_sc)
    #print(button_stop.value())
    
    
    if run_sc == 1:
        exec(open('accel_control.py').read())
    #print('\nWaiting')
    time.sleep(0.05)
