import network
import socket
import time
import machine
import math


uart1 = machine.UART(1, baudrate=230400, tx=machine.Pin(4), rx=machine.Pin(5))


roll = 0.0

# WAP
ap = network.WLAN(network.AP_IF)
ap.config(essid='Dashbord - 192.168.4.1', password='passord12345')
ap.active(True)
#
while not ap.active():
    pass

print('Connected! Visit: ', ap.ifconfig()[0])


html = """<!DOCTYPE html>
<html>
<head>
    <title>Pico Dashbord</title>
    <style>
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; background: #222; color: white; padding-top: 30px; }
        .gauge-container { position: relative; width: 250px; height: 125px; overflow: hidden; }
        .gauge { width: 250px; height: 250px; border-radius: 50%; background: conic-gradient(#e74c3c 90deg 180deg, #2ecc71 180deg 270deg); position: absolute; transform: rotate(-180deg); }
        .needle { width: 4px; height: 110px; background: white; position: absolute; bottom: 0; left: 123px; transform-origin: bottom center; transition: transform 0.1s linear; }
        .gauge-cover { width: 180px; height: 180px; background: #222; border-radius: 50%; position: absolute; top: 35px; left: 35px; }
        .label { font-size: 48px; font-weight: bold; margin-top: 10px; }
        #status { font-size: 14px; color: #555; margin-top: 20px; }
    </style>
</head>
<body>
    <h2>Kran Roll</h2>
    <div class="gauge-container">
        <div class="gauge"></div>
        <div class="needle" id="needle"></div>
        <div class="gauge-cover"></div>
    </div>
    <div class="label" id="val">0.0°</div>
    <div id="status">System Active</div>

<script>
    const needle = document.getElementById('needle');
    const valText = document.getElementById('val');
    
    // Using a more "aggressive" fetch approach
    async function updateUI() {
        try {
            // 'priority: high' tells Chrome this is time-sensitive data
            const response = await fetch('/data', { priority: 'high' });
            const data = await response.json();
            
            // Update the DOM
            needle.style.transform = `rotate(${data.roll}deg)`;
            valText.textContent = data.roll.toFixed(1) + ' grader';
            
            // Request the next frame immediately
            // requestAnimationFrame tells the browser to sync with the screen refresh
            requestAnimationFrame(() => setTimeout(updateUI, 50));
        } catch (e) {
            setTimeout(updateUI, 70);
        }
    }
    updateUI();
</script>
</body>
</html>
"""

# 4. Web Server Setup
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setblocking(False)
s.bind(addr)
s.listen(1)

while True:
    # --- TASK 1: THE DATA PARSER ---
    if uart1.any():
        try:
            # Read everything in buffer
            raw = uart1.read().decode('utf-8')
            
            # Find last frame < >
            end_marker = raw.rfind('>')
            start_marker = raw.rfind('<', 0, end_marker)
            
            if start_marker != -1 and end_marker != -1:
                clean_str = raw[start_marker + 1 : end_marker]
                new_roll = float(clean_str) * (180 / math.pi)
                
                # Update global variable if in range
                if -180 <= new_roll <= 180:
                    roll = new_roll
        except:
            pass

    # --- TASK 2: Web Server ---
    try:
        cl, addr = s.accept()
        try:
            cl.settimeout(0.08)
            # Use a slightly larger receive buffer for browser headers
            request = cl.recv(1024).decode('utf-8')
            
            if 'GET /data' in request:
                # Add Cache-Control to prevent browser from caching old values
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-cache\r\n\r\n{"roll": %f}' % roll)
            else:
                cl.send('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html)
        except Exception as e:
            print("Request error:", e)
        finally:
            cl.close()
    except OSError:
        pass

    # Essential: Give the Wi-Fi chip and UART a tiny window to breathe
    time.sleep_ms(2)