from machine import Pin, SPI
import time

spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          firstbit=SPI.MSB, sck=Pin(18), mosi=Pin(19), miso=Pin(16))

cs = Pin(17, Pin.OUT, value=1)

def strobe(cmd):
    cs(0); spi.write(bytes([cmd])); cs(1)

def read_status(addr):
    cs(0)
    spi.write(bytes([addr | 0xC0]))
    buf = bytearray(1)
    spi.readinto(buf)
    cs(1)
    return buf[0]

# Manual reset per CC1101 datasheet section 11.3
cs(0); time.sleep_us(5)
cs(1); time.sleep_us(40)
cs(0); time.sleep_us(5)
cs(1)

time.sleep_ms(100)          # <-- key: give chip time to fully reset

strobe(0x30)                # SRES command
time.sleep_ms(100)          # <-- wait for oscillator to stabilise

partnum = read_status(0xF0)
version = read_status(0xF1)

print(f"PARTNUM : 0x{partnum:02X}  (expect 0x00)")
print(f"VERSION : 0x{version:02X}  (expect 0x14)")

if partnum == 0x00 and version == 0x14:
    print("✅ CC1101 OK")
else:
    print("⚠️  Unexpected - try adding a 100nF cap between VCC and GND on the module")
