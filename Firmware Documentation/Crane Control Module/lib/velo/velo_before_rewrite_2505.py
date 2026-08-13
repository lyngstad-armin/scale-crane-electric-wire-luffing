#Stepper Accel Library
from machine import Pin, PWM, Timer, I2C
import time, struct

#Stepper library that enables acceleration without blocking main script
class stacy:
    def __init__(self,step_pin,dir_pin,SPSA = 400,RECK = 0):
    
        self.PWM = PWM(Pin(step_pin),freq = 800, duty_ns=10000)
        self.PWM.deinit()
         
        self.DIR = Pin(dir_pin, Pin.OUT)
        self.DIR_VALUE = 0
        
        self.SPSA = SPSA
        
        self.motor_active = False
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
            del file; del row; del line
    #RECK TIMER ON             
    def reckon_timer_on(self):
        self.reck = Timer(-1)
        self.reck.init(mode=Timer.PERIODIC,freq = 30,callback=self.reck_update)
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
            del d
                
    
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
        if self.motor_active == True:
            self.run_s(self.DIR_VALUE)
        del sps


    def run(self,d):
        if d == -1:
            d = 0
        self.DIR_VALUE = d
        self.DIR.value(self.DIR_VALUE)
        self.PWM.init(freq=self.SPSA)
        self.motor_active = True
        if self.do_reckoning == 1:
            self.reckon_timer_on()
        del d
            
    def run_s(self,d):
        if d == -1:
            d = 0
        self.DIR_VALUE = d
        self.DIR.value(self.DIR_VALUE)
        self.PWM.init(freq=self.SPSA)
        self.motor_active = True
        del d
            
    def stop(self):
        self.PWM.deinit()
        self.motor_active = False
        if self.do_reckoning == 1:
            with open('reckoning.csv','w') as f:
                    f.write("{}\r\n".format(round(self.reckoning,1)))
            del f
    
    
    
#===========================Encoder class to deal with encoders======================================
class encoder:
    FORMAT = '16i'
    SIZE = struct.calcsize(FORMAT)
    def __init__(self, sda_pin, scl_pin, sid = 0, ch = 7, freq = 20):
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
        self.stored = self.load_rotation()
        #Track uptime
        self.duration = 0
        #Track when to save data
        self.write_clock = 0
        self.write_freq = 80
        
        
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
            f.write(struct.pack(self.FORMAT, *self.stored))
    
    #Load function for binary flat file
    def load_rotation(self):
        try:
            with open('enc.bin','rb') as f:
                return list(struct.unpack(self.FORMAT, f.read(self.SIZE)))
        except:
            return [0] * 16
        
    #Define channel changer for multiplexer MUX
    def muxch(self, ch):
        if 0 <= ch < 8:
            try:
                self.i2c.writeto(0x70, bytes([1 << ch]))
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
        except Exception as e:
            print(f"Failed to read in update on {self.ch}: {e}")
            return
        
        #Assign Quadrant, left shift value
        self.quadrant = [self.quadrant[1], angle//1024 ]
        #Check for rotation boundaries
        if 3 in self.quadrant and 0 in self.quadrant:
            if self.quadrant[0] == 3 and self.quadrant[1] == 0:
                self.stored[2*self.sid] += 1
            elif self.quadrant[0] == 0 and self.quadrant[1] == 3:
                self.stored[2*self.sid] -= 1
        
        #Tick timer for storage
        self.write_clock += 1
        if self.write_clock >= self.write_freq:
            self.write_clock = 0
            self.save_rotation()

    #Enable update loop
    def enable(self,duration):
        if hasattr(self,'t'):
            self.timer_off()
        self.duration = duration
        #self.stored = self.load_rotation()
        self.timer_on()
        
    #Set position
    def setpos(self,setpos):
        self.stored = self.load_rotation()
        try:
            self.muxch(self.ch)
            raw = self.i2c.readfrom_mem(self.adress, 0x0c, 2)
            angle = int.from_bytes(raw,"big") & 0x0FFF
        except Exception as e:
            print(f"Set failed on {self.ch}: {e}")
            return
        data = int((angle/4096)*self.resolution)
        self.stored[2*self.sid] = 0
        self.stored[2*self.sid+1] = setpos - data
        self.save_rotation()
        
    def getpos(self):
        try:
            self.muxch(self.ch)
            raw = self.i2c.readfrom_mem(self.adress, 0x0c, 2)
            angle = int.from_bytes(raw,"big") & 0x0FFF
            data = int((angle/4096)*self.resolution)
            #Total position = Read data + Rotations * Rotational resoltion + Positional offset
            position = data+self.stored[2*self.sid]*self.resolution+self.stored[2*self.sid+1]
            return position
        except Exception as e:
            print(f"Get failed {self.ch}: {e}")
            return None
        
        
class link:
    import time
    def __init__(self,SX,EX):
        self.motor = SX
        self.encoder = EX
        
        self.timer_freq = 20
        self.timer_active = False
        
        self.target = 0
        
    def goto(self,pos,spd):
        #self.encoder.enable(5)
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
            