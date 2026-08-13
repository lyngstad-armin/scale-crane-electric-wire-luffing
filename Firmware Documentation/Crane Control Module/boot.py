from velo import stacy

jib2 = stacy(0,1)
jib1 = stacy(3,2)
comp1 = stacy(8,20)
comp2 = stacy(11,10)
winch = stacy(13,12)
boom = stacy(15,14)
slew1 = stacy(6,7) 
slew2 = stacy(22,21)

def CRANE_OFF():
    jib1.stop()
    jib2.stop()
    boom.stop()
    winch.stop()
    comp1.stop()
    comp2.stop()
    slew1.stop()
    slew2.stop()
