import machine


uart1 = machine.UART(1, baudrate=115200 , tx=machine.Pin(4), rx=machine.Pin(5))

while True:
    if uart1.any():
        data = uart1.read() 
        if data:
            roll = data.decode()
            print(roll)