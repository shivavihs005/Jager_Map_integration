"""
pure_pursuit.py
Pure Pursuit geometric path tracking controller.
Outputs a steering angle in degrees.
"""
import math


def bearing_between(lat1, lon1, lat2, lon2):
    """Compass bearing (degrees) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return bearing % 360.0


class PurePursuitController:
    def __init__(self, wheelbase_m, lookahead_m, max_steer_deg=30.0):
        self.wheelbase   = wheelbase_m
        self.lookahead   = lookahead_m
        self.max_steer   = max_steer_deg

    def compute_steering(self, current_lat, current_lon, current_heading_deg,
                         target_lat, target_lon):
        """
        Returns steering angle in degrees.
        Positive = turn right ; Negative = turn left.
        """
        # Bearing from current position to look-ahead waypoint
        target_bearing = bearing_between(current_lat, current_lon,
                                         target_lat,  target_lon)

        # Heading error: how much we need to turn
        alpha = target_bearing - current_heading_deg
        # Normalise to [-180, 180]
        alpha = (alpha + 180) % 360 - 180
        alpha_rad = math.radians(alpha)

        # Approximate lookahead distance using chord
        Ld = self.lookahead

        # Pure Pursuit formula:  delta = atan(2 * L * sin(alpha) / Ld)
        delta_rad = math.atan2(2.0 * self.wheelbase * math.sin(alpha_rad), Ld)
        delta_deg = math.degrees(delta_rad)

        # Clamp
        delta_deg = max(-self.max_steer, min(self.max_steer, delta_deg))
        return delta_deg
