#scode interpreter
#Micropy
import gc

try:
    del scode_translate
except Exception as e:
    del e
    pass

read_line = []

#Read file and remove annotations
with open('qtest.csv','r') as file:
    for line in file:
            row = line.strip().split(',')
            read_line.append(row)
    for i in range(len(read_line)):
        cstr = str(read_line[i])
        cstr = cstr.replace('[','')
        cstr = cstr.replace(']','')
        cstr = cstr.replace('\\','')
        cstr = cstr.replace('t','')
        split = cstr.split('#',1)
        cstr = split[0]
        cstr = cstr.replace("'","")
        cstr = cstr.strip(' ')
        read_line[i]= cstr

#Read commands and convert to lists
command = []
for i in range(len(read_line)):
    cache_line = [0,0,0]
    cache = [0,0,0,0,0,0]
    pstr = read_line[i]
    #case Wait
    if pstr.startswith('W'):
        pstr= pstr + (' ')
        w_cache = []
        c_w = 1
        while pstr[c_w] != ' ':
            w_cache.append(pstr[c_w])
            c_w = c_w + 1
        w_cache_2 = str()
        w_cache_2 = w_cache_2.join(w_cache)
        cache_line[0] = ['W',w_cache_2,1,1,1,1]
        cache_line[1] = [1,1,1,1,1,1]
        cache_line[2] = [1,1,1,1,1,1]
    #case Tram Motor
    elif pstr.startswith('G'):
        cache_line[0] = [0,0,0,0,0,0]
        c_en = 1
        #Enabling motors from G123456
        while pstr[c_en] != ' ':
            cache_line[0][int(pstr[c_en])-1] = 2
            c_en = c_en + 1
        c_dir = c_en + 2
        dir_pos = 0
        #Check for Direction Argument
        if not pstr[c_dir-1] == 'D':
            print('Expected Direction Argument')
            break
        while pstr[c_dir] != ' ':
            #if int(pstr[c_dir]) == 0:
            #    cache_line[0][int(pstr[dir_pos])-1] = -1
            #dir_pos = dir_pos + 1
            cache_int = 0
            while cache_line[0][cache_int] != 2:
                cache_int = cache_int + 1
            if int(pstr[c_dir]) == 0:
                dir_posi = -1
            else:
                dir_posi = 1
            cache_line[0][cache_int] = dir_posi
                
            
            c_dir = c_dir + 1 #Keep
        c_sps = c_dir + 2
        #Check for multiple Velocity Argument
        sps_cache = [[],[],[],[],[],[]]
        sps_site = str()
        
        if not pstr[c_sps-1] == 'V':
            print('Expected At Least 1 Speed Argument')
            break
        #Checking if V applies to all
        c_sps_a = 0
        if pstr[c_sps] == 'A':
            c_sps_a = c_sps + 2
            while pstr[c_sps_a] !=')':
                for ALL in range(6):
                    sps_cache[ALL].append(pstr[c_sps_a])
                c_sps_a = c_sps_a + 1
            for ALL in range(6):
                    sps_cache[ALL] = int(sps_site.join(sps_cache[ALL]))
            c_sps = c_sps_a + 3
            cache_line[1] = sps_cache
        #Looping for multiple V until Break
        while not pstr[c_sps-1] == 'B':
            c_sps = c_sps + 2
            c_sps_nomer = int(pstr[c_sps-2])-1
            sps_cache[c_sps_nomer] = []
            while pstr[c_sps] != ')':
                sps_cache[c_sps_nomer].append(pstr[c_sps])
                c_sps = c_sps + 1
            sps_cache[c_sps_nomer] = int(sps_site.join(sps_cache[c_sps_nomer]))
            cache_line[1] = sps_cache
            c_sps = c_sps + 3
        #Change all empty V to 0
        for g in range(6):
                if sps_cache[g] == []:
                    sps_cache[g] = 0
        #Check for multiple Step Argument
        sts_cache = [[],[],[],[],[],[]]
        sts_site = str()
        c_sts = c_sps + 2
        if not pstr[c_sts-1] == 'S':
            print('Expected At Least 1 Step Argument')
            break
        #Checking if S applies to all
        if pstr[c_sts] == 'A':
            c_sts_a = c_sts + 2
            while pstr[c_sts_a] !=')':
                for ALL in range(6):
                    sts_cache[ALL].append(pstr[c_sts_a])
                c_sts_a = c_sts_a + 1
            for ALL in range(6):
                    sts_cache[ALL] = int(sts_site.join(sts_cache[ALL]))
            c_sts = c_sts_a + 3
            #cache_line[2] = sts_cache
        #Loop for multiple S until Break
        while not pstr[c_sts-1] == 'B':
            c_sts = c_sts + 2
            c_sts_nomer = int(pstr[c_sts-2])-1
            sts_cache[c_sts_nomer] = []
            while pstr[c_sts] != ')':
                sts_cache[c_sts_nomer].append(pstr[c_sts])
                c_sts = c_sts + 1
            sts_cache[c_sts_nomer] = int(sts_site.join(sts_cache[c_sts_nomer]))
            #cache_line[2] = sts_cache
            c_sts = c_sts +3
        for g in range(6):
            if sts_cache[g] == []:
                sts_cache[g] = 0
            if cache_line[0][g] == 0:
                sts_cache[g] = 0
        cache_line[2] = sts_cache  
                
                
                
        #Case motor to position
    elif pstr.startswith('M'):
        cache_line[0] = [0,0,0,0,0,0]
        c_en = 1
        #Enabling motors from G123456
        while pstr[c_en] != ' ':
            cache_line[0][int(pstr[c_en])-1] = 2
            c_en = c_en + 1
        c_sps = c_en + 2
        
        #Importing current position
        #ALLOCATE MEMORY
        try:
            del position
            del data
        except Exception as e:
            del e
        try:
            del file
            del line
        except Exception as e:
            del e
        #print(list(globals().keys()))
        #print(gc.mem_free()//1024)
        
        
        
        
        
        
        with open('current_position.csv','r') as file:
            data = []
            position = []
            for line in file:
                data.append(line.replace("\r\n",""))
            for i in range(len(data)):
                position.append(int(data[i]))
        #V args from G module
            #Check for multiple Velocity Argument
        sps_cache = [[],[],[],[],[],[]]
        sps_site = str()
        
        if not pstr[c_sps-1] == 'V':
            print('Expected At Least 1 Speed Argument')
            break
        #Checking if V applies to all
        c_sps_a = 0
        if pstr[c_sps] == 'A':
            c_sps_a = c_sps + 2
            while pstr[c_sps_a] !=')':
                for ALL in range(6):
                    sps_cache[ALL].append(pstr[c_sps_a])
                c_sps_a = c_sps_a + 1
            for ALL in range(6):
                    sps_cache[ALL] = int(sps_site.join(sps_cache[ALL]))
            c_sps = c_sps_a + 3
            cache_line[1] = sps_cache
        #Looping for multiple V until Break
        while not pstr[c_sps-1] == 'B':
            c_sps = c_sps + 2
            c_sps_nomer = int(pstr[c_sps-2])-1
            sps_cache[c_sps_nomer] = []
            while pstr[c_sps] != ')':
                sps_cache[c_sps_nomer].append(pstr[c_sps])
                c_sps = c_sps + 1
            sps_cache[c_sps_nomer] = int(sps_site.join(sps_cache[c_sps_nomer]))
            cache_line[1] = sps_cache
            c_sps = c_sps + 3
        #Change all empty V to 0
        for g in range(6):
                if sps_cache[g] == []:
                    sps_cache[g] = 0
         #Check for multiple Step Argument
        sts_cache = [[],[],[],[],[],[]]
        sts_site = str()
        c_sts = c_sps + 2
        if not pstr[c_sts-1] == 'S':
            print('Expected At Least 1 Step Argument')
            break
        #Checking if S applies to all
        if pstr[c_sts] == 'A':
            c_sts_a = c_sts + 2
            while pstr[c_sts_a] !=')':
                for ALL in range(6):
                    sts_cache[ALL].append(pstr[c_sts_a])
                c_sts_a = c_sts_a + 1
            for ALL in range(6):
                    sts_cache[ALL] = int(sts_site.join(sts_cache[ALL]))
            c_sts = c_sts_a + 3
            #cache_line[2] = sts_cache
        #Loop for multiple S until Break
        while not pstr[c_sts-1] == 'B':
            c_sts = c_sts + 2
            c_sts_nomer = int(pstr[c_sts-2])-1
            sts_cache[c_sts_nomer] = []
            while pstr[c_sts] != ')':
                sts_cache[c_sts_nomer].append(pstr[c_sts])
                c_sts = c_sts + 1
            sts_cache[c_sts_nomer] = int(sts_site.join(sts_cache[c_sts_nomer]))
            #cache_line[2] = sts_cache
            c_sts = c_sts +3
        for g in range(6):
            if sts_cache[g] == []:
                sts_cache[g] = 0
        #calculating diff pos
        for i in range(6):
            sts_cache[i] = sts_cache[i] - position[i]
            #assigning dir
            if sts_cache[i] < 0:
                sts_cache[i] = sts_cache[i]*(-1)
                if cache_line[0][i] == 2:
                    cache_line[0][i] = -1
            elif cache_line[0][i] == 2:
                    cache_line[0][i] = 1
        #removing unused positions
        for i in range(6):
            if cache_line[0][i] == 0:
                sts_cache[i] = 0
        cache_line[2] = sts_cache
        
    cache = [cache_line[0],cache_line[1],cache_line[2]]
    command.append(cache)
    #print(gc.mem_free()//1024)
    del cache
    del sps_cache
    del sts_cache
    
    #writing current to current_position
    #ALLOCATE MEMORY
    try:
        del position
        del data
    except Exception as e:
        del e
    try:
        del file
        del line
    except Exception as e:
        del e
    with open('current_position.csv','r') as file:
        position = []
        data = []
        for line in file:
            data.append(line.replace("\r\n",""))
        for i in range(len(data)):
            position.append(int(data[i]))
    for i in range(len(position)):
        if not cache_line[0][0] == 'W':
            position[i] = position[i] + (cache_line[2][i] * cache_line[0][i])
        if position[i] < 0:
            position[i] = 0
    #ALLOCATE MEMORY
    del data
    try:
        del file
        del line
    except Exception as e:
        del e
        
    with open('current_position.csv','w') as file:
        for i in range(len(position)):
            position[i] = str(position[i])
            file.write(position[i])
            file.write('\n')

#DELETE VARIABLES
del read_line
del position
del c_en
del cstr
del g
del pstr
del i
del c_sts
del c_sps_a
del c_sps
del row
del file
del sts_site
del c_sts_a
del sps_site
del cache_line

#CHECK MEMORY
#print(list(globals().keys()))
#print(gc.mem_free()//1024)

for line in range(len(command)):
    for row in range(3):
        for entry in range(6):
            if row != 0:
                command[line][row][entry] *= 4
            command[line][row][entry] = str(command[line][row][entry])
#print(command)
with open('step_stew.csv','w') as file:
    for line in range(len(command)):
        for row in range(3):
            file.write(','.join(command[line][row]))
            file.write('\n')

#DELETE VARIABLES
del command
del line
del row
del file
del entry

#CHECK MEMORY
#print(list(globals().keys()))
#print(gc.mem_free()//1024)
gc.collect()