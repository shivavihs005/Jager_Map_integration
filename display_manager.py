from RPLCD.i2c import CharLCD
import time
import socket

class DisplayManager:
    def __init__(self, address=0x27, port=1, cols=16, rows=2):
        self.lcd = None
        self.cols = cols
        self.rows = rows
        try:
            self.lcd = CharLCD(i2c_expander='PCF8574', address=address, port=port, cols=cols, rows=rows, charmap='A00')
            self.lcd.backlight_enabled = False # User requested backlight OFF
            self.clear()
            self.write_line("Display Init", 0)
            print("LCD Initialized successfully")
        except Exception as e:
            print(f"LCD Initialization failed (might not be connected): {e}")

    def clear(self):
        if self.lcd:
            try:
                self.lcd.clear()
                self.lcd.backlight_enabled = True # Force OFF
            except Exception:
                pass

    def write_line(self, text, row=0):
        if self.lcd:
            try:
                # Ensure text fits
                text = text[:self.cols]
                self.lcd.cursor_pos = (row, 0)
                self.lcd.write_string(text)
                self.lcd.backlight_enabled = False # Force OFF
            except Exception:
                pass

    def display_ip(self):
        if not self.lcd:
            return
        
        # 1. Show Connection Status briefly
        try:
            # Try to get SSID (works on Linux/Pi)
            import subprocess
            ssid = subprocess.check_output(['iwgetid', '-r']).decode('utf-8').strip()
            self.clear()
            self.write_line("WiFi Connected!", 0)
            self.write_line(f"SSID: {ssid}", 1)
            time.sleep(3) # Show for 3 seconds
        except Exception:
            self.clear()
            self.write_line("WiFi Connected!", 0)
            time.sleep(2)

        # 2. Get IP
        ip = "No IP"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            pass
            
        # 3. Show IP Continuously
        self.clear()
        self.write_line("Status: Running", 0)
        self.write_line(f"IP:{ip}", 1)

# Global instance
display_manager = DisplayManager()
