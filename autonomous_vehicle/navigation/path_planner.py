"""
path_planner.py
Waypoint queue manager. Feeds waypoints (lat, lon) to the navigation controller.
"""
import math


EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlon/2)**2
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class PathPlanner:
    def __init__(self, reached_threshold_m=0.30):
        self._waypoints = []    # list of (lat, lon) tuples
        self._current_idx = 0
        self._reached_threshold = reached_threshold_m

    # ── Add / replace waypoints ───────────────────────────────────────────────
    def set_destination(self, lat, lon):
        """Single destination — clears old route."""
        self._waypoints = [(lat, lon)]
        self._current_idx = 0
        print(f"[Path] Destination set: ({lat:.6f}, {lon:.6f})")

    def set_waypoints(self, waypoint_list):
        self._waypoints = list(waypoint_list)
        self._current_idx = 0
        print(f"[Path] Loaded {len(self._waypoints)} waypoints")

    def add_waypoint(self, lat, lon):
        self._waypoints.append((lat, lon))

    # ── Progress tracking ─────────────────────────────────────────────────────
    def get_current_waypoint(self):
        if self._current_idx < len(self._waypoints):
            return self._waypoints[self._current_idx]
        return None

    def get_lookahead_waypoint(self, current_lat, current_lon, lookahead_m):
        """
        Returns the first waypoint further than lookahead_m from current position.
        Used by Pure Pursuit.
        """
        for wp in self._waypoints[self._current_idx:]:
            d = haversine_m(current_lat, current_lon, wp[0], wp[1])
            if d >= lookahead_m:
                return wp
        # No waypoint beyond lookahead — return last waypoint
        return self._waypoints[-1] if self._waypoints else None

    def check_and_advance(self, current_lat, current_lon):
        """Call on each control loop tick. Advances to next waypoint if reached."""
        wp = self.get_current_waypoint()
        if wp is None:
            return

        dist = haversine_m(current_lat, current_lon, wp[0], wp[1])
        if dist <= self._reached_threshold:
            self._current_idx += 1
            print(f"[Path] Waypoint {self._current_idx} reached. Remaining: {self.remaining()}")

    def is_complete(self):
        return self._current_idx >= len(self._waypoints)

    def remaining(self):
        return max(0, len(self._waypoints) - self._current_idx)

    def clear(self):
        self._waypoints = []
        self._current_idx = 0

    def get_all_waypoints(self):
        return list(self._waypoints)

    def get_route_geojson(self):
        """Returns a GeoJSON LineString dict for Leaflet."""
        coords = [[lon, lat] for lat, lon in self._waypoints]
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {}
            }]
        }
