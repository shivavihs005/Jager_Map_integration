"""
lidar_interface.py
Future stub: LiDAR obstacle detection.
Replace this with your actual LiDAR driver when hardware is available.
"""


class LiDARInterface:
    def __init__(self):
        print("[LiDAR] Stub — not connected")
        self.obstacles = []

    def update(self):
        """Read scan and populate self.obstacles list."""
        pass

    def get_nearest_obstacle_m(self):
        return float('inf')

    def get_obstacle_map(self):
        return []
