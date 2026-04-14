import cv2
import numpy as np
import time

class CameraStream:
    """Hardware accelerated V4L2 Camera Stream + Indoor Brightness logic."""
    def __init__(self):
        self.width = 320
        self.height = 240
        self.cap = None
        self.is_connected = False
        self.failed_frames = 0
        self.reconnect()

    def reconnect(self):
        """Attempts to re-establish the hardware camera stream natively."""
        print(f"[CAMERA] Attempting hardware init on Auto Backend...")
        try:
            if self.cap:
                self.cap.release()
            self.is_connected = False
            
            # Most robust auto-negotiation
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture("/dev/video0")
            
            if self.cap.isOpened():
                self.is_connected = True
                self.failed_frames = 0
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, 15)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                print("[CAMERA] Hardware hook SUCCESS.")
            else:
                print("[CAMERA] Failed to establish video hook.")
        except Exception as e:
            print(f"[CAMERA] Error parsing video source: {e}")

    def get_health(self):
        if self.is_connected and self.failed_frames < 10:
            return "ONLINE"
        elif self.failed_frames >= 10:
            return "RECONNECTING"
        return "OFFLINE"

    def test_connection(self):
        """API hook for system diagnostics"""
        if self.is_connected and self.cap.isOpened():
            ret, _ = self.cap.read()
            return "PASS" if ret else "FAIL (NO FRAME)"
        return "FAIL (DISCONNECTED)"

    def get_frame(self):
        """Standard MJPEG frame generation"""
        if not self.is_connected:
            self.failed_frames += 1
            if self.failed_frames > 30: # Attempt reconnect every 2 seconds roughly
                self.reconnect()
            return self.get_mock_frame()
            
        ret, frame = self.cap.read()
        if not ret:
            self.failed_frames += 1
            if self.failed_frames > 30:
                self.reconnect()
            return self.get_mock_frame()
            
        self.failed_frames = 0
        
        # Optional: Add HUD overlay here if needed
        cv2.putText(frame, "JAGER_DASH: INDOOR CAM", (10, 20), cv2.FONT_HERSHEY_PLAIN, 1, (0,255,0), 1)
        
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes() if ret else None

    def get_brightness_direction(self):
        """
        Parses camera frame. Left half vs Right half brightness sum.
        Returns a steering PWM pulse (680 left, 1460 right) towards brightest path.
        """
        if not self.is_connected:
            return 1060 # Center mock

        ret, frame = self.cap.read()
        if not ret:
            self.failed_frames += 1
            return 1060
            
        self.failed_frames = 0
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        half = self.width // 2
        
        left_light = np.sum(gray[:, :half])
        right_light = np.sum(gray[:, half:])
        
        # Super rudimentary logic map: steer into light
        if left_light > right_light * 1.1: 
            return 800  # Steer Left
        elif right_light > left_light * 1.1:
            return 1300 # Steer Right
        else:
            return 1060 # Straight

    def get_mock_frame(self):
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        cv2.putText(frame, "NO CAMERA FEED", (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def generate_mjpeg_stream(self):
        """Generator function for Flask streaming"""
        while True:
            frame = self.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            time.sleep(1/15.0)
