# -*- coding: utf-8 -*-
import smbus
import time
import math

bus = smbus.SMBus(1)

MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
ACCEL_XOUT_H = 0x3B
bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)

MAG_ADDR = 0x0D
bus.write_byte_data(MAG_ADDR, 0x0B, 0x01)
bus.write_byte_data(MAG_ADDR, 0x09, 0x1D)

def read_accel():
    data = bus.read_i2c_block_data(MPU_ADDR, ACCEL_XOUT_H, 6)
    ax = (data[0] << 8) | data[1]
    ay = (data[2] << 8) | data[3]
    az = (data[4] << 8) | data[5]
    if ax > 32767: ax -= 65536
    if ay > 32767: ay -= 65536
    if az > 32767: az -= 65536
    return ax / 16384.0, ay / 16384.0, az / 16384.0

def read_mag():
    data = bus.read_i2c_block_data(MAG_ADDR, 0x00, 6)
    x = data[0] | (data[1] << 8)
    y = data[2] | (data[3] << 8)
    z = data[4] | (data[5] << 8)
    if x > 32767: x -= 65536
    if y > 32767: y -= 65536
    if z > 32767: z -= 65536
    return x, y, z

def get_heading():
    x, y, _ = read_mag()
    heading = math.atan2(y, x)
    heading = math.degrees(heading)
    if heading < 0: heading += 360
    return heading

prev_heading = None
alpha = 0.3
def smooth_heading(h):
    global prev_heading
    if prev_heading is None:
        prev_heading = h
        return h
    prev_heading = alpha * h + (1 - alpha) * prev_heading
    return prev_heading

try:
    print("Starting IMU + Magnetometer Test")
    while True:
        ax, ay, az = read_accel()
        heading_raw = get_heading()
        heading = smooth_heading(heading_raw)
        print("Accel (g): X={:.2f} Y={:.2f} Z={:.2f}".format(ax, ay, az))
        print("Heading: {:.2f} deg".format(heading))
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Stopped by user")
