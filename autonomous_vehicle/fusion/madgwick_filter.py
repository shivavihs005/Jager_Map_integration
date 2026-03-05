"""
madgwick_filter.py
Madgwick AHRS filter — fuses gyro, accelerometer, and magnetometer.
Outputs: roll, pitch, yaw in radians (and degrees).
Reference: S. O. H. Madgwick, 2010
"""
import math


class MadgwickFilter:
    def __init__(self, beta=0.1):
        """
        beta: filter gain (higher = faster response, more noise).
              0.033 is Madgwick's recommended; 0.1 works well on a car.
        """
        self.beta = beta

        # Quaternion components [w, x, y, z]
        self.q = [1.0, 0.0, 0.0, 0.0]

        # Euler output (radians)
        self.roll  = 0.0
        self.pitch = 0.0
        self.yaw   = 0.0

    # ── Core update ──────────────────────────────────────────────────────────
    def update(self, dt,
               gx, gy, gz,          # gyro  rad/s
               ax, ay, az,          # accel m/s²  (need not be normalised)
               mx, my, mz):         # mag   any units
        """
        dt  – time step in seconds
        Magnetometer must be passed; use (0,0,0) to disable mag correction.
        """
        q1, q2, q3, q4 = self.q

        # Normalise accelerometer
        norm_a = math.sqrt(ax*ax + ay*ay + az*az)
        if norm_a == 0:
            return
        ax /= norm_a; ay /= norm_a; az /= norm_a

        # ── Gradient step by accel alone (if no mag) ──────────────────────
        use_mag = (mx != 0 or my != 0 or mz != 0)

        if use_mag:
            norm_m = math.sqrt(mx*mx + my*my + mz*mz)
            if norm_m == 0:
                use_mag = False
            else:
                mx /= norm_m; my /= norm_m; mz /= norm_m

        _2q1 = 2 * q1; _2q2 = 2 * q2; _2q3 = 2 * q3; _2q4 = 2 * q4
        _4q1 = 4 * q1; _4q2 = 4 * q2; _4q3 = 4 * q3
        _8q2 = 8 * q2; _8q3 = 8 * q3
        q1q1 = q1*q1; q2q2 = q2*q2; q3q3 = q3*q3; q4q4 = q4*q4

        # Gradient descent for accelerometer
        s1 = _4q1*q3q3 + _2q3*ax + _4q1*q2q2 - _2q2*ay
        s2 = _4q2*q4q4 - _2q4*ax + 4*q1q1*q2 - _2q1*ay - _4q2 + _8q2*q2q2 + _8q2*q3q3 + _4q2*az
        s3 = 4*q1q1*q3 + _2q1*ax + _4q3*q4q4 - _2q4*ay - _4q3 + _8q3*q2q2 + _8q3*q3q3 + _4q3*az
        s4 = 4*q2q2*q4 - _2q2*ax + 4*q3q3*q4 - _2q3*ay

        if use_mag:
            # Reference direction of Earth's magnetic field
            _2q1mx = 2 * q1 * mx; _2q1my = 2 * q1 * my; _2q1mz = 2 * q1 * mz
            _2q2mx = 2 * q2 * mx
            hx = mx*q1q1 - _2q1my*q4 + _2q1mz*q3 + mx*q2q2 + \
                 2*q2*my*q3 + 2*q2*mz*q4 - mx*q3q3 - mx*q4q4
            hy = _2q1mx*q4 + my*q1q1 - _2q1mz*q2 + _2q2mx*q3 - \
                 my*q2q2 + my*q3q3 + 2*q3*mz*q4 - my*q4q4
            _2bx = math.sqrt(hx*hx + hy*hy)
            _2bz = -_2q1mx*q3 + _2q1my*q2 + mz*q1q1 + \
                   _2q2mx*q4 - mz*q2q2 + 2*q3*my*q4 - mz*q3q3 + mz*q4q4
            _4bx = 2 * _2bx; _4bz = 2 * _2bz

            s1 += _4bx*(0.5 - q3q3 - q4q4)*mx + (_4bx*(q2*q3 - q1*q4) + _4bz*(q1*q3 + q2*q4))*my + \
                  (_4bx*(q1*q4 + q2*q3) + _4bz*(0.5 - q2q2 - q3q3))*mz
            s2 += _4bx*(q2*q3 + q1*q4)*mx + (_4bx*(q2*q4 - q1*q3) - _4bz*(q1*q2 + q3*q4))*my - \
                  (_4bz*(q2*q4 - q1*q3))*mz
            s3 += (-_4bx*(q1*q4 - q2*q3) + _4bz*(q1*q2 + q3*q4))*mx + \
                  (_4bx*(q2*q4 + q1*q3) + _4bz*(q3*q4 - q1*q2))*my + \
                  (_4bx*(q1*q3 - q2*q4) - _4bz*(q2*q3 + q1*q4))*mz
            s4 += (-_4bx*(q1*q3 + q2*q4) + _4bz*(q2*q4 - q1*q3))*mx + \
                  (_4bx*(q1*q2 - q3*q4) + _4bz*(q1*q3 + q2*q4))*my + \
                  (_4bx*(q2*q3 - q1*q4) + _4bz*(q1*q2 - q3*q4))*mz

        # Normalise step
        norm_s = math.sqrt(s1*s1 + s2*s2 + s3*s3 + s4*s4)
        if norm_s > 0:
            s1 /= norm_s; s2 /= norm_s; s3 /= norm_s; s4 /= norm_s

        # Rate of change of quaternion from gyroscope
        qDot1 = 0.5 * (-q2*gx - q3*gy - q4*gz) - self.beta*s1
        qDot2 = 0.5 * ( q1*gx + q3*gz - q4*gy) - self.beta*s2
        qDot3 = 0.5 * ( q1*gy - q2*gz + q4*gx) - self.beta*s3
        qDot4 = 0.5 * ( q1*gz + q2*gy - q3*gx) - self.beta*s4

        # Integrate
        q1 += qDot1 * dt; q2 += qDot2 * dt
        q3 += qDot3 * dt; q4 += qDot4 * dt

        # Normalise quaternion
        norm_q = math.sqrt(q1*q1 + q2*q2 + q3*q3 + q4*q4)
        self.q = [q1/norm_q, q2/norm_q, q3/norm_q, q4/norm_q]

        # ── Convert to Euler ───────────────────────────────────────────────
        self._update_euler()

    # ── Euler angles ─────────────────────────────────────────────────────────
    def _update_euler(self):
        q1, q2, q3, q4 = self.q
        # Intrinsic ZYX (yaw → pitch → roll)
        self.roll  = math.atan2(2*(q1*q2 + q3*q4), 1 - 2*(q2*q2 + q3*q3))
        sinp       = 2*(q1*q3 - q4*q2)
        sinp       = max(-1.0, min(1.0, sinp))
        self.pitch = math.asin(sinp)
        self.yaw   = math.atan2(2*(q1*q4 + q2*q3), 1 - 2*(q3*q3 + q4*q4))

    # ── Public API ───────────────────────────────────────────────────────────
    def get_euler(self):
        return self.roll, self.pitch, self.yaw   # radians

    def get_euler_deg(self):
        return (math.degrees(self.roll),
                math.degrees(self.pitch),
                math.degrees(self.yaw))

    def get_yaw_deg(self):
        """Returns 0–360° heading (0 = North/forward if magnetometer calibrated)."""
        yaw = math.degrees(self.yaw)
        return yaw % 360.0

    def reset(self):
        self.q = [1.0, 0.0, 0.0, 0.0]
        self.roll = self.pitch = self.yaw = 0.0
