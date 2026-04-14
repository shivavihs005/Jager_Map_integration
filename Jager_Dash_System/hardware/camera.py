"""
Camera stream via FFmpeg MJPEG pipe.
ffplay /dev/video0 confirmed working — uses same ffmpeg backend.
"""
import subprocess
import threading
import time

class CameraStream:
    DEVICE = "/dev/video0"
    WIDTH  = 320
    HEIGHT = 240
    FPS    = 15

    def __init__(self):
        self.is_connected = False
        self.failed_frames = 0
        self._proc = None
        self._lock = threading.Lock()

    def get_health(self):
        if self.is_connected and self.failed_frames < 5:
            return "ONLINE"
        elif 5 <= self.failed_frames < 15:
            return "RECONNECTING"
        return "OFFLINE"

    def test_connection(self):
        """Quick check for /api/calibrate diagnostic."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-f", "v4l2", "-i", self.DEVICE,
                 "-show_entries", "stream=width,height", "-of", "csv=p=0"],
                capture_output=True, timeout=3
            )
            if result.returncode == 0:
                return "PASS"
            return "FAIL (NO SIGNAL)"
        except Exception as e:
            return f"FAIL ({e})"

    def generate_mjpeg_stream(self):
        """
        Yields multipart MJPEG frames for Flask Response.
        Parses raw ffmpeg MJPEG stdout by JPEG SOI/EOI markers.
        """
        while True:
            cmd = [
                "ffmpeg",
                "-loglevel", "error",
                "-f",         "v4l2",
                "-framerate", str(self.FPS),
                "-video_size", f"{self.WIDTH}x{self.HEIGHT}",
                "-i",         self.DEVICE,
                "-vf",        f"scale={self.WIDTH}:{self.HEIGHT}",
                "-f",         "mjpeg",
                "-q:v",       "5",
                "-"
            ]

            print(f"[CAMERA] Launching: {' '.join(cmd)}")
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=0
                )
            except FileNotFoundError:
                print("[CAMERA] ffmpeg not found! Run: sudo apt install ffmpeg")
                self.is_connected = False
                time.sleep(5)
                continue

            self.is_connected = True
            self.failed_frames = 0
            buf = b""
            consecutive_empty = 0

            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    consecutive_empty += 1
                    if consecutive_empty > 10:
                        print("[CAMERA] ffmpeg stdout dry — restarting...")
                        break
                    time.sleep(0.05)
                    continue

                consecutive_empty = 0
                buf += chunk

                # Extract all complete JPEG frames in the buffer
                while True:
                    start = buf.find(b"\xff\xd8")  # JPEG SOI
                    end   = buf.find(b"\xff\xd9")  # JPEG EOI

                    if start == -1 or end == -1 or end <= start:
                        break

                    frame = buf[start : end + 2]
                    buf   = buf[end + 2:]

                    self.failed_frames = 0
                    self.is_connected  = True

                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n"
                           + frame + b"\r\n\r\n")

            # ffmpeg died — log stderr and retry
            err_out = proc.stderr.read().decode(errors="replace")
            print(f"[CAMERA] ffmpeg exited. stderr: {err_out[:300]}")
            proc.kill()
            self.is_connected = False
            self.failed_frames += 1
            time.sleep(2)   # Brief pause before reconnect attempt
