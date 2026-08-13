#Stepper Accel Library
from machine import Pin, PWM, Timer, I2C
import time, struct

#Stepper library that enables acceleration without blocking main script
class stacy:
    FORMAT = '16i'
    SIZE = struct.calcsize(FORMAT)
    def __init__(self,step,dire,rid=0):
        
        #Assign default speed
        self.SPSA = 50
        
        #Initialize PWM generation
        self.PWM = PWM(Pin(step),freq = self.SPSA, duty_ns=10000)
        self.PWM.deinit()
        
        #Initialize Direction Output
        self.DIR = Pin(dire, Pin.OUT)
        self.DIR_V = 0
        
        #Do dead reckoning?
        self.rid = rid
        if self.rid != 0:
            #Get stored reckoning
            self.stored = self.load_reck()
            self.reck = self.load_reck()
            #Values for timing write to bff.bin
            self.r_write_clock = 0
            self.r_write_freq  = 300
            self.r_freq = 20
        #Motor active read
        self.m_active = False
        
      
        
        #=============== END OF INIT=============
    
    
    
    #Set motor speed
    def speed(self,sps):
        
        #Negative values map over to negative direction
        if sps < 0:
            sps = -sps
            self.DIR_V = -1
            
        #Set SPS actual to input speed
        self.SPSA = sps
        
        #If the motor was running already, let it keep running
        if self.m_active == True:
            self.run(self.DIR_V)
    
    #Start motor function
    def run(self,dr):
        
        #Check for invalid direction [0,1]
        if dr == -1:
            dr = 0
            
        #Assign corrected value to storage and to output
        self.DIR_V = dr
        self.DIR.value(self.DIR_V)
        
        #Initialize PWM generation for motor steps
        self.PWM.init(freq=self.SPSA)
        
        #Store motor state
        self.m_active = True
        
        if self.rid != 0:
            self.r_timer_on()
    
    #Stop function
    def stop(self):
        #Stop PWM generation
        self.PWM.deinit()
        
        #Store motor state
        self.m_active = False
        
        if self.rid != 0:
            self.save_reck()
    
    #Store function for binary flat file
    def save_reck(self):
        with open('reck.bin','wb') as f:
            f.write(struct.pack(self.FORMAT, *self.stored))
    
    #Load function for binary flat file
    def load_reck(self):
        try:
            with open('reck.bin','rb') as f:
                return list(struct.unpack(self.FORMAT, f.read(self.SIZE)))
        except:
            return [0] * 16
    
    
    def r_timer_on(self):
        self.r_timer = Timer(mode=Timer.PERIODIC, freq=self.r_freq, callback=self.r_update)
        
    def r_timer_off(self):
        self.r_timer.deinit()
        
    def r_update(self,timer):
        #Assign correct direction for calculation
        if self.DIR_V == 0:
            d = -1
        else:
            d = 1
        
        #Update list of stored RECK
        self.reck[self.rid] += round(d*self.SPSA/self.r_freq,3)  
        self.stored[self.rid] = round(self.reck[self.rid])
        
        #Timer for write to disk
#         self.r_write_clock += 1
#         if self.r_write_clock >= self.r_write_freq:
#             self.r_write_clock = 0
#             self.save_reck()
        #If motor is OFF, turn off the callback timer
        if self.m_active == False:
            self.r_timer_off()
            return
    
    def getreck(self):
        return self.stored[self.rid]
    def resetreck(self):
        self.stored = [0] * 16
        self.save_reck()
        self.load_reck()
        self.reck = [0] * 16
    
    
#===========================Encoder class to deal with encoders======================================
class encoder:
    FORMAT = '16i'
    SIZE = struct.calcsize(FORMAT)
    STORED = []
    def __init__(self, sda_pin, scl_pin, sid = 0, ch = 7, freq = 20, mva = 0):
        #Initialize I2C
        self.i2c = I2C(1, scl=Pin(scl_pin), sda= Pin(sda_pin) , freq = 400000)
        #Declare I2C Adress
        self.adress = 0x36
        #Set step resolution (for output)
        self.resolution = 400
        #Assign storage id
        self.sid = sid
        #Assign mux channel
        self.ch = ch
        #Assign update frequency
        self.freq = freq
        #Flat list for binary flat file
        encoder.STORED = self.load_rotation()
        #Track uptime
        self.duration = 0
        #Track when to save data
        self.write_clock = 0
        self.write_freq = 80
        
        #Average outputs
        self.mva = mva
        if self.mva == 1:
            self.MV_LIST = [None]*5
        #Check if connection to MUX is stable
        try:
            self.muxch(self.ch)
        except Exception as e:
            print(f"Unexpected exception MUX: {e}")
            
        #Try to connect to I2C
        try:
            raw = self.i2c.readfrom_mem(self.adress, 0x0c, 2)
            angle = int.from_bytes(raw,"big") & 0x0FFF
            
            
            #Quadrant tracking for rotation perception
            self.quadrant = [angle//1024,angle//1024]
        except Exception as e:
            self.quadrant = [2,2]
            print(f"Failed to retrive data on initialization, channel {self.ch}")
            
    #=============== END OF INIT ==============================================#
            
    #Save function for binary flat file
    def save_rotation(self):
        with open('enc.bin','wb') as f:
            f.write(struct.pack(self.FORMAT, *encoder.STORED))
    
    #Load function for binary flat file
    def load_rotation(self):
        try:
            with open('enc.bin','rb') as f:
                return list(struct.unpack(self.FORMAT, f.read(self.SIZE)))
        except:
            print(f"Failed to read BFF")
            return None
        
    #Define channel changer for multiplexer MUX
    def muxch(self, ch):
        if 0 <= ch < 8:
            try:
                time.sleep_us(30)
                self.i2c.writeto(0x70, bytes([1 << ch]))
                time.sleep_us(30) #settling time
            except Exception as e:
                print(f"Could not connect to MUX {ch}")
    
    #Turn on timer
    def timer_on(self):
        self.t = Timer(mode=Timer.PERIODIC, freq=self.freq, callback=self.update)
        self.t_active = True
        
    #Turn off timer
    def timer_off(self):
        self.t.deinit()
        self.t_active = False
        
    #Update loop for rotation tracking
    def update(self,timer):
        
        #Tick duration timer down
        self.duration -= 1 / self.freq
        if self.duration <= 0:
            self.timer_off()
        
        #Read Encoder Angle
        try:
            self.muxch(self.ch)
            raw = self.i2c.readfrom_mem(self.adress, 0x0c, 2)
            angle = int.from_bytes(raw,"big") & 0x0FFF
            
            #%
            if self.mva == 1:
                self.MV_LIST = [self.MV_LIST[1],self.MV_LIST[2],self.MV_LIST[3],self.MV_LIST[4],angle]
       
        except Exception as e:
            print(f"Failed to read in update on {self.ch}: {e}")
            return
        
        #Assign Quadrant, left shift value
        self.quadrant = [self.quadrant[1], angle//1024 ]
        #Check for rotation boundaries
        if 3 in self.quadrant and 0 in self.quadrant:
            if self.quadrant[0] == 3 and self.quadrant[1] == 0:
                encoder.STORED[2*self.sid] += 1
            elif self.quadrant[0] == 0 and self.quadrant[1] == 3:
                encoder.STORED[2*self.sid] -= 1
        
        #Tick timer for storage
        #self.write_clock += 1
        #if self.write_clock >= self.write_freq:
        #    self.write_clock = 0
        #    self.save_rotation()

    #Enable update loop
    def enable(self,duration):
        if hasattr(self,'t'):
            self.timer_off()
        self.duration = duration
        #encoder.STORED = self.load_rotation()
        self.timer_on()
        
    #Set position
    def setpos(self,setpos):
        encoder.STORED = self.load_rotation()
        try:
            self.muxch(self.ch)
            raw = self.i2c.readfrom_mem(self.adress, 0x0c, 2)
            angle = int.from_bytes(raw,"big") & 0x0FFF
        except Exception as e:
            print(f"Set failed on {self.ch}: {e}")
            return
        data = int((angle/4096)*self.resolution)
        encoder.STORED[2*self.sid] = 0
        encoder.STORED[2*self.sid+1] = setpos - data
        self.save_rotation()
        
    def getpos(self):
        try:
            self.muxch(self.ch)
            reads = []
            for k in range(3):
                raw = self.i2c.readfrom_mem(self.adress, 0x0c, 2)
                reads.append(int.from_bytes(raw,"big") & 0x0FFF)
            angle = sorted(reads)[1]
            data = int((angle/4096)*self.resolution)
            #Total position = Read data + Rotations * Rotational resoltion + Positional offset
            position = data+encoder.STORED[2*self.sid]*self.resolution+encoder.STORED[2*self.sid+1]
            return position
        except Exception as e:
            print(f"Get failed {self.ch}: {e}")
            return None
        
    def getavg(self):
        if self.mva == 1:
            try:
                self.MV_LIST.sort()
                angle = sum(self.MV_LIST[1:4])//3
                data = int((angle/4096)*self.resolution)
                #Total position = Read data + Rotations * Rotational resoltion + Positional offset
                position = data+encoder.STORED[2*self.sid]*self.resolution+encoder.STORED[2*self.sid+1]
                return position
            except Exception as e:
                print(f"Getavg failed {self.ch}: {e}")
                return None
        else:
            print("Average Not Enabled for this encoder")
class link:
    import time
    def __init__(self,SX,EX):
        self.motor = SX
        self.encoder = EX
        
        self.timer_freq = 20
        self.timer_active = False
        
        self.target = 0
        
    def goto(self,pos,spd):
        curr_pos = self.encoder.getpos()
        self.target = pos
        if not curr_pos + 20 >= self.target or not curr_pos - 20 <= self.target:
            diff_pos = curr_pos - pos
            min_time = round(abs(diff_pos)/spd,1)
            if min_time >= 4:
                pass
                #self.encoder.enable(min_time+1)
            if diff_pos >= 1:
                dr = -1
            elif diff_pos <= -1:
                dr = 1
            self.motor.speed(spd)
            self.motor.run(dr)
        self.timer_on()
    
    #Update and check for target position
    def update(self,timer):
        curr_pos = self.encoder.getpos()
        if self.target-100 <= curr_pos <= self.target:
            self.motor.stop()
            self.timer_off()
    
    #Create timer on
    def timer_on(self):
        self.tim = Timer(mode=Timer.PERIODIC,freq = self.timer_freq,callback=self.update)
        self.timer_active = True
        
    #Create timer shutoff    
    def timer_off(self):
        #self.tim.init(freq=1)
        self.tim.deinit()
        self.timer_active = False
            