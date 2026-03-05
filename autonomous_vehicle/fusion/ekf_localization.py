"""
ekf_localization.py
Extended Kalman Filter for GPS + IMU fusion.
State vector: [x, y, heading, velocity, acceleration]
"""
import math
import numpy as np


EARTH_RADIUS_M = 6_371_000.0


def gps_to_xy(lat, lon, origin_lat, origin_lon):
    """Convert GPS coordinate to local (x, y) in metres relative to origin."""
    dlat = math.radians(lat - origin_lat)
    dlon = math.radians(lon - origin_lon)
    x = EARTH_RADIUS_M * dlon * math.cos(math.radians(origin_lat))
    y = EARTH_RADIUS_M * dlat
    return x, y


class EKFLocalizer:
    """
    State: [x, y, heading, velocity, acceleration]
    Observations:
        - GPS     → [x_gps, y_gps]
        - IMU acc → [acceleration]
        - Mag/Madg→ [heading]
    """

    # Noise matrices (tune these for your environment)
    Q_DIAG   = [0.01, 0.01, 0.001, 0.05, 0.1]   # Process noise
    R_GPS    = [1.5, 1.5]                          # GPS measurement noise (m)
    R_HEAD   = [0.05]                              # Heading noise (rad)
    R_ACCEL  = [0.2]                               # Acceleration noise (m/s²)

    def __init__(self):
        # State: [x, y, heading, velocity, accel]
        self.x = np.zeros((5, 1))

        # Covariance matrix
        self.P = np.eye(5) * 1.0

        # Noise matrices
        self.Q = np.diag(self.Q_DIAG)
        self.R_gps   = np.diag(self.R_GPS)
        self.R_heads = np.diag(self.R_HEAD)
        self.R_acc   = np.diag(self.R_ACCEL)

        self.origin_lat = None
        self.origin_lon = None
        self.initialized = False

    def initialize_origin(self, lat, lon):
        self.origin_lat = lat
        self.origin_lon = lon
        self.x[2, 0] = 0.0          # heading
        self.initialized = True
        print(f"[EKF] Origin set: lat={lat:.6f}  lon={lon:.6f}")

    # ── Prediction step ──────────────────────────────────────────────────────
    def predict(self, dt):
        """Motion model: constant acceleration, integrate position + velocity."""
        if not self.initialized:
            return

        x, y, h, v, a = self.x.flatten()

        # Predicted state
        x_new = x + v * math.cos(h) * dt
        y_new = y + v * math.sin(h) * dt
        h_new = h                     # heading from magnetometer/Madgwick only
        v_new = max(0.0, v + a * dt)  # clamp to non-negative
        a_new = a                     # acc from IMU

        self.x = np.array([[x_new], [y_new], [h_new], [v_new], [a_new]])

        # Jacobian of motion model
        F = np.eye(5)
        F[0, 2] = -v * math.sin(h) * dt
        F[0, 3] =  math.cos(h) * dt
        F[1, 2] =  v * math.cos(h) * dt
        F[1, 3] =  math.sin(h) * dt
        F[3, 4] =  dt

        self.P = F @ self.P @ F.T + self.Q

    # ── Generic measurement update ────────────────────────────────────────────
    def _update(self, z, H, R):
        S = H @ self.P @ H.T + R
        K = self.P @ H.T @ np.linalg.inv(S)
        y_innov = z - H @ self.x
        self.x = self.x + K @ y_innov
        self.P = (np.eye(5) - K @ H) @ self.P

    # ── GPS update ───────────────────────────────────────────────────────────
    def update_gps(self, lat, lon):
        if not self.initialized:
            self.initialize_origin(lat, lon)
            return

        gx, gy = gps_to_xy(lat, lon, self.origin_lat, self.origin_lon)
        z = np.array([[gx], [gy]])

        H = np.zeros((2, 5))
        H[0, 0] = 1.0   # x
        H[1, 1] = 1.0   # y

        self._update(z, H, self.R_gps)

    # ── Heading update (from Madgwick yaw) ───────────────────────────────────
    def update_heading(self, heading_rad):
        if not self.initialized:
            return
        z = np.array([[heading_rad]])
        H = np.zeros((1, 5))
        H[0, 2] = 1.0
        self._update(z, H, self.R_heads)

    # ── Acceleration update ──────────────────────────────────────────────────
    def update_acceleration(self, acc_forward):
        """
        acc_forward: scalar acceleration along vehicle heading (m/s²).
        Estimate this as the projection of IMU accel onto heading direction.
        """
        if not self.initialized:
            return
        z = np.array([[acc_forward]])
        H = np.zeros((1, 5))
        H[0, 4] = 1.0   # acceleration state
        self._update(z, H, self.R_acc)

    # ── State getters ─────────────────────────────────────────────────────────
    def get_state(self):
        x, y, h, v, a = self.x.flatten()
        return {
            "x":            x,
            "y":            y,
            "heading_rad":  h,
            "heading_deg":  math.degrees(h) % 360.0,
            "velocity_ms":  v,
            "velocity_kmh": v * 3.6,
            "acceleration": a
        }

    def get_position(self):
        x, y = self.x[0, 0], self.x[1, 0]
        return x, y

    def get_gps_from_xy(self):
        """Back-convert EKF x/y to GPS lat/lon for map display."""
        if not self.initialized:
            return self.origin_lat or 0.0, self.origin_lon or 0.0
        x, y = self.x[0, 0], self.x[1, 0]
        lat = self.origin_lat + math.degrees(y / EARTH_RADIUS_M)
        lon = self.origin_lon + math.degrees(x / (EARTH_RADIUS_M * math.cos(math.radians(self.origin_lat))))
        return lat, lon
