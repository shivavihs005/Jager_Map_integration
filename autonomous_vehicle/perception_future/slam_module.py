"""
slam_module.py
Future stub: SLAM (Simultaneous Localisation and Mapping).
"""


class SLAMModule:
    def __init__(self):
        print("[SLAM] Stub — not active")

    def update(self, lidar_scan, imu_data):
        pass

    def get_map(self):
        return {}

    def get_pose(self):
        return {"x": 0.0, "y": 0.0, "heading": 0.0}
