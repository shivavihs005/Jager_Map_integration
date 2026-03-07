import math


def haversine_m(lat1, lon1, lat2, lon2):
    radius = 6_371_000.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a_val = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2.0) ** 2
    )
    return radius * 2.0 * math.atan2(math.sqrt(a_val), math.sqrt(1.0 - a_val))


def bearing_deg(lat1, lon1, lat2, lon2):
    lon_delta = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    y_val = math.sin(lon_delta) * math.cos(lat2_rad)
    x_val = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon_delta)
    return (math.degrees(math.atan2(y_val, x_val)) + 360.0) % 360.0


class PurePursuitFollower:
    def __init__(self, lookahead_m):
        self.lookahead_m = lookahead_m

    def get_lookahead(self, route, route_index, current_position):
        if not route:
            return None, route_index

        lat, lon = current_position
        while route_index < len(route) - 1:
            next_point = route[route_index]
            if haversine_m(lat, lon, next_point[0], next_point[1]) > self.lookahead_m:
                break
            route_index += 1

        clamped_index = min(route_index, len(route) - 1)
        return route[clamped_index], clamped_index