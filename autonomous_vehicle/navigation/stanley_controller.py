"""
stanley_controller.py
Stanley path tracking controller (passive — available for future use).
Reference: Thrun et al., Stanford DARPA Grand Challenge.
Outputs a steering angle in degrees.
"""
import math


def angle_diff(a, b):
    """Shortest delta from b to a in degrees, range [-180, 180]."""
    d = a - b
    return (d + 180) % 360 - 180


class StanleyController:
    def __init__(self, k=2.5, max_steer_deg=30.0):
        """
        k  – cross-track error gain.
        Higher k gives tighter tracking but more oscillation.
        """
        self.k         = k
        self.max_steer = max_steer_deg

    def compute_steering(self, heading_error_deg, cross_track_error_m, speed_ms):
        """
        heading_error_deg   : vehicle heading minus path heading (degrees)
        cross_track_error_m : signed lateral distance from path (m).
                              Positive = path is to the left.
        speed_ms            : vehicle speed in m/s (avoid /0)

        Returns steering angle in degrees.
        """
        speed_ms = max(speed_ms, 0.1)   # avoid divide-by-zero at standstill

        # Stanley equation
        cross_term = math.degrees(math.atan2(self.k * cross_track_error_m, speed_ms))
        delta_deg  = heading_error_deg + cross_term

        # Clamp
        delta_deg = max(-self.max_steer, min(self.max_steer, delta_deg))
        return delta_deg
