# cc1101.py — CC1101 / AS07-M1101S MicroPython driver for Raspberry Pi Pico
#
# Wiring (SPI0 defaults):
#   VCC  → 3.3V     GND  → GND
#   SCK  → GP18     MOSI → GP19    MISO → GP16    CSN → GP17
#   GDO0 → GP14  (connect for best RX reliability, or pass gdo0=None)

from machine import Pin, SPI
import time

# ── Register addresses ────────────────────────────────────────────────────────
IOCFG0=0x02;FIFOTHR=0x03;SYNC1=0x04;SYNC0=0x05
PKTLEN=0x06;PKTCTRL1=0x07;PKTCTRL0=0x08;CHANNR=0x0A
FSCTRL1=0x0B;FSCTRL0=0x0C;FREQ2=0x0D;FREQ1=0x0E;FREQ0=0x0F
MDMCFG4=0x10;MDMCFG3=0x11;MDMCFG2=0x12;MDMCFG1=0x13;MDMCFG0=0x14
DEVIATN=0x15;MCSM1=0x17;MCSM0=0x18;FOCCFG=0x19;BSCFG=0x1A
AGCCTRL2=0x1B;AGCCTRL1=0x1C;AGCCTRL0=0x1D
FREND1=0x21;FREND0=0x22
FSCAL3=0x23;FSCAL2=0x24;FSCAL1=0x25;FSCAL0=0x26
TEST2=0x2C;TEST1=0x2D;TEST0=0x2E

# Status registers (read with 0xC0 flag)
R_PARTNUM=0xF0;R_VERSION=0xF1;R_RSSI=0xF4
R_MARCSTATE=0xF5;R_TXBYTES=0xFA;R_RXBYTES=0xFB

# Strobes
SRES=0x30;SRX=0x34;STX=0x35;SIDLE=0x36;SFRX=0x3A;SFTX=0x3B

# MARC states
ST_IDLE=0x01;ST_RX=0x0D;ST_TX=0x13
ST_TXUFLOW=0x16;ST_RXOFLOW=0x11

# FIFO addresses
TXFIFO_BURST = 0x7F   # 0x3F | 0x40  burst write TX FIFO
RXFIFO_BURST = 0xFF   # 0x3F | 0xC0  burst read  RX FIFO (valid while CS low)
RXFIFO_SINGLE= 0xBF   # 0x3F | 0x80  single read RX FIFO

MAX_PAYLOAD = 61

# ── Default config: 433.92 MHz, GFSK, 38.4 kBaud, CRC on ────────────────────
DEFAULT_CONFIG = [
    (IOCFG0,   0x06),  # GDO0: high on sync word, low on end-of-packet
    (FIFOTHR,  0x47),
    (SYNC1,    0xD3),(SYNC0,    0x91),
    (PKTLEN,   0x3D),  # max 61 bytes
    (PKTCTRL1, 0x04),  # append RSSI+LQI status bytes, no addr filter
    (PKTCTRL0, 0x45),  # variable length, CRC enabled, whitening on
    (CHANNR,   0x00),
    (FSCTRL1,  0x06),(FSCTRL0,  0x00),
    (FREQ2,    0x10),(FREQ1,    0xA7),(FREQ0,    0x62),  # 433.92 MHz
    (MDMCFG4,  0xCA),(MDMCFG3,  0x83),  # 38.4 kBaud
    (MDMCFG2,  0x93),(MDMCFG1,  0x22),(MDMCFG0,  0xF8),
    (DEVIATN,  0x34),
    (MCSM1,    0x30),  # after TX->idle, after RX->idle (simpler state machine)
    (MCSM0,    0x18),
    (FOCCFG,   0x16),(BSCFG,    0x6C),
    (AGCCTRL2, 0x43),(AGCCTRL1, 0x40),(AGCCTRL0, 0x91),
    (FREND1,   0x56),(FREND0,   0x10),
    (FSCAL3,   0xE9),(FSCAL2,   0x2A),(FSCAL1,   0x00),(FSCAL0,   0x1F),
    (TEST2,    0x81),(TEST1,    0x35),(TEST0,    0x09),
]


class CC1101:
    """
    CC1101 / AS07-M1101S driver for Raspberry Pi Pico.

        radio = CC1101()           # GP18/19/16/17, GDO0=GP14
        radio = CC1101(gdo0=None)  # no GDO0 wired
        radio.init()

        radio.send(b"hello")

        pkt = radio.recv(timeout_ms=2000)
        if pkt:
            print(pkt.data, pkt.rssi_dbm, pkt.lqi, pkt.crc_ok)
    """

    def __init__(self, spi_id=0, sck=18, mosi=19, miso=16, csn=17, gdo0=14):
        self._spi  = SPI(spi_id, baudrate=2_000_000, polarity=0, phase=0,
                         firstbit=SPI.MSB,
                         sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))
        self._cs   = Pin(csn,  Pin.OUT, value=1)
        self._gdo0 = Pin(gdo0, Pin.IN) if gdo0 is not None else None

    # ── low-level SPI ─────────────────────────────────────────────────────────

    def _strobe(self, cmd):
        self._cs(0)
        self._spi.write(bytes([cmd]))
        self._cs(1)

    def _read_status(self, addr):
        self._cs(0)
        self._spi.write(bytes([addr | 0xC0]))
        buf = bytearray(1)
        self._spi.readinto(buf)
        self._cs(1)
        return buf[0]

    def _read_reg(self, addr):
        self._cs(0)
        self._spi.write(bytes([addr | 0x80]))
        buf = bytearray(1)
        self._spi.readinto(buf)
        self._cs(1)
        return buf[0]

    def _write_reg(self, addr, val):
        self._cs(0)
        self._spi.write(bytes([addr, val]))
        self._cs(1)

    def _write_burst(self, addr, data):
        self._cs(0)
        self._spi.write(bytes([addr | 0x40]))
        self._spi.write(bytes(data))
        self._cs(1)

    def _read_fifo(self, n):
        """Read n bytes from RX FIFO using correct burst address."""
        self._cs(0)
        self._spi.write(bytes([RXFIFO_BURST]))
        buf = bytearray(n)
        self._spi.readinto(buf)
        self._cs(1)
        return buf

    # ── reset ─────────────────────────────────────────────────────────────────

    def reset(self):
        self._cs(0); time.sleep_us(5)
        self._cs(1); time.sleep_us(40)
        self._cs(0); time.sleep_us(5)
        self._cs(1)
        time.sleep_ms(100)
        self._strobe(SRES)
        time.sleep_ms(100)

    # ── init ──────────────────────────────────────────────────────────────────

    def init(self, config=None):
        self.reset()
        pn  = self._read_status(R_PARTNUM)
        ver = self._read_status(R_VERSION)
        if pn != 0x00 or ver != 0x14:
            raise RuntimeError(
                "CC1101 not found (PARTNUM=0x{:02X} VER=0x{:02X}) "
                "Check: SCK=GP18 MOSI=GP19 MISO=GP16 CSN=GP17".format(pn, ver))
        for addr, val in (config or DEFAULT_CONFIG):
            self._write_reg(addr, val)
        self._write_burst(0x3E, bytes([0xC0]))  # PA table: +10 dBm
        self._strobe(SIDLE)
        print("CC1101 ready  PARTNUM=0x{:02X}  VERSION=0x{:02X}".format(pn, ver))

    # ── state ─────────────────────────────────────────────────────────────────

    def idle(self):
        self._strobe(SIDLE)
        deadline = time.ticks_add(time.ticks_ms(), 100)
        while self._read_status(R_MARCSTATE) != ST_IDLE:
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                break
            time.sleep_us(50)

    def marcstate(self):
        return self._read_status(R_MARCSTATE)

    # ── transmit ──────────────────────────────────────────────────────────────

    def send(self, data, timeout_ms=200):
        """Transmit up to 61 bytes. Returns True on success."""
        if len(data) > MAX_PAYLOAD:
            raise ValueError("Max payload is {} bytes".format(MAX_PAYLOAD))

        self.idle()
        self._strobe(SFTX)
        time.sleep_us(100)

        # Write length prefix + payload into TX FIFO
        self._cs(0)
        self._spi.write(bytes([TXFIFO_BURST]))
        self._spi.write(bytes([len(data)]))
        self._spi.write(bytes(data))
        self._cs(1)

        self._strobe(STX)

        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while True:
            s = self.marcstate()
            if s in (ST_IDLE, ST_RX):
                return True
            if s == ST_TXUFLOW:
                self._strobe(SFTX)
                return False
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                self.idle()
                return False
            time.sleep_us(50)

    # ── receive ───────────────────────────────────────────────────────────────

    class Packet:
        __slots__ = ('data', 'rssi_dbm', 'lqi', 'crc_ok')
        def __init__(self, data, rssi, lqi, crc_ok):
            self.data     = data
            self.rssi_dbm = rssi
            self.lqi      = lqi
            self.crc_ok   = crc_ok
        def __repr__(self):
            return "Packet(data={}, rssi={:.1f}dBm, lqi={}, crc_ok={})".format(
                self.data, self.rssi_dbm, self.lqi, self.crc_ok)

    @staticmethod
    def _rssi_dbm(raw):
        return (raw - 256) / 2 - 74 if raw >= 128 else raw / 2 - 74

    def recv(self, timeout_ms=1000):
        """
        Enter RX and wait for one packet. Returns Packet or None on timeout.
        """
        if self.marcstate() != ST_RX:
            self._strobe(SIDLE)
            self._strobe(SFRX)
            time.sleep_us(100)
            self._strobe(SRX)

        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)

        if self._gdo0 is not None:
            # GDO0 wired: sync word goes high, end-of-packet goes low
            while not self._gdo0.value():
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    return None
            while self._gdo0.value():
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    self._strobe(SIDLE); return None
            time.sleep_us(200)  # let status bytes append
        else:
            # No GDO0: wait for RXBYTES to arrive and stop growing
            prev = 0; stable = 0
            while True:
                rxb = self._read_status(R_RXBYTES) & 0x7F
                if rxb > 0 and rxb == prev:
                    stable += 1
                    if stable >= 3:
                        break
                else:
                    stable = 0
                prev = rxb
                if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                    return None
                time.sleep_us(100)

        if self.marcstate() == ST_RXOFLOW:
            self._strobe(SIDLE); self._strobe(SFRX); return None

        rxb = self._read_status(R_RXBYTES) & 0x7F
        if rxb < 4:
            self._strobe(SIDLE); self._strobe(SFRX); return None

        length = self._read_fifo(1)[0]
        if length == 0 or length > MAX_PAYLOAD:
            self._strobe(SIDLE); self._strobe(SFRX); return None

        rxb = self._read_status(R_RXBYTES) & 0x7F
        if rxb < length + 2:
            self._strobe(SIDLE); self._strobe(SFRX); return None

        payload = bytes(self._read_fifo(length))
        status  = self._read_fifo(2)

        self._strobe(SIDLE)
        self._strobe(SFRX)
        time.sleep_us(100)
        self._strobe(SRX)

        return self.Packet(
            data    = payload,
            rssi    = self._rssi_dbm(status[0]),
            lqi     = status[1] & 0x7F,
            crc_ok  = bool(status[1] & 0x80),
        )

    # ── config helpers ────────────────────────────────────────────────────────

    def set_channel(self, ch):
        self.idle()
        self._write_reg(CHANNR, ch & 0xFF)

    def set_output_power(self, pa=0xC0):
        """433 MHz PA: 0x12=-30dBm  0x60=0dBm  0xC0=+10dBm"""
        self._write_burst(0x3E, bytes([pa]))

    def rssi_dbm(self):
        """Instantaneous RSSI in dBm — valid in RX mode only."""
        return self._rssi_dbm(self._read_status(R_RSSI))
