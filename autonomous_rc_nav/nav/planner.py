import math

import requests

from config import APP, NAV


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


class RoutePlanner:
    def __init__(self, base_url=APP.osrm_base_url, timeout=8.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def snap_to_road(self, lat, lon):
        url = f"{self.base_url}/nearest/v1/driving/{lon},{lat}?number=1"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            waypoint = data["waypoints"][0]
            snap_lon, snap_lat = waypoint["location"]
            distance_m = haversine_m(lat, lon, snap_lat, snap_lon)
            return {
                "ok": distance_m <= NAV.max_destination_snap_m,
                "input": [lat, lon],
                "snapped": [snap_lat, snap_lon],
                "distance_m": distance_m,
                "name": waypoint.get("name") or "Unnamed Road",
                "source": "osrm",
            }
        except Exception:
            return {
                "ok": True,
                "input": [lat, lon],
                "snapped": [lat, lon],
                "distance_m": 0.0,
                "name": "Fallback Destination",
                "source": "fallback",
            }

    def calculate_route(self, origin, destination):
        origin_str = f"{origin[1]},{origin[0]}"
        destination_str = f"{destination[1]},{destination[0]}"
        url = (
            f"{self.base_url}/route/v1/driving/{origin_str};{destination_str}"
            "?geometries=geojson&overview=full&steps=false"
        )
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            route = data["routes"][0]
            coordinates = [[lat, lon] for lon, lat in route["geometry"]["coordinates"]]
            return {
                "coordinates": coordinates,
                "distance_m": route.get("distance", 0.0),
                "duration_s": route.get("duration", 0.0),
                "source": "osrm",
            }
        except Exception:
            coordinates = self._fallback_route(origin, destination)
            distance_m = 0.0
            for index in range(1, len(coordinates)):
                prev = coordinates[index - 1]
                curr = coordinates[index]
                distance_m += haversine_m(prev[0], prev[1], curr[0], curr[1])
            return {
                "coordinates": coordinates,
                "distance_m": distance_m,
                "duration_s": distance_m / 1.2 if distance_m else 0.0,
                "source": "fallback",
            }

    def _fallback_route(self, origin, destination, steps=24):
        route = []
        for index in range(steps + 1):
            factor = index / steps
            lat = origin[0] + ((destination[0] - origin[0]) * factor)
            lon = origin[1] + ((destination[1] - origin[1]) * factor)
            route.append([lat, lon])
        return route