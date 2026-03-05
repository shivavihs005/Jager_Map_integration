"""
camera_interface.py
Future stub: Camera / lane detection.
"""


class CameraInterface:
    def __init__(self):
        print("[Camera] Stub — not connected")

    def update(self):
        pass

    def get_lane_error_m(self):
        """Cross-track error from centre of detected lane."""
        return 0.0

    def get_frame(self):
        return None
