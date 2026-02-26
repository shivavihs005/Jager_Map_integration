"""
imu.py — Madgwick Quaternion-Based IMU for MPU-6500
Pure Python implementation (no numpy dependency).
Provides stable yaw/pitch/roll via quaternion fusion of accel + gyro.
"""

import time
import math

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError:
        SMBus = None

MPU_ADDR = 0x68
PWR_MGMT_1 = 0x6B
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43

ACCEL_SCALE = 16384.0   # ±2g
GYRO_SCALE = 131.0      # ±250°/s


class IMU:
    def __init__(self):
        self.bus = None
        self.mock_mode = True

        # Quaternion state [w, x, y, z]
        self.q = [1.0, 0.0, 0.0, 0.0]

        # Madgwick filter gain
        self.beta = 0.1

        # Timing
        self.last_time = time.time()

        # Raw cached values
        self.accel = [0.0, 0.0, 1.0]
        self.gyro = [0.0, 0.0, 0.0]

        # Gyro bias from calibration
        self.gyro_bias = [0.0, 0.0, 0.0]

        if SMBus is None:
            print("[IMU] No SMBus module found. Running in mock mode.")
            return

        try:
            self.bus = SMBus(1)
            self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0x00)
            time.sleep(0.1)
            self.bus.write_byte_data(MPU_ADDR, GYRO_CONFIG, 0x00)
            self.bus.write_byte_data(MPU_ADDR, ACCEL_CONFIG, 0x00)
            self.mock_mode = False
            print("[IMU] MPU-6500 initialized successfully.")
        except Exception as e:
            print(f"[IMU] Init failed: {e}. Running in mock mode.")
            self.bus = None

    def calibrate(self, samples=500):
        """Average gyro readings at rest to find bias."""
        if self.mock_mode:
            return

        print("[IMU] Calibrating gyro bias... keep car still.")
        total = [0.0, 0.0, 0.0]
        for _ in range(samples):
            _, gyro = self._read_raw()
            total[0] += gyro[0]
            total[1] += gyro[1]
            total[2] += gyro[2]
            time.sleep(0.004)
        self.gyro_bias = [t / samples for t in total]
        print(f"[IMU] Bias calibrated: {self.gyro_bias}")

    def _read_word(self, reg):
        try:
            high = self.bus.read_byte_data(MPU_ADDR, reg)
            low = self.bus.read_byte_data(MPU_ADDR, reg + 1)
            val = (high << 8) | low
            if val > 32767:
                val -= 65536
            return val
        except Exception:
            return 0

    def _read_raw(self):
        """Read raw accel (g) and gyro (deg/s) values."""
        ax = self._read_word(ACCEL_XOUT_H) / ACCEL_SCALE
        ay = self._read_word(ACCEL_XOUT_H + 2) / ACCEL_SCALE
        az = self._read_word(ACCEL_XOUT_H + 4) / ACCEL_SCALE

        gx = self._read_word(GYRO_XOUT_H) / GYRO_SCALE
        gy = self._read_word(GYRO_XOUT_H + 2) / GYRO_SCALE
        gz = self._read_word(GYRO_XOUT_H + 4) / GYRO_SCALE

        return [ax, ay, az], [gx, gy, gz]

    def update(self):
        """Read sensors and run one Madgwick filter iteration."""
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        if self.mock_mode:
            return

        accel_raw, gyro_raw = self._read_raw()

        # Remove calibrated bias and convert gyro to rad/s
        gx = math.radians(gyro_raw[0] - self.gyro_bias[0])
        gy = math.radians(gyro_raw[1] - self.gyro_bias[1])
        gz = math.radians(gyro_raw[2] - self.gyro_bias[2])

        self.accel = accel_raw
        self.gyro = [gyro_raw[i] - self.gyro_bias[i] for i in range(3)]

        # --- Madgwick AHRS Update ---
        q0, q1, q2, q3 = self.q

        # Rate of change of quaternion from gyroscope
        qd0 = 0.5 * (-q1 * gx - q2 * gy - q3 * gz)
        qd1 = 0.5 * ( q0 * gx + q2 * gz - q3 * gy)
        qd2 = 0.5 * ( q0 * gy - q1 * gz + q3 * gx)
        qd3 = 0.5 * ( q0 * gz + q1 * gy - q2 * gx)

        # Accelerometer correction (gradient descent)
        ax, ay, az = accel_raw
        a_norm = math.sqrt(ax*ax + ay*ay + az*az)

        if a_norm > 0.01:
            ax /= a_norm
            ay /= a_norm
            az /= a_norm

            # Objective function
            f0 = 2.0 * (q1*q3 - q0*q2) - ax
            f1 = 2.0 * (q0*q1 + q2*q3) - ay
            f2 = 2.0 * (0.5 - q1*q1 - q2*q2) - az

            # Jacobian^T * f (gradient step)
            s0 = -2*q2*f0 + 2*q1*f1
            s1 =  2*q3*f0 + 2*q0*f1 - 4*q1*f2
            s2 = -2*q0*f0 + 2*q3*f1 - 4*q2*f2
            s3 =  2*q1*f0 + 2*q2*f1

            s_norm = math.sqrt(s0*s0 + s1*s1 + s2*s2 + s3*s3)
            if s_norm > 0:
                s0 /= s_norm
                s1 /= s_norm
                s2 /= s_norm
                s3 /= s_norm

            qd0 -= self.beta * s0
            qd1 -= self.beta * s1
            qd2 -= self.beta * s2
            qd3 -= self.beta * s3

        # Integrate
        q0 += qd0 * dt
        q1 += qd1 * dt
        q2 += qd2 * dt
        q3 += qd3 * dt

        # Normalize quaternion
        q_norm = math.sqrt(q0*q0 + q1*q1 + q2*q2 + q3*q3)
        self.q = [q0/q_norm, q1/q_norm, q2/q_norm, q3/q_norm]

    def get_yaw(self):
        q0, q1, q2, q3 = self.q
        yaw = math.degrees(math.atan2(
            2.0 * (q0*q3 + q1*q2),
            1.0 - 2.0 * (q2*q2 + q3*q3)
        ))
        return yaw

    def get_pitch(self):
        q0, q1, q2, q3 = self.q
        val = 2.0 * (q0*q2 - q3*q1)
        val = max(-1.0, min(1.0, val))
        return math.degrees(math.asin(val))

    def get_roll(self):
        q0, q1, q2, q3 = self.q
        roll = math.degrees(math.atan2(
            2.0 * (q0*q1 + q2*q3),
            1.0 - 2.0 * (q1*q1 + q2*q2)
        ))
        return roll

    def get_data(self):
        return {
            "yaw": round(self.get_yaw(), 2),
            "pitch": round(self.get_pitch(), 2),
            "roll": round(self.get_roll(), 2),
            "accel": {
                "x": round(self.accel[0], 3),
                "y": round(self.accel[1], 3),
                "z": round(self.accel[2], 3)
            },
            "gyro": {
                "x": round(self.gyro[0], 2),
                "y": round(self.gyro[1], 2),
                "z": round(self.gyro[2], 2)
            }
        }
