

from machine import Pin, SPI
import struct, time

# spi
spi = SPI(0, baudrate=2_000_000, polarity=0, phase=0,
          firstbit=SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs  = Pin(17, Pin.OUT, value=1)

# radio hjelpefunksjoner
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
    deadline = time.ticks_add(time.ticks_ms(), 50)
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

partnum = read_status(0xF0)
version = read_status(0xF1)
print(hex(partnum))
print(hex(version))

def motor_kontroll():
    # motor kode?
    pass

# CC1101 init
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

print("Kran er klar")
flush_and_rx()

while True:
    # 1. Wait for joystick packet
    rxb = wait_packet(timeout_ms=500)

    if rxb == 0:
        print("(Ingen signal)")
        motor_kontroll() # endre til hvordan man nullsetter omega
        flush_and_rx()
        continue

    if read_status(0xF5) == 0x11:  # RX overflow
        flush_and_rx()
        continue

    if rxb < 4:
        flush_and_rx()
        continue

    length = read_fifo(1)[0]
    rxb2   = read_status(0xFB) & 0x7F

    if not (0 < length <= 61 and rxb2 >= length + 2):
        flush_and_rx()
        continue

    payload = read_fifo(length)
    status  = read_fifo(2)

    if not (status[1] & 0x80):  # CRC fail
        flush_and_rx()
        continue
    if partnum != 0 or version != 20:
        break
    print(hex(version))


    # vi kan sette motor kode her?
    if rxb != 0:
        motor_kontroll() # beveg motorene
        data = struct.unpack('BBBBBB', payload)
        print(data)


    # 3. sender telemetri tilbake
    send_packet(bytes([status[0], status[1] & 0x7F]))

    # 4. Back to RX
    flush_and_rx()
    
print('feil partnum og/eller version')
