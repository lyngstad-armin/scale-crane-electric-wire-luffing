#Stepper Accel Library
from machine import Pin, PWM, Timer, I2C
import time

#Stepper library that enables acceleration without blocking main script
class stacy:
    def __init__(self,step_pin,dir_pin,SPSA = 400, ACCEL = 1, RECK = 0):
    
        self.PWM = PWM(Pin(step_pin),freq = 1000, duty_ns=10000)
        self.PWM.deinit()
         
        self.DIR = Pin(dir_pin, Pin.OUT)
        self.DIR_VALUE = 0
        
        self.SPSA = SPSA
        self.SPST = SPSA
        self.ACCEL = ACCEL
        self.timer_freq = 100
        
        self.motor_active = False
        self.timer_on()
        self.timer_off()
        
        #DEAD RECKONING (FOR SLEW)
        self.do_reckoning = RECK
        if self.do_reckoning == 1:
            
            self.write_refresh = 1000 #ms refresh write
            self.write_recent = 0
            self.reckoning = 0
            self.reck_active = False
            with open('reckoning.csv','r') as file:
                for line in file:
                    row = line.rstrip('\n').rstrip('\r').split(',')
                    self.reckoning = float(row[0])
    #RECK TIMER ON             
    def reckon_timer_on(self):
        self.reck = Timer(-1)
        self.reck.init(mode=Timer.PERIODIC,freq = 20,callback=self.reck_update)
        self.reck_active = True
        
    #RECK TIMER OFF
    def reckon_timer_off(self):
        self.reck.deinit()
        self.reck_active = False
    #RECK UPDATE
    def reck_update(self,timer):
        if self.motor_active == False:
            self.reckon_timer_off()
        else:
            if self.DIR_VALUE == 0:
                d = -1
            else:
                d = 1
            self.reckoning += round(d*self.SPSA/20,3)
            #check rollover
            if self.reckoning >= 15150:
                self.reckoning = 0
            elif self.reckoning < 0:
                self.reckoning = 15149
                
                
            if time.ticks_diff(time.ticks_ms(),self.write_recent) >= self.write_refresh:
                self.write_recent = time.ticks_ms()
                with open('reckoning.csv','w') as f:
                    f.write("{}\r\n".format(round(self.reckoning,1)))
    
    
    #GET RECKONING POSITION
    def get_reck(self):
        #print(round(self.reckoning,1))
        return round(self.reckoning,1)

    #Set Speed
    def speed(self,sps):
        if sps < 0:
            sps = -sps
            self.DIR_VALUE = -1
        self.SPSA = sps
        self.SPST = sps
        if self.motor_active == True:
            self.run_s(self.DIR_VALUE)
            
    #Speed Ramp
    def speed_r(self,sps):
        if sps < 0:
            sps = -sps
            self.DIR_VALUE = -1
        self.SPST = sps   
        self.timer_on()
    
    #Initialize timer for constant refresh callback
    def timer_on(self):
        self.tim = Timer(-1)
        self.tim.init(mode=Timer.PERIODIC,freq = self.timer_freq,callback=self.update)
        self.timer_active = True
        
    #Turn off timer
    def timer_off(self):
        
        #Supposed to deinitialize timer
        self.tim.deinit()
        self.timer_active = False
        #print('stepper timer off') #PRINTTIMERSTEPPER


    def update(self,timer):
        if self.motor_active == False:
            self.timer_off()
            #print('active false')
        else:
            if self.SPSA == self.SPST:
                self.timer_off()
                #print('==')
            elif self.SPSA > self.SPST:
                self.SPSA -= self.ACCEL
            elif self.SPSA < self.SPST:
                self.SPSA += self.ACCEL
            self.PWM.init(freq=self.SPSA)
            if self.SPSA <= 40:
                self.PWM.deinit()
                self.stop()
                #print('<40')
                self.SPSA = 400
    def run(self,d):
        if d == -1:
            d = 0
        self.DIR_VALUE = d
        self.DIR.value(self.DIR_VALUE)
        
        self.PWM.init(freq=self.SPSA)
        self.motor_active = True
        
        if self.do_reckoning == 1:
            self.reckon_timer_on()      
    def run_s(self,d):
        if d == -1:
            d = 0
        self.DIR_VALUE = d
        self.DIR.value(self.DIR_VALUE)
        
        self.PWM.init(freq=self.SPSA)
        self.motor_active = True
            
    def stop(self):
        self.timer_off()
        self.PWM.deinit()
        self.motor_active = False
            
    def stop_r(self):
        self.speed_r(0)
    
    #def ramp_calc(self,SPSA,SPST):
    #    displacement = (SPST**2 - SPSA**2)/(2*self.ACCEL*self.timer_freq)
    #    #print('Steps:',displacement,'\nDegrees:',displacement*360/400)
    #    return displacement
    
    
    
#===========================Encoder class to deal with encoders======================================
class encoder:
    def __init__(self,sda_pin,scl_pin,adress=0x36,resolution=400,sid = 1,ch=7):
        #Declare initial variables
        self.sda_pin = Pin(sda_pin)
        self.scl_pin = Pin(scl_pin)
        self.adress = adress
        self.resolution = resolution
        #id for memory.csv
        self.sid = sid
        self.ch = ch
        #Declare I2C
        self.i2c = I2C(1, scl=self.scl_pin, sda=self.sda_pin, freq=400000)
        
        #Scan i2c #self.i2cdevices = self.i2c.scan()
        
        #Fetch Roations
        self.rotations = 0
        #Is this really needed?
        try:
            self.muxch(self.ch)
        except Exception as e:
            print(f"Unexpected exception MUX: {e}")
        finally:
            self.fetch_rotations()
        
        #Log quadrant for rotation detection
        self.log_quadrant = []
        
        
        #Init read
        try:
            data = self.i2c.readfrom_mem(self.adress,0x0c ,2)
            angle = int.from_bytes(data,"big")
            self.read = angle // (4096/self.resolution)
        except Exception as e:
            print(f"Unexpected exception READ: {e}")
        
        #Flash timer
        self.timer_freq = 50
        self.timer_on()
        self.timer_off()
        
        #---------------
        #End of __init__
        #---------------
        
    def muxch(self,ch):
        if ch >= 0 and ch < 8:
            self.i2c.writeto(0x70,bytes([1 << ch]))
            #print(ch)
        
    #Fetch Rotations from memory.csv
    def fetch_rotations(self):
        with open('memory.csv','r') as file:
            lid = 0
            for line in file:
                lid += 1
                if lid == self.sid:
                    row = line.rstrip('\n').rstrip('\r').split(',')
                    self.rotations = int(row[0])
                    #print(self.rotations)
        
        
        
        
    #Callback loop for machine timer 
    def update(self,timer_on):
        
        #Change MUX to correct channel
        self.muxch(self.ch)
        #Fetch I2C data from sensor
        data = self.i2c.readfrom_mem(self.adress,0x0c ,2)
        angle = int.from_bytes(data,"big")
        self.read = angle // (4096/self.resolution)
        
        #Store rotations in memory
        self.log_quadrant.append(1+(angle // (1028)))
        if len(self.log_quadrant) > 2:
            self.log_quadrant.pop(0)
        if 4 in self.log_quadrant and 1 in self.log_quadrant:
            if self.log_quadrant[0] > self.log_quadrant[1]:
                self.rotations += 1
            else:
                self.rotations -= 1
                
            #Fetch all rotations (all sensors)
            temp_data = []
            with open('memory.csv','r') as file:
                for line in file:
                    row = line.rstrip('\n').rstrip('\r').split(',')
                    temp_data.append(int(row[0]))
            #Overwrite current sensor id rotation
            temp_data[self.sid-1] = self.rotations
            
            #print(temp_data) #Temp print
            
            #Write to memory with updated rotation index
            with open('memory.csv','w') as f:
                for i in temp_data:
                    csv_line = "{}\r\n".format(i)
                    f.write(csv_line)
                    
        
        #Decrease time left in ontime
        self.duration -= 1/self.timer_freq
        if self.duration <= 1/self.timer_freq:
            self.timer_off()
        if self.duration <= 0:
            self.tim.deinit()
            self.timer_off()
            #print('<=0 failure')
        #Temp print to show enabled
        #print(self.read)
        
        
        
    #Create internal machine timer for updates
    def timer_on(self):
        
        self.tim = Timer(mode=Timer.PERIODIC,freq = self.timer_freq,callback=self.update)
        self.timer_active = True
    #Create timer shutoff    
    def timer_off(self):
        #self.tim.init(freq=1)
        self.tim.deinit()
        self.timer_active = False
        
        
    #Tick timer and set ontime
    def enable(self,duration = 10):
        
        self.timer_off()
        self.fetch_rotations()
        self.timer_on()
        self.duration = duration
    
    #Force off
    def stop(self):
        self.timer_off()
        
    #Pull position
    def getpos(self):
        #(self.rotations*400+self.read)
        try:
            data = self.i2c.readfrom_mem(self.adress,0x0c ,2)
            #self.read = int.from_bytes(self.i2c.readfrom_mem(self.adress,0x0c ,2),"big") // (4096/self.resolution)
            self.pos = self.rotations*400 + self.read
        except Exception as e:
            print(f"Can't read I2C data")
            print(f"{e}")
            self.read = 0
            self.pos = 0
        return self.pos
    
    #Set 0 rotations
    def setpos(self):
        temp_data : list = []
        with open('memory.csv','r') as file:
            for line in file:
                row = line.rstrip('\n').rstrip('\r').split(',')
                temp_data.append(int(row[0]))
            #Overwrite current sensor id rotation
        temp_data[self.sid-1] = 0
        self.rotations = 0
            #Write to memory with updated rotation index
        with open('memory.csv','w') as f:
            for i in temp_data:
                csv_line = "{}\r\n".format(i)
                f.write(csv_line)
    
#=======================Class object to link a stepper motor to an encoder==============================================    
class link:
    
    def __init__(self,stepper,encoder):
        self.stepper = stepper
        self.encoder = encoder
        
        self.timer_freq = 200
        self.timer_on()
        self.timer_off()
        
        self.allow_stop_r = 0
        
    def timer_on(self):
        self.tim = Timer(-1)
        self.tim.init(mode=Timer.PERIODIC,freq = self.timer_freq,callback=self.update)
        self.timer_active = True
    def timer_off(self):
        self.tim.deinit()
        self.timer_active = False
        #print('link timer off') #PRINTTIMERLINK
        
    def update(self,timer):
        self.timestep += (1/self.timer_freq)*1000
        if self.timestep >= self.time_rampdown and self.allow_stop_r == 1:
            self.allow_stop_r = 0
            
            #TODO debug this
            self.stepper.stop_r()
            self.timer_off()
        elif self.timestep > 25*10**3:
            self.timer_off()
            print('link timeout')
        
        
        
    def goto(self,go_pos,speed=800,sspeed=0,a = 0):
        if sspeed == 0:
            sspeed = self.stepper.SPSA
        if a == 0:
            a = self.stepper.ACCEL
        self.stepper.ACCEL = a
        #Find current position
        curr_pos = self.encoder.getpos()
        diff_pos = go_pos - curr_pos
        #Find how many steps ramping takes
        ramp_up = self.stepper.ramp_calc(sspeed,speed)
        ramp_down = self.stepper.ramp_calc(40,speed)
        #Calculate start and stop times to hit target
        time_up = ramp_up // self.stepper.ACCEL
        time_down = ramp_down // self.stepper.ACCEL
        #Steps from ramp_up to ramp_down
        if diff_pos < 0:
            between_steps = -(diff_pos+ramp_up)
            direction = -1
        elif diff_pos > 0:
            between_steps = diff_pos - ramp_up
            direction = 1
        #Time duration between_steps
        between_time = (between_steps*1000/speed) // 1
        #Total time
        total_time = (time_up + between_time + time_down) // 1
        ramp_down_time = (time_up + between_time) // 1
        
        
        #Run command
        self.timestep = 0
        self.time_rampdown = ramp_down_time
        
        self.encoder.enable(total_time/1000 +0.5)
        self.stepper.DIR_VALUE = direction
        
        
        #TODO debug this
        
        self.stepper.speed(sspeed)
        self.stepper.run(direction)
        self.stepper.speed_r(speed)
        
        self.allow_stop_r = 1
        self.timer_on()
        
        #print(diff_pos,ramp_up,ramp_down,time_up,time_down,between_time,between_steps,total_time)
    
    def go(self,pos,speed=800,sspeed=400,r=0):
        curr_pos = self.encoder.getpos()
        if pos < 0:
            pos = -pos
            direction = -1
        else:
            direction = 1
        target_pos = curr_pos + pos*direction
        #Distance and time for ramps
        ramp_down = self.stepper.ramp_calc(40,speed)
        ramp_up = self.stepper.ramp_calc(sspeed,speed)
        time_up = ramp_up // self.stepper.ACCEL
        time_down = ramp_down // self.stepper.ACCEL
        
        between_steps = (pos - ramp_down - ramp_up) // 1
        between_time = (between_steps*1000/speed) // 1
        
        total_time = time_up + time_down + between_time
        ramp_down_time = between_time + time_up
        
        self.timestep = 0
        self.time_rampdown = ramp_down_time
        
        self.encoder.enable(total_time/1000 +0.5)
        self.stepper.DIR_VALUE = direction
            
        self.stepper.speed(sspeed)
        self.stepper.run(direction)
        self.stepper.speed_r(speed)
        
        self.allow_stop_r = 1
        self.timer_on()
        #print(ramp_up,time_up,ramp_down,time_down)
        #print('\n',between_steps,between_time)
        
        
#e1 = encoder(12,13,sid=1,ch=4)
#e2 = encoder(12,13,sid=2,ch=7)