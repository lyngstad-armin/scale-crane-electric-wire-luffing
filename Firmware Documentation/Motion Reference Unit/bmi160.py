from machine import I2C
import time

class BMI160:
    # I2C address (0x68 or 0x69)
    def __init__(self, i2c: I2C, addr=0x68):
        self.i2c = i2c
        self.addr = addr

        # Check chip ID (should be 0xD1)
        chip_id = self._read_u8(0x00)
        if chip_id != 0xD1:
            raise OSError("BMI160 not found, chip id = 0x{:02X}".format(chip_id))

        # Soft reset
        self._write_u8(0x7E, 0xB6)
        time.sleep_ms(100)

        # Set accel normal mode
        self._write_u8(0x7E, 0x11)
        time.sleep_ms(50)

        # Set gyro normal mode
        self._write_u8(0x7E, 0x15)
        time.sleep_ms(50)

        # Accel config: 100 Hz, normal
        self._write_u8(0x40, 0x28)

        # Gyro config: 100 Hz, normal
        self._write_u8(0x42, 0x28)

        # Accel range ±2g
        self._write_u8(0x41, 0x03)

        # Gyro range ±2000 dps
        self._write_u8(0x43, 0x00)

    # ---------- Low-level I2C helpers ----------
    def _write_u8(self, reg, val):
        self.i2c.writeto_mem(self.addr, reg, bytes([val]))

    def _read_u8(self, reg):
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _read_i16(self, reg):
        data = self.i2c.readfrom_mem(self.addr, reg, 2)
        val = data[0] | (data[1] << 8)
        if val & 0x8000:
            val -= 65536
        return val

    # ---------- Public sensor reads ----------
    def accel(self):
        # Registers 0x12–0x17
        ax = self._read_i16(0x12)
        ay = self._read_i16(0x14)
        az = self._read_i16(0x16)
        return ax, ay, az

    def gyro(self):
        # Registers 0x0C–0x11
        gx = self._read_i16(0x0C)
        gy = self._read_i16(0x0E)
        gz = self._read_i16(0x10)
        return gx, gy, gz