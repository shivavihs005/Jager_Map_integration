import math


EARTH_RADIUS_M = 6_371_000.0


class DeadReckoning:
    def project(self, lat, lon, heading_deg, speed_mps, dt):
        distance = max(0.0, speed_mps) * max(0.0, dt)
        heading_rad = math.radians(heading_deg)

        north = distance * math.cos(heading_rad)
        east = distance * math.sin(heading_rad)

        delta_lat = (north / EARTH_RADIUS_M) * (180.0 / math.pi)
        cos_lat = math.cos(math.radians(lat)) or 1e-9
        delta_lon = (east / (EARTH_RADIUS_M * cos_lat)) * (180.0 / math.pi)
        return lat + delta_lat, lon + delta_lon