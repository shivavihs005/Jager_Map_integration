from RPLCD.i2c import CharLCD
import time

I2C_ADDR = 0x27 

def turn_off_backlight():
    print(f"Connecting to LCD at {hex(I2C_ADDR)}...")
    try:
        lcd = CharLCD(i2c_expander='PCF8574', address=I2C_ADDR, port=1, cols=16, rows=2, charmap='A00')
        
        print("Turning backlight OFF...")
        lcd.backlight_enabled = True
        
        print("Compelling backlight OFF...")
        # Sometimes direct commands help if the property setter fails
        # For PCF8574, bit 3 usually controls backlight. 
        # But allow library to handle it first.
        
        print("Done. Is it off?")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    turn_off_backlight()
