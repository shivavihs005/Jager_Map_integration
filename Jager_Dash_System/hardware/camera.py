import cv2
import numpy as np
import time

class CameraStream:
    """Mock camera stream generator for Windows."""
    def __init__(self):
        print("[MOCK CAMERA] Initializing video stream...")
        self.width = 640
        self.height = 480
        
    def get_frame(self):
        """Generate a simulated camera frame for the dashboard."""
        # Create a black image
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Add some random noise to simulate 'brightness comparison'
        noise = np.random.randint(0, 50, (self.height, self.width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        # Add HUD overlay text
        cv2.putText(frame, f"MOCK CAMERA FEED", (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 159), 2)
                    
        cv2.putText(frame, f"TIME: {time.strftime('%H:%M:%S')}", (50, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 240, 255), 2)
                    
        # Simulate obstacle detection area
        cv2.rectangle(frame, (100, 150), (540, 400), (159, 0, 255), 2)
        
        # Encode to JPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            return None
        return jpeg.tobytes()

    def generate_mjpeg_stream(self):
        """Generator function for Flask streaming"""
        while True:
            frame = self.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
            time.sleep(0.1) # Simulate ~10 FPS
