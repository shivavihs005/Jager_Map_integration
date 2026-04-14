"""
Camera stream via FFmpeg MJPEG pipe.
Camera confirmed: yuyv422, 320x240, 15fps on /dev/video0
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

    def get_health(self):
        if self.is_connected and self.failed_frames < 5:
            return "ONLINE"
        elif 5 <= self.failed_frames < 15:
            return "RECONNECTING"
        return "OFFLINE"

    def test_connection(self):
        """Quick pipe test for /api/calibrate."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-loglevel", "error",
                 "-f", "v4l2", "-i", self.DEVICE,
                 "-frames:v", "1", "-f", "mjpeg", "-"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # CRITICAL: never pipe stderr
                timeout=5
            )
            if result.returncode == 0 and len(result.stdout) > 100:
                return "PASS"
            return "FAIL (NO SIGNAL)"
        except Exception as e:
            return f"FAIL ({e})"

    def generate_mjpeg_stream(self):
        """
        Endlessly yields MJPEG frames for Flask streaming.
        Restarts ffmpeg automatically on failure.
        """
        while True:
            cmd = [
                "ffmpeg",
                "-loglevel",    "error",
                "-f",           "v4l2",
                "-input_format","yuyv422",     # Exact format the camera outputs
                "-framerate",   str(self.FPS),
                "-video_size",  f"{self.WIDTH}x{self.HEIGHT}",
                "-i",           self.DEVICE,
                "-f",           "mjpeg",       # Output MJPEG frames
                "-q:v",         "5",           # JPEG quality (2=best, 31=worst)
                "-"
            ]

            print(f"[CAMERA] Launching stream...")
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,  # CRITICAL: never pipe stderr or ffmpeg deadlocks
                    bufsize=0
                )
            except FileNotFoundError:
                print("[CAMERA] ERROR: ffmpeg not found! Run: sudo apt install ffmpeg")
                self.is_connected = False
                time.sleep(5)
                continue

            self.is_connected = True
            self.failed_frames = 0
            print("[CAMERA] Stream started.")

            buf = b""
            empty_reads = 0

            try:
                while True:
                    chunk = proc.stdout.read(8192)

                    if not chunk:
                        empty_reads += 1
                        if empty_reads > 20:
                            print("[CAMERA] stdout empty — restarting ffmpeg...")
                            break
                        time.sleep(0.05)
                        continue

                    empty_reads = 0
                    buf += chunk

                    # Extract all complete JPEG frames from buffer
                    while True:
                        soi = buf.find(b"\xff\xd8")  # JPEG Start Of Image
                        eoi = buf.find(b"\xff\xd9")  # JPEG End Of Image

                        if soi == -1 or eoi == -1 or eoi < soi:
                            break

                        frame   = buf[soi : eoi + 2]
                        buf     = buf[eoi + 2:]

                        self.is_connected  = True
                        self.failed_frames = 0

                        yield (b"--frame\r\n"
                               b"Content-Type: image/jpeg\r\n\r\n"
                               + frame + b"\r\n\r\n")

            except GeneratorExit:
                print("[CAMERA] Client disconnected.")
                proc.kill()
                return
            except Exception as e:
                print(f"[CAMERA] Stream error: {e}")
            finally:
                proc.kill()
                proc.wait()

            # ffmpeg died — wait and retry
            self.is_connected = False
            self.failed_frames += 1
            print(f"[CAMERA] Restarting in 2s... (fail #{self.failed_frames})")
            time.sleep(2)
