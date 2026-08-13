from microdot import Microdot
from cors import CORS
from websocket import with_websocket
import mm_wlan
from machine import UART, Pin
import struct

uart = UART(0, baudrate=115200, tx=0, rx=1, rxbuf=1024, txbuf=512)

ssid = 'Leilighet-wifi'
ssid_hjemme = 'Tektro313'
ssid_tlf = 'Jonas sin iPhone'
ssid_armin = 'Ibsensgate99B-Guest'
passord_tlf = '12345678'
passord = 'altibox50'
passord_hjemme = 'BognelvSkipslisens313'
passord_armin = 'Rolex1987'


mm_wlan.connect_to_network(ssid_tlf, passord_tlf)
app = Microdot()
cors = CORS(app, allowed_origins=['http://192.168.87.107:8080'],
            allow_credentials=True)


@app.get('/')
async def index(request):
    return {'roll': 1}

noe = 1
data = 0
forrige = 0
def lesing():
    if uart.any():
        temp = uart.read()
        temp1 = struct.unpack('@40s', temp)
        
        temp2 = temp1[0].decode("utf-8")
        if temp2.find("<") != -1 and temp2.find(">") != -1:
            temp = temp2.replace(">", "")
            temp1 = temp.replace("<", "")
            IMU = temp1
        else:
            IMU = 0
            print('debug')
    else:
        IMU = 0
    return IMU


@app.route('/echo')
@with_websocket
async def echo(request, ws):
    while True:
        uart.write('n')
        global forrige
        global data
        forrige = data
        data = await ws.receive()
        #print(data)
        IMU_final = lesing()
        if IMU_final != 0:
            await ws.send(IMU_final)
        print(f"IMU: {IMU_final}")
        
        


app.run(debug=True, port=80)