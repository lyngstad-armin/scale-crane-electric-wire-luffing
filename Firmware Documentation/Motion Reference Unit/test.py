import network
import socket
from time import sleep
from machine import Pin
import sys

# WiFi credentials
ssid = 'Jonas sin iPhone'
password = '12345678'

# LED setup (GPIO 25 = onboard LED on Pico)
led = Pin('LED', Pin.OUT)


# ----------------------------
# Connect to WiFi
# ----------------------------
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    while not wlan.isconnected():
        print('Waiting for connection...')
        sleep(1)

    ip = wlan.ifconfig()[0]
    print('Connected on', ip)
    return ip


# ----------------------------
# Open Socket
# ----------------------------
def open_socket():
    address = ('', 80)  # Listen on port 80
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    print('Server listening on port 80')
    return connection


# ----------------------------
# HTML Webpage
# ----------------------------
def webpage(temperature, state):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pico W Web Server</title>
    </head>
    <body>
        <h1>Pico W LED Control</h1>

        <form action="/lighton">
            <input type="submit" value="Light ON" />
        </form>

        <form action="/lightoff">
            <input type="submit" value="Light OFF" />
        </form>

        <form action="/close">
            <input type="submit" value="Stop Server" />
        </form>

        <p>LED is {state}</p>
        <p>Temperature is {temperature}</p>

    </body>
    </html>
    """
    return html


# ----------------------------
# Web Server Loop
# ----------------------------
def serve(connection):
    state = 'OFF'
    led.value(0)
    temperature = 0

    while True:
        client, addr = connection.accept()
        print('Client connected from', addr)

        request = client.recv(1024)
        request = str(request)
        print('Request:', request)

        # Control LED
        if '/lighton' in request:
            led.value(1)
            state = 'ON'

        elif '/lightoff' in request:
            led.value(0)
            state = 'OFF'

        elif '/close' in request:
            client.close()
            sys.exit()

        # Send response
        html = webpage(temperature, state)

        client.send('HTTP/1.1 200 OK\r\n')
        client.send('Content-Type: text/html\r\n')
        client.send('Connection: close\r\n\r\n')
        client.sendall(html)

        client.close()


# ----------------------------
# Main Program
# ----------------------------
ip = connect()
connection = open_socket()
serve(connection)