from stepper import Stepper
from machine import Pin
import time
import gc

enab_p= machine.Pin(20,machine.Pin.OUT)
s1 = Stepper(0,1,en_pin=enab_p,steps_per_rev=200,speed_sps=200)
s2 = Stepper(8,9,en_pin=enab_p,steps_per_rev=200,speed_sps=200)
s3 = Stepper(6,5,en_pin=enab_p,steps_per_rev=200,speed_sps=200)

s4 = Stepper(28,18,en_pin=enab_p,steps_per_rev=200,speed_sps=200)
s5 = Stepper(26,22,en_pin=enab_p,steps_per_rev=200,speed_sps=200)
s6 = Stepper(21,19,en_pin=enab_p,steps_per_rev=200,speed_sps=200)

dm = {1:s1,2:s2,3:s3,4:s4,5:s5,6:s6}
enab_p.value(1)

#Start free run
def run_u(sn,dr,sps):
    sp = dm.get(sn)
    sp.speed(sps)
    sp.free_run(dr)
#Stop
def run_d(sn):
    sp = dm.get(sn)
    sp.stop()
def adj_spd(sn,a,ts):
    sp = dm.get(sn)
    sp.speed(ts)

enab_p.value(0)

#en = [-1,-1,0,0,0,0]
#sps = [1500,1000,1,1,1,1]
#asp = [2340*4,2340*1,0,0,0,0]

#-----------------------#
#		Main Loop		#
#-----------------------#
def loop(en,sps,asp):
    #print(asp)
    position = []
    data = []
    with open('current_position.csv','r') as file:
        for line in file:
            data.append(line.replace("\r\n",""))
        #print(data)
        for i in range(len(data)):
            position.append(int(data[i]))
    #    #print(position)
    #with open('current_position.csv','w') as file:
    #    for i in range(len(position)):
    #        position[i] = str(position[i])
    #        file.write(position[i])
    #        file.write('\n')
            
    enab_p.value(0)
    #start time
    st_time = time.ticks_ms()
    #static values
    csp = [0,0,0,0,0,0]
    end_time = [0,0,0,0,0,0]
    en_ref = []
    for i in range(len(en)):
       en_ref.append(en[i])
    ivl = []
    for i in range(6):
        ivl.append((1000*asp[i]/sps[i])+time.ticks_ms())
    
    print('\nStart run')
    while True:
        #-----------------------#
        #		Clock			#
        c_time = time.ticks_ms()#
        us_cspeed = 500			#
        time.sleep_us(us_cspeed)#
        #-----------------------#
        
 
        for i in range(6):
            if en[i] != 0 and ivl[i] >= c_time:
                if csp[i] == 0:
                    csp[i] = csp[i]+1
                    run_u(i+1,en[i],sps[i])
            elif ivl[i] < c_time:
                run_d(i+1)
                en[i] = 0
                if end_time[i] == 0:
                    end_time[i] = time.ticks_ms()
        if en == [0,0,0,0,0,0]:
            enab_p.value(1)
            print('Total time',(max(end_time)-st_time)/1000,'seconds')
            times = [((a-st_time)/1000)*b for a,b in zip(end_time,sps)]
            times_ac = [a*b for a,b in zip(en_ref,times)]
            print(times_ac)
            print('Command finished\n')
            break
    return position

#CSV FILE TREATMENT
def csv_readfile(filename):
    csv_data = []
    en_ = []
    sps_ = []
    asp_ = []
    with open(filename,'r') as file:
        for line in file:
            row = line.strip().split(',')
            csv_data.append(row)
        for i in range(len(csv_data)/3):
            if not csv_data[i*3][0] == 'W':
                en_ = csv_data[i*3]
                sps_ = csv_data[(i*3)+1]
                asp_ = csv_data[(i*3)+2]
                for i in range(len(en_)):
                    en_[i] = int(en_[i])
                    sps_[i] = int(sps_[i])
                    asp_[i] = int(asp_[i])
                    if sps_[i] == 0:
                        sps_[i] = 1
                gc.collect()
                position = loop(en_,sps_,asp_)
                #print('\n',en_,'\n',sps_,'\n',asp_)
            else:
                wait_l = csv_data[i*3][1]
                print('Wait command encountered\nWaiting for',wait_l,'seconds')
                time.sleep(int(wait_l))
        print('Program finished successfully')
        print('Total current position:',position)
csv_readfile('step_stew.csv')