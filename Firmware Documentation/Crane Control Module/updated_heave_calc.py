import time, umatrix, gc, math

#DECLARE POSITION VECTORS FOR HEAVE
P_PS = umatrix.matrix( [     0,	 103.6,	  0.0],
                           [-103.6,	     0,	   0.0],
                           [   0.0,	  0.0,	     0] )
#(0,0,103.6)
    
P_SB = umatrix.matrix( [     0,	 -76.67,	22.58],
                           [76.67,	     0,	   0.0],
                           [-22.58,	  0.0,	     0] )
#(0,22.6,76.7)
P_BJ = umatrix.matrix( [     0,	   0.0,	500.0],
                           [  0.0,	     0,	   0.0],
                           [ -500.0,	  0.0,	     0] )
#(0,500,0)    
P_JR = umatrix.matrix( [      0,	110.2,	286.4],
                        [ -110.2,	      0,	    0.0],
                        [ -286.4,	   0.0,	      0] )

#(0,286.4,-110.2)
POS = P_PS.transpose, P_SB.transpose, P_BJ.transpose, P_JR.transpose
del P_PS; del P_SB; del P_BJ; del P_JR

def heave_calc(POS, th1,th2,th3,th4,rolld,hd):
    degrad = math.pi / 180
    
    #POS      TUPLE POSITION VECTORS
    #TH1            ROLL ANGLE (RAD)
    #TH2            SLEW ANGLE (RAD)
    #TH3            BOOM ANGLE (RAD)
    #TH4            JIB  ANGLE (RAD)
    #ROLLD    ANGULAR VELOCITY (RAD/S)
    #HD       LINEAR  VELOCITY (mm/S)
    
    #OUTPUT XCDOT3  LINEAR VELOCITY 3-AXIS REP (mm/S)
    
    #Position Vectors (constant)
    P_PS, P_SB, P_BJ, P_JR = POS
    cos = math.cos
    sin = math.sin
    #Relative Rotation Matrices
    
    c1, s1 = cos(th1), sin(th1)
    c2, s2 = cos(th2*degrad), sin(th2*degrad)
    c3, s3 = cos(th3*degrad), sin(th3*degrad)
    c4, s4 = cos(th4*degrad), sin(th4*degrad)
    
    R1 = umatrix.matrix([1,0,0],[0,c1,-s1],[0,s1,c1])  #ROLL
    R21 = umatrix.matrix([c2,-s2,0],[s2,c2,0],[0,0,1]) #SLEW
    R32 = umatrix.matrix([1,0,0],[0,c3,-s3],[0,s3,c3]) #BOOM
    R43 = umatrix.matrix([1,0,0],[0,c4,-s4],[0,s4,c4]) #JIB
    #Additional Relative Rotations
    R21T = R21.transpose
    R31T = R21T * R32.transpose
    R41T = R31T * R43.transpose 
    #Absolute Rotation Matrices
    R2 = R1 * R21
    R3 = R2 * R32
    R4 = R3 * R43
    #Angluar Velocities
    W1 = umatrix.matrix([rolld],[0],[0])
    #Linear Velocity (Heave)
    #ht = umatrix.matrix([0,0,hd]).transpose
    #Lie Group
    #e3 = umatrix.matrix([0,0,1])
    #Simplify multiplication order
    R1C = P_PS*W1
    R2C_1 = R21T*W1
    R2C_2 = P_SB*R2C_1
    R3C_1 = R31T*W1
    R3C_2 = P_BJ*R3C_1
    R4C_1 = R41T*W1
    R4C_2 = P_JR*R4C_1
    
    XCDOT3 = ( R1 * R1C + R2 * R2C_2 + R3 * R3C_2 + R4 * R4C_2)
    return float(hd + XCDOT3[2][0])



while True:
    mem_b = gc.mem_free()//1024
    now = time.ticks_ms()
    
    res = heave_calc(POS,0,0,0,0,0.0004,2)
    
    diff = time.ticks_diff(time.ticks_ms(),now)
    mem_a = gc.mem_free()//1024
    
    print(f"Time: {diff} ms Mem Before: {mem_b}, Mem After: {mem_a}, Res: {res}")
    gc.collect()
    


