from microdot import Microdot
from cors import CORS
import mm_wlan
import machine
import time

ssid_tlf = 'Jonas sin iPhone'
passord_tlf = '12345678'
nett = True

while nett:
    time.sleep_ms(500)
    try:
        mm_wlan.connect_to_network(ssid_tlf, passord_tlf)
    except Exception as e:
        print(e)
    else:
        nett = False
    
app = Microdot()
cors = CORS(app, allowed_origins=['http://172.20.10.13:8080'],
            allow_credentials=True)


@app.post('/')
async def index(request):
    data = request.json
    sim = int(data.get('simulasjon'))
    if sim == 1:
        request.app.shutdown()
        exec(open('accel_control.py').read())
        machine.reset()
        return
    return sim


app.run(debug=True, port=80)
