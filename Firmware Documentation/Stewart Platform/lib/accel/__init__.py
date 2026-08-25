#Stepper Accel Library
from machine import Pin, PWM
#import time

#Stepper library that enables acceleration without blocking main script
class stacy:
    def __init__(self,step_pin,dir_pin,SPSA = 1600):
    
        self.PWM = PWM(Pin(step_pin),freq = 1000, duty_ns=40000)
        self.PWM.deinit()
         
        self.DIR = Pin(dir_pin, Pin.OUT)
        self.DIR_VALUE = 0
        
        self.SPSA = SPSA
        
        self.motor_active = False
                    
    #Set Speed
    def speed(self,sps):
        if sps < 60:
            self.stop()
        self.SPSA = sps
        if self.motor_active == True:
            self.run(self.DIR_VALUE)
    
    def run(self,d):
        if d == -1:
            d = 0
        self.DIR_VALUE = d
        self.DIR.value(self.DIR_VALUE)
        
        self.PWM.init(freq=self.SPSA)
        self.motor_active = True

    def stop(self):
        self.PWM.deinit()
        self.motor_active = False
        
s4 = stacy(28,18)
s4.run(1)
