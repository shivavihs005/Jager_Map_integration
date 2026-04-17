import pigpio
import time

RX_PIN = 21   # LiDAR TX → Pi RX
BAUD   = 115200   # ⚠️ Most LiDAR use 115200 (TF-Luna/SDM15 type)

pi = pigpio.pi()
if not pi.connected:
    print("❌ pigpio not running")
    exit()

pi.set_mode(RX_PIN, pigpio.INPUT)
pi.bb_serial_read_open(RX_PIN, BAUD)

print("🚀 Reading LiDAR distance...\n")

buffer = bytearray()

try:
    while True:
        count, data = pi.bb_serial_read(RX_PIN)

        if count:
            buffer.extend(data)

            # Process frames (TF-Luna style: 9 bytes starting with 0x59 0x59)
            while len(buffer) >= 9:
                if buffer[0] == 0x59 and buffer[1] == 0x59:
                    frame = buffer[:9]
                    buffer = buffer[9:]

                    # Extract distance
                    dist = frame[2] + (frame[3] << 8)

                    print(f"📏 Distance: {dist} cm")
                else:
                    buffer.pop(0)

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n🛑 Stopped")

finally:
    pi.bb_serial_read_close(RX_PIN)
    pi.stop()
