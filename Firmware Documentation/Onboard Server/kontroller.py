

import struct, time
from machine import Pin, I2C, SPI
from pcf8574 import PCF8574
from hd44780 import HD44780
from lcd import LCD

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
pcf = PCF8574(i2c)
hd44780 = HD44780(pcf, num_lines=2, num_columns=16)
lcd = LCD(hd44780, pcf)
lcd.backlight_on()

# ── SPI setup ────────────────────────────────────────────────────────────────
spi  = SPI(0, baudrate=2_000_000, polarity=0, phase=0,
           firstbit=SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs   = Pin(17, Pin.OUT, value=1)
gdo0 = Pin(14, Pin.IN)
    
x1 = 0
x2 = 0
x3 = 0
y1 = 0
y2 = 0
y3 = 0
z1 = 0
z2 = 0
z3 = 0

# ── Radio helpers ─────────────────────────────────────────────────────────────
def strobe(cmd):
    cs(0); spi.write(bytes([cmd])); cs(1)

def read_status(addr):
    cs(0); spi.write(bytes([addr | 0xC0]))
    buf = bytearray(1); spi.readinto(buf); cs(1)
    return buf[0]

def write_reg(addr, val):
    cs(0); spi.write(bytes([addr, val])); cs(1)

def read_fifo(n):
    cs(0); spi.write(bytes([0xFF]))
    buf = bytearray(n); spi.readinto(buf); cs(1)
    return buf

def rssi_dbm(raw):
    return (raw - 256) / 2 - 74 if raw >= 128 else raw / 2 - 74

def flush_and_rx():
    strobe(0x36); strobe(0x3A); time.sleep_us(100); strobe(0x34)

def send_packet(data):
    strobe(0x36); strobe(0x3B); time.sleep_us(100)
    cs(0); spi.write(bytes([0x7F])); spi.write(bytes([len(data)])); spi.write(data); cs(1)
    strobe(0x35)
    deadline = time.ticks_add(time.ticks_ms(), 100)
    while read_status(0xF5) not in (0x01, 0x0D):
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            break
        time.sleep_us(50)

def wait_packet(timeout_ms):
    deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
    prev = 0; stable = 0
    while True:
        rxb = read_status(0xFB) & 0x7F
        if rxb > 0 and rxb == prev:
            stable += 1
            if stable >= 3:
                return rxb
        else:
            stable = 0
        prev = rxb
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return 0
        time.sleep_us(100)

# ── CC1101 init ───────────────────────────────────────────────────────────────
cs(0); time.sleep_us(5); cs(1); time.sleep_us(40)
cs(0); time.sleep_us(5); cs(1); time.sleep_ms(100)
strobe(0x30); time.sleep_ms(100)

config = [
    (0x02,0x06),(0x03,0x47),(0x04,0xD3),(0x05,0x91),
    (0x06,0x3D),(0x07,0x04),(0x08,0x45),(0x0A,0x00),
    (0x0B,0x06),(0x0C,0x00),(0x0D,0x10),(0x0E,0xA7),
    (0x0F,0x62),(0x10,0xCA),(0x11,0x83),(0x12,0x93),
    (0x13,0x22),(0x14,0xF8),(0x15,0x34),(0x17,0x3F),
    (0x18,0x18),(0x19,0x16),(0x1A,0x6C),(0x1B,0x43),
    (0x1C,0x40),(0x1D,0x91),(0x21,0x56),(0x22,0x10),
    (0x23,0xE9),(0x24,0x2A),(0x25,0x00),(0x26,0x1F),
    (0x2C,0x81),(0x2D,0x35),(0x2E,0x09),
]
for addr, val in config:
    write_reg(addr, val)
cs(0); spi.write(bytes([0x3E | 0x40, 0xC0])); cs(1)

print("Controller ready")

# ── Main loop ─────────────────────────────────────────────────────────────────
link_rssi = None
link_lqi  = None
next_tx   = time.ticks_ms()
skjermtid = time.ticks_ms()

while True:
    skjerm_dt = time.ticks_diff(time.ticks_ms(), skjermtid)
    x1 += 1
    x2 += 1
    x3 += 1
    y1 += 1
    y2 += 1
    y3 += 1
    z1 += 1
    z2 += 1
    z3 += 1

    send_packet(struct.pack("BBBBBBBBB", x1, x2, x3, y1, y2, y3, z1, z2, z3))

    # 3. Listen for RSSI telemetry reply (30ms window)
    flush_and_rx()
    rxb = wait_packet(timeout_ms=30)
    if rxb >= 4:
        length = read_fifo(1)[0]
        rxb2 = read_status(0xFB) & 0x7F
        if length == 2 and rxb2 >= 4:
            payload = read_fifo(2)
            status  = read_fifo(2)
            if status[1] & 0x80:
                link_rssi = rssi_dbm(payload[0])
                link_lqi  = payload[1]


    if link_rssi is not None:
        print("x1={:3d} y1={:3d}  rssi={:.1f}dBm lqi={}".format(x1, y1, link_rssi, link_lqi))
        if skjerm_dt > 400:
            print('skriver til skjerm')
            lcd.write_lines(f"{link_rssi:.1f}dbm lqi:{link_lqi}\nx:{x1} y:{y1}")
            skjermtid = time.ticks_ms()
    else:
        print(f"x1={x1} y1={y1}  no link")
        if skjerm_dt > 400:
            print('skriver til skjerm')
            lcd.write_lines(f"no link\nx:{x1} y:{y1}")
            skjermtid = time.ticks_ms()

    # 5. Pace to 20Hz (50ms per cycle)
    next_tx = time.ticks_add(next_tx, 50)
    wait = time.ticks_diff(next_tx, time.ticks_ms())
    if wait > 0:
        time.sleep_ms(wait)
