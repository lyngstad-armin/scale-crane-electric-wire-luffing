from accel import stacy
from machine import Pin
import gc
import time

#Create Objects and Dict
enab_p = Pin(20,Pin.OUT)
s1 = stacy(0,1)
s2 = stacy(8,9)
s3 = stacy(6,5)

s4 = stacy(28,18)
s5 = stacy(26,22)
s6 = stacy(21,19)

dm = {1:s1,2:s2,3:s3,4:s4,5:s5,6:s6}
#Disable motors
enab_p.value(0)  
    
#==================-----------============ LOOP ==========-----------==============
def loop(en,sps,asp):
    enab_p.value(0)
    #start time
    st_time = time.ticks_ms()
    #static values
    csp = [0,0,0,0,0,0]
    end_time = [0,0,0,0,0,0]
    en_ref = []
    for i in range(len(en)):
       en_ref.append(en[i])
       if sps[i] <= 40 and en[i] != 0:
           sps[i] = 45
    ivl = []
    for i in range(6):
        ivl.append((1000000*asp[i]/sps[i])+time.ticks_us()) 
    while True:
        #-----------------------#
        #		Clock			#
        c_time = time.ticks_us()#
        us_cspeed = 1000
        #-----------------------#
        for i in range(6):
            if en[i] != 0 and ivl[i] >= c_time:
                if csp[i] == 0:
                    csp[i] = csp[i]+1
                    dm.get(i+1).speed(sps[i])
                    dm.get(i+1).run(en[i])
            elif ivl[i] < c_time:
                dm.get(i+1).stop()
                en[i] = 0
                if end_time[i] == 0:
                    end_time[i] = time.ticks_ms()
        if en == [0,0,0,0,0,0]:
            enab_p.value(1)
            print('Total time',(max(end_time)-st_time)/1000,'seconds')
            times = [((a-st_time)/1000)*b for a,b in zip(end_time,sps)]
            times_ac = [(a*b/4)//1 for a,b in zip(en_ref,times)]
            print(times_ac,'\n')
            del ivl
            del asp
            del en
            del sps
            del times
            del times_ac
            #print('after loop:',gc.mem_free()//1024)

            
            
            break
        l_time = time.ticks_us()
        if l_time - c_time <= us_cspeed:
            time.sleep_us(l_time-c_time)
    return

#CSV
def csv_readfile(filename):
    max_index = 0
    with open(filename,'r') as file:
        for line in file:
            max_index += 1
    for i in range(max_index//3):
        csv_data = []
        en_ = []
        sps_ = []
        asp_ = []
        read_index = 0
        with open(filename,'r') as file:
            for line in file:
                if i*3 == read_index or i*3+1 == read_index or i*3+2 == read_index:
                    row = line.strip().split(',')
                    csv_data.append(row)
                read_index += 1
        en_ = csv_data[0]
        sps_ = csv_data[1]
        asp_ = csv_data[2]
        for i in range(len(en_)):
            en_[i] = int(en_[i])
            sps_[i] = int(sps_[i])
            asp_[i] = int(asp_[i])
        del csv_data
        loop(en_,sps_,asp_)
        gc.collect()
    enab_p.value(1)

#def csv_readfile_old(filename): #### old version
#    csv_data = []
#    en_ = []
#    sps_ = []
#    asp_ = []
#    en_master = []
#    sps_master = []
#    asp_master = []
    #max_index = 0
    #with open(filename,'r') as file:
    #    for line in file:
    #        max_index += 1
#    with open(filename,'r') as file:
#        for line in file:
#            row = line.strip().split(',')
#            csv_data.append(row)
#    for i in range(len(csv_data)/3):
#        if not csv_data[i*3][0] == 'W':
#            en_ = csv_data[i*3]
#            sps_ = csv_data[(i*3)+1]
#            asp_ = csv_data[(i*3)+2]
#            for i in range(len(en_)):
#                en_[i] = int(en_[i])
#                sps_[i] = int(sps_[i])
#                asp_[i] = int(asp_[i])
#                if sps_[i] == 0:
#                    sps_[i] = 1
#            en_master.append(en_)
#            sps_master.append(sps_)
#            asp_master.append(asp_)
#    #Garbage collection
#    en_ = None
#    sps_ = None
#    asp_ = None
#    csv_data = None
#    #Run
#    for i in range(len(en_master)):
#        loop(en_master[i],sps_master[i],asp_master[i])
#        print('in csv writer: ',gc.mem_free()//1024)
#    enab_p.value(1)
csv_readfile('step_stew.csv')