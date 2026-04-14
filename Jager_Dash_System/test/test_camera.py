"""
Standalone camera test using ffmpeg pipe (same as ffplay backend).
Run on Pi: python3 test_camera.py
Press ESC to quit.
"""
import subprocess
import numpy as np
import cv2

WIDTH  = 320
HEIGHT = 240
FPS    = 15
DEVICE = "/dev/video0"

cmd = [
    "ffmpeg",
    "-loglevel", "quiet",
    "-f", "v4l2",
    "-framerate", str(FPS),
    "-video_size", f"{WIDTH}x{HEIGHT}",
    "-i", DEVICE,
    "-f", "rawvideo",
    "-pix_fmt", "bgr24",
    "-"
]

print("Starting FFmpeg camera pipe...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
frame_size = WIDTH * HEIGHT * 3

try:
    while True:
        raw = proc.stdout.read(frame_size)
        if len(raw) != frame_size:
            print("Camera disconnected or frame incomplete.")
            break

        frame = np.frombuffer(raw, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))
        cv2.imshow("JAGER_DASH Camera Test (FFmpeg)", frame)

        if cv2.waitKey(1) == 27:  # ESC
            break
finally:
    proc.kill()
    cv2.destroyAllWindows()
    print("Camera test done.")
